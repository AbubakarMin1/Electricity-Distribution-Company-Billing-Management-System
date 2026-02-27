from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import datetime
import os
import logging
import oracledb
import uvicorn
import uuid

d = os.environ.get("ORACLE_HOME")               # Defined by the file `oic_setup.sh`
oracledb.init_oracle_client(lib_dir=d)          # Thick mode

# These environment variables come from `env.sh` file.
user_name = os.environ.get("DB_USERNAME")
user_pswd = os.environ.get("DB_PASSWORD")
db_alias  = os.environ.get("DB_ALIAS")

#connection = oracledb.connect(user=user_name, password=user_pswd, dsn=db_alias) #########
connection = oracledb.connect(
user=user_name,
password=user_pswd,
dsn=db_alias
)

# make sure to setup connection with the DATABASE SERVER FIRST. refer to python-oracledb documentation for more details on how to connect, and run sql queries and PL/SQL procedures.
#IP is = http://193.123.91.175
app = FastAPI()

logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.DEBUG)

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# -----------------------------
# API Endpoints
# -----------------------------
 
# ---------- GET methods for the pages ----------
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Bill payment page
@app.get("/bill-payment", response_class=HTMLResponse)
async def get_bill_payment(request: Request):
    return templates.TemplateResponse("bill_payment.html", {"request": request})

# Bill generation page
@app.get("/bill-retrieval", response_class=HTMLResponse)
async def get_bill_retrieval(request: Request):
    return templates.TemplateResponse("bill_retrieval.html", {"request": request})

# Adjustments page
@app.get("/bill-adjustments", response_class=HTMLResponse)
async def get_bill_adjustment(request: Request):
    return templates.TemplateResponse("bill_adjustment.html", {"request": request, "adjustment_details": None}) #####

##
@app.get("/test-connection")
async def test_connection():
    try:
        connection = oracledb.connect(user=user_name, password=user_pswd, dsn=db_alias)
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM DUAL")  # Simple test query for Oracle
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return {"status": "success", "result": result}
    except oracledb.DatabaseError as e:
        return {"status": "error", "message": str(e)}
##


