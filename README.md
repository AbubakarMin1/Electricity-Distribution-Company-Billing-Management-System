# ⚡ Electricity Distribution Company – Billing Management System

A full-stack web application built for an electricity distribution company to manage customer billing operations. Developed as a project for **CS340 – Databases** at **Lahore University of Management Sciences (LUMS)**. The system connects a **FastAPI** backend to an **Oracle Database** and serves a Jinja2-templated frontend for three core billing operations.

---

## 🌟 Features

### Bill Retrieval
- Look up a customer's bill by Customer ID, Connection ID, month, and year
- Displays full customer details, connection info, billing summary, tariff breakdown, taxes, subsidies, fixed charges, and the last 10 bills of payment history

### Bill Payment
- Submit a payment against a Bill ID
- Automatically determines payment status (Fully Paid / Partially Paid) based on due date
- Updates outstanding balance in the database and generates a payment receipt
- Supports Bank Transfer, Cash, and Credit Card payment methods

### Bill Adjustment
- Officers can submit adjustments to existing bills with a reason and designation
- Calls a PL/SQL stored function (`fun_adjust_Bill`) in the Oracle DB
- Generates an adjustment receipt with a unique Adjustment ID

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | Oracle DB (via `python-oracledb` in Thick mode) |
| Templating | Jinja2 |
| Frontend | HTML, CSS (custom) |
| Server | Uvicorn |

---

## 📁 Project Structure

```
project/
│
├── app.py                   # Main FastAPI application & all route handlers
├── requirements.txt         # Python dependencies
│
├── static/
│   └── style.css            # Shared stylesheet
│
└── templates/
    ├── index.html           # Landing page / dashboard
    ├── bill_retrieval.html  # Bill retrieval form
    ├── bill_details.html    # Full bill details view
    ├── bill_payment.html    # Payment form
    ├── payment_receipt.html # Payment confirmation
    └── bill_adjustment.html # Adjustment form + receipt
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Oracle Database access with the relevant schema set up
- Oracle Instant Client installed locally (required for Thick mode)

### 1. Clone the repository
```bash
git clone https://github.com/AbubakarMin1/Electricity-Distribution-Company-Billing-Management-System.git
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set environment variables

The app reads credentials from environment variables. Create an `env.sh` file:

```bash
export DB_USERNAME="your_oracle_username"
export DB_PASSWORD="your_oracle_password"
export DB_ALIAS="your_db_alias_or_dsn"
export ORACLE_HOME="/path/to/oracle/instant/client"
```

Then source it:
```bash
source env.sh
```

### 4. Run the application
```bash
python app.py
```

The app will be available at `http://localhost:8000`.

---

## 🗄️ Database

The application connects to an Oracle Database in **Thick mode** using `python-oracledb`. The schema includes the following key tables:

| Table | Description |
|---|---|
| `Customers` | Customer personal information |
| `Connections` | Electricity connections per customer |
| `ConnectionTypes` | Connection types with associated tariff codes |
| `Bill` | Monthly bills per connection |
| `PaymentDetails` | Payment records linked to bills |
| `Tariff` | Rate per unit by connection type |
| `TaxRates` | Tax rates by authority and connection type |
| `TaxAuthority` | Tax authority names and IDs |
| `FixedCharges` | Fixed charges by connection type |
| `Subsidy` | Subsidy rates per connection type |
| `DivInfo` | Division and subdivision information |
| `BillAdjustments` | Adjustment records (managed via PL/SQL) |

A PL/SQL stored function `fun_adjust_Bill` handles bill adjustment logic on the database side.

---

## 🔌 API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/` | Landing page |
| GET | `/bill-payment` | Bill payment form |
| POST | `/bill-payment` | Process a payment |
| GET | `/bill-retrieval` | Bill retrieval form |
| POST | `/bill-retrieval` | Fetch and display bill details |
| GET | `/bill-adjustments` | Bill adjustment form |
| POST | `/bill-adjustments` | Submit a bill adjustment |
| GET | `/test-connection` | Test Oracle DB connectivity |

---

## ⚠️ Notes

- The Oracle Instant Client path must be correctly set via the `ORACLE_HOME` environment variable for Thick mode to work. Refer to the [python-oracledb documentation](https://python-oracledb.readthedocs.io/) for setup details.
- Database credentials are read entirely from environment variables — never hardcode them in `app.py`.
- A `.gitignore` is recommended to exclude your `env.sh` file from version control.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