# ---------- POST methods for the pages ----------
@app.post("/bill-payment", response_class=HTMLResponse)
async def post_bill_payment(
    request: Request, 
    bill_id: int = Form(...), 
    amount: float = Form(...), 
    payment_method_id: int = Form(...)
):
    try:
        oracledb.init_oracle_client(lib_dir=os.environ.get("ORACLE_HOME"))
        connection = oracledb.connect(
            user=user_name, 
            password=user_pswd,
            dsn=db_alias,)
        cursor = connection.cursor()
        #the amount when extracted from the user, can only be in int, even though its a float value, im assuming that the way its extracted is only in int
        #basically calling my PL/SQL function but the function didn't have the implementation to store the outstanding amount into arrears, so i just decided to 
        #do most of the work in the application layer, there wasn't any restriction to NOT do it here, and the assignment is very ambigous in the things you ask us to do
        process_payment_query = """
        SELECT TotalAmount_BeforeDueDate, TotalAmount_AfterDueDate, DueDate
        FROM Bill
        WHERE BillID = :bill_id
        """
        cursor.execute(process_payment_query, {"bill_id": bill_id})
        bill_details = cursor.fetchone()
        if not bill_details:
            return templates.TemplateResponse(
                "bill_payment.html",
                {"request": request,
                "message": "Bill not found! Bill ID Invalid! sahi wala daalo", 
                "alert_type": "error"},
            )
        total_amount_before_due, total_amount_after_due, due_date = bill_details

        payment_date = datetime.datetime.now()
        if payment_date > due_date: 
            outstanding_amount = total_amount_after_due - amount
        else:
            outstanding_amount = total_amount_before_due - amount

        if outstanding_amount > 0:
            payment_status = "Partially Paid"
        elif outstanding_amount < 0:
            return templates.TemplateResponse(
                "bill_payment.html",
                {"request": request,
                "message": "Amount is greater than bill, renter with the exact amount :", 
                "alert_type": "error"},
            )
        else:   
            payment_status = "Fully Paid"
            outstanding_amount = 0
        insert_payment_query = """
        INSERT INTO PaymentDetails (BillID, PaymentDate, PaymentStatus, PaymentMethodID, AmountPaid)
        VALUES (:bill_id, :payment_date, :payment_status, :payment_method_id, :amount_paid)
        """
        cursor.execute(
            insert_payment_query,
            {
                "bill_id": bill_id,
                "payment_date": payment_date,
                "payment_status": payment_status,
                "payment_method_id": payment_method_id,
                "amount_paid": amount,
            },
        )
        update_bill_query = """
            UPDATE Bill
            SET TotalAmount_BeforeDueDate = :outstanding_amount,
                TotalAmount_AfterDueDate = :outstanding_amount * 1.10
            WHERE BillID = :bill_id
        """
        #you can also add the arrears to the bill amount but that logic would assume that the arrears werent added before
        cursor.execute(
            update_bill_query,
            {"outstanding_amount": outstanding_amount, "bill_id": bill_id},
        )
        ##### only sets the arrears to be the outstanding amount, you can also set the actual bill amount to the outstanding amount but it
        ##### won't logically make sense depends on what you want us to implement but there wasn't anything specified so i went with this
        ##### also if we call the function to show us the bill, the bill amount will be the same but the arrears would change
        # update_bill_query = """
        # UPDATE Bill
        # SET Arrears = Arrears + :outstanding_amount
        # WHERE BillID = :bill_id
        # """
        # cursor.execute(
        #     update_bill_query,
        #     {"outstanding_amount": outstanding_amount, "bill_id": bill_id},
        # )
        ## this is for viva if you ask me to change it, i just swapped both functions places
        
        connection.commit()
        
        payment_method_descriptions = {
                1: "Bank Transfer",
                2: "Cash",
                3: "Credit Card",}

        payment_method = payment_method_id 
        payment_method_description = payment_method_descriptions.get(payment_method,"something")
        print(f"Payment Method: {payment_method_description}")
        
        payment_dict = {
            "bill_id": bill_id,
            "amount": amount,
            "payment_method_id": payment_method_id,
            "payment_method_description": payment_method_description,
            "payment_date": payment_date,
            "payment_status": payment_status,
            "outstanding_amount": outstanding_amount,
        }
        
        return templates.TemplateResponse(
            "payment_receipt.html",
            {"request": request, "payment_details": payment_dict, "message": "Payment processed successfully!", "alert_type": "success"}
        )

    except oracledb.DatabaseError as e:
        logger.error(f"Database error: {e}")
        return templates.TemplateResponse(
            "bill_payment.html",
            {"request": request, "message": f"Database error: {str(e)}", "alert_type": "error"},
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

@app.post("/bill-retrieval", response_class=HTMLResponse)
async def post_bill_retrieval(
    request: Request,
    customer_id: str = Form(...),
    connection_id: str = Form(...),
    month: int = Form(...),
    year: int = Form(...)
):
    try:
        oracledb.init_oracle_client(lib_dir=os.environ.get("ORACLE_HOME"))
        connection = oracledb.connect(
            user=user_name,
            password=user_pswd,
            dsn=db_alias,
        )
        # if month < 0 or month > 12 or year < 1500 or year > 2024:
        #     return templates.TemplateResponse(
        #             "bill_retrieval.html",
        #             {"request": request, "message": "Invalid month or year", "alert_type": "error"},
        #         )
        #month and year are string so i converted them to int
        cursor = connection.cursor()
        customer_query = """
            SELECT FirstName, LastName, Address, PhoneNumber, Email
            FROM Customers WHERE CustomerID = :customer_id
        """
        cursor.execute(customer_query, {"customer_id": customer_id})
        customer_result = cursor.fetchone()

        if not customer_result:
            return templates.TemplateResponse(
                "bill_retrieval.html",
                {"request": request, "message": "Customer not found! Re-enter correct Customer ID", "alert_type": "error"},
            )

        first_name, last_name, customer_address, customer_phone, customer_email = customer_result
        customer_name = first_name + ' ' + last_name

        connection_query = """
            SELECT c.ConnectionTypeCode, d.DivisionName, d.SubDivName, c.InstallationDate, c.MeterType
            FROM Connections c
            JOIN DivInfo d ON c.DivisionID = d.DivisionID AND c.SubDivID = d.SubDivID
            WHERE c.ConnectionID = :connection_id
        """
        cursor.execute(connection_query, {"connection_id": connection_id})
        connection_result = cursor.fetchone()

        if not connection_result:
            return templates.TemplateResponse(
                "bill_retrieval.html",
                {"request": request, "message": "Connection not found! Re-enter correct Connection ID", "alert_type": "error"},
            )
        print('hello')
        
        connection_type_code, division_name, subdivision_name, installation_date, meter_type = connection_result
        connection_type_query = """
            SELECT Description FROM ConnectionTypes WHERE ConnectionTypeCode = :connection_type_code 
        """
        cursor.execute(connection_type_query, {"connection_type_code": connection_type_code})
        connection_type_result = cursor.fetchone()
        connection_type = connection_type_result[0] if connection_type_result else "Unknown"

        bill_query = """
            SELECT BillIssueDate, Net_PeakUnits, Net_OffPeakUnits, DueDate, TotalAmount_BeforeDueDate, TotalAmount_AfterDueDate,
                   Arrears, FixedFee, TaxAmount
            FROM Bill
            WHERE ConnectionID = :connection_id AND BillingMonth = :month AND BillingYear = :year
        """
        cursor.execute(
            bill_query,
            {"connection_id": connection_id, "month": month, "year": year},
        )
        bill_result = cursor.fetchone()

        if not bill_result:
            return templates.TemplateResponse(
                "bill_retrieval.html",
                {"request": request, "message": "Bill not found for the specified month and year!", "alert_type": "error"},
            )

        (
            issue_date,
            net_peak_units,
            net_off_peak_units,
            due_date,
            bill_amount, #this is the bill apparently
            amount_after_due_date,
            arrears_amount,
            fixed_fee_amountb,
            tax_amount,
        ) = bill_result
        ################ Ndont know what formula to implement
        tariff_query = """
            SELECT 
                t.TarrifDescription AS TariffName,
                b.Import_PeakUnits + b.Import_OffPeakUnits AS Units,
                t.RatePerUnit AS Rate,
                (b.Import_PeakUnits + b.Import_OffPeakUnits) * t.RatePerUnit AS Amount  -- from the project 2 manual
            FROM 
                Tariff t
            JOIN
                ConnectionTypes ct ON ct.ConnectionTypeCode = t.ConnectionTypeCode
            JOIN 
                Connections c ON c.ConnectionTypeCode = ct.ConnectionTypeCode
            JOIN 
                Bill b ON b.ConnectionID = c.ConnectionID
            WHERE 
                b.ConnectionID = :connection_id
                AND b.BillingMonth = :month
                AND b.BillingYear = :year
                AND (b.Import_PeakUnits + b.Import_OffPeakUnits) IS NOT NULL
        """
        cursor.execute(
            tariff_query,
            {"connection_id": connection_id, "month": month, "year": year},
        )

        tariffs = [
            {"name": tariff_name, "units": units, "rate": rate, "amount": amount}
            for tariff_name, units, rate, amount in cursor.fetchall()
        ]

        ################
        
        tax_query = """
        SELECT 
            ta.AuthorityName AS TaxDescription,
            tr.Rate AS TaxRate,
            b.TotalAmount_BeforeDueDate * tr.Rate AS TaxAmount
        FROM 
            TaxRates tr
        JOIN 
            TaxAuthority ta ON ta.TaxAuthorityID = tr.TaxAuthorityID
        JOIN 
            Connections c ON c.ConnectionTypeCode = tr.ConnectionTypeCode
        JOIN 
            Bill b ON b.ConnectionID = c.ConnectionID
        WHERE 
            c.ConnectionID = :connection_id
            AND b.BillingMonth = :month
            AND b.BillingYear = :year
            AND b.ConnectionID = :connection_id
        """
        cursor.execute(
            tax_query,
            {"connection_id": connection_id, "month": month, "year": year},
        )

        taxes = [
            {"name": tax_description, "rate": tax_rate, "amount": tax_amount}
            for tax_description, tax_rate, tax_amount in cursor.fetchall()
        ]

        subsidy_query = """
            SELECT SUBSIDYCODE, PROVIDERID, RatePerUnit
            FROM Subsidy
            WHERE ConnectionTypeCode = :connection_type_code
        """
        cursor.execute(subsidy_query, {"connection_type_code": connection_type_code})
        subsidies = [
            {"name": provider_name, "provider_name": ProviderID, "rate_per_unit": rate_per_unit}
            for provider_name, ProviderID, rate_per_unit in cursor.fetchall()
        ]

        fixed_fee_query = """
        SELECT 
            fc.FixedChargeType ,
            fc.FixedFee
        FROM 
            FixedCharges fc
        JOIN 
            ConnectionTypes c ON c.ConnectionTypeCode = fc.ConnectionTypeCode
        JOIN 
            TaxAuthority ta ON ta.TaxAuthorityID = fc.TaxAuthorityID
        WHERE 
            c.ConnectionTypeCode = :connection_type_code
        """
        cursor.execute(
            fixed_fee_query,{"connection_type_code": connection_type_code},)
        fixed_fees = [
            {"name": fixed_fee_description, "amount": fixed_fee_amount}
            for fixed_fee_description, fixed_fee_amount in cursor.fetchall()
        ]

        history_query = """
            SELECT 
                b.BillingMonth, 
                b.BillingYear, 
                b.TotalAmount_BeforeDueDate,  -- Fetch TotalAmount_BeforeDueDate instead of BillAmount
                b.DueDate, 
                p.PaymentStatus  -- Extract PaymentStatus from PaymentDetails table
            FROM 
                Bill b
            LEFT JOIN 
                PaymentDetails p ON b.BillID = p.BillID  -- Change the join condition to use BillID
            WHERE 
                b.ConnectionID = :connection_id
            ORDER BY 
                b.BillingYear DESC, b.BillingMonth DESC
            FETCH FIRST 10 ROWS ONLY
        """
        cursor.execute(history_query, {"connection_id": connection_id})
        billing_history = [
            {"month": month, "year": year, "amount": amount, "due_date": due_date, "status": status}
            for month, year, amount, due_date, status in cursor.fetchall()
        ]
        #print('bruh')

        bill_details = {
            "customer_id": customer_id,
            "connection_id": connection_id,
            "customer_name": customer_name,
            "customer_address": customer_address,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "connection_type": connection_type,
            "division": division_name,
            "subdivision": subdivision_name,
            "installation_date": installation_date,
            "meter_type": meter_type,
            "issue_date": issue_date,
            "net_peak_units": net_peak_units,
            "net_off_peak_units": net_off_peak_units,
            "bill_amount": bill_amount,
            "due_date": due_date,
            "amount_after_due_date": amount_after_due_date,
            "month": month,
            "arrears_amount": arrears_amount,
            "fixed_fee_amount": fixed_fee_amountb,
            "tax_amount": tax_amount,
            "tariffs": tariffs,
            "taxes": taxes,
            "subsidies": subsidies,
            "fixed_fee": fixed_fees,
            "bills_prev": billing_history,
        }

    except oracledb.Error as e:
        return templates.TemplateResponse(
            "bill_retrieval.html",
            {"request": request, "message": f"Database error: {str(e)}", "alert_type": "error"},
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

    return templates.TemplateResponse("bill_details.html", {"request": request, "bill_details": bill_details})

############## IT FINALLY WORKS, check for tweaks here and there

@app.post("/bill-adjustments", response_class=HTMLResponse)
async def post_bill_adjustments(
    request: Request,
    bill_id: int = Form(...),
    officer_name: str = Form(...),
    officer_designation: str = Form(...),
    original_bill_amount: float = Form(...),
    adjustment_amount: float = Form(...),
    adjustment_reason: str = Form(...),
):
    try:
        oracledb.init_oracle_client(lib_dir=os.environ.get("ORACLE_HOME"))
        connection = oracledb.connect(
            user=user_name,
            password=user_pswd,
            dsn=db_alias,
        )
        #why does the user need to input the original bill amount if the original bill amount is already in the database as the beforeduedate value?
        #we can have a check for the original bill amount, so that if it doesnt match, it gives an error, but we havent been told to implement that
        cursor = connection.cursor()
        adjustment_id = int(str(uuid.uuid4().int)[:5]) # constraint to only have intergers as the id of length 5 (length not a constraint i just like it)
        adjustment_date = datetime.datetime.now()
        result = cursor.callfunc(
            "fun_adjust_Bill",
            int,  # if 1 then works, if -1 then no
            [
                adjustment_id,          # p_AdjustmentID
                bill_id,                # p_BillID
                adjustment_date,        # p_AdjustmentDate
                officer_name,           # p_OfficerName
                officer_designation,    # p_OfficerDesignation
                original_bill_amount,   # p_OriginalBillAmount
                adjustment_amount,      # p_AdjustmentAmount
                adjustment_reason,      # p_AdjustmentReason
            ],
        )

        bill_update_query = """
            UPDATE Bill
            SET AdjustmentAmount = :adjustment_amount
            WHERE BillID = :bill_id
        """
        
        cursor.execute(
            bill_update_query,
            {
                "adjustment_amount": adjustment_amount,
                "bill_id": bill_id,
            },
        )            
        
        if result == 1:
            #print('hello')
            connection.commit()
        else:
            return templates.TemplateResponse(
                            "bill_adjustment.html",
                            {"request": request,
                            "message": "Bill not found! Bill ID Invalid! sahi wala daalo", 
                            "alert_type": "error"},
                        )
        adjustment_details = {
            "adjustment_id": adjustment_id,
            "bill_id": bill_id,
            "officer_name": officer_name,
            "officer_designation": officer_designation,
            "original_bill_amount": original_bill_amount,
            "adjustment_amount": adjustment_amount,
            "adjustment_reason": adjustment_reason,
            "adjustment_date": adjustment_date,
        }

        return templates.TemplateResponse(
            "bill_adjustment.html",
            {"request": request, "adjustment_details": adjustment_details, "message": "Adjustment processed successfully!", "alert_type": "success"}
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)