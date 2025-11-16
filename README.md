# 📘 Daftar Accounts

A desktop application for managing customer accounts (ledger system) built using **Python + PySide6** with full **Arabic UI** and RTL support.  
The app allows you to add customers, record transactions, calculate totals, print PDF statements, and export CSV files.

---

## 🚀 Features

### 👥 Customer Management

- Add new customers  
- Rename existing customers  
- Delete a customer (including all transactions)  
- Real-time search  
- Display total balance for each customer  

### 💳 Transaction Management

- Add new transactions:
  - Date  
  - Description  
  - Amount  
  - Type: Purchase (positive) or Payment (negative)
- Delete transactions  
- Automatic total calculation  
- Arabic RTL interface with large readable fonts

### 📄 Export Options

- Export customer transactions to **CSV**
- Generate beautifully formatted **PDF account statements**  
  Supports:
  - Arabic text shaping (`arabic_reshaper`)
  - Bidi text (`python-bidi`)
  - Custom Arabic fonts

### 🗄️ Database

- SQLite database with:
  - `customers` table
  - `transactions` table

The database and config files are stored in:

```
~/.daftar_accounts/
```

---

## 📦 Installation

### 1. Clone the project

```bash
git clone https://github.com/yourusername/daftar-accounts.git
cd daftar-accounts
```

### 2. Install dependencies

```bash
pip install PySide6 reportlab arabic_reshaper python-bidi
```

### 3. Run the application

```bash
python3 QT_Application.py
```

---

## 📁 Project Structure

```
.
├── main.py                # Main application code
├── fonts/                 # (Optional) Arabic fonts for PDF generation
├── accounts.db            # SQLite database (auto-created)
└── config.json            # Saved window geometry
```

---

## 🧱 Database Schema

### **customers**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Customer name |

### **transactions**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| customer_id | INTEGER | Foreign key → customers.id |
| date | TEXT | YYYY-MM-DD |
| description | TEXT | Description of transaction |
| amount | REAL | Positive = purchase, Negative = payment |
| kind | TEXT | "Purchase" or "Payment" |

---

## 🖥️ Application Interface

### Main Components

- **Customer List Page**
  - Add/Rename/Delete customer  
  - Open customer account  
  - Search field  
  - Total per customer  

- **Customer Account Page**
  - Add/Delete transactions  
  - Print PDF  
  - Export CSV  
  - Display grand total  

---

## 🔑 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl + N** | Add new customer |
| **Ctrl + T** | Add new transaction |
| **Delete** | Delete selected customer or transaction |
| **Enter** | Confirm dialog |
| **Escape** | Cancel dialog |

---

## 📄 PDF Generation Details

PDF statements are generated using **ReportLab** with full Arabic support using:

- `arabic_reshaper`
- `python-bidi`
- Registered Arabic fonts (e.g., Noto Naskh Arabic)

Styled table includes:

| Field | Formatting |
|-------|------------|
| Date | RTL-friendly |  
| Description | Arabic reshaped |  
| Amount | Positive/Negative formatting |  
| Type | Purchase / Payment |  

A grand total row is added at the bottom.

---

## 📊 CSV Export

Exports a UTF-8 CSV file containing:

- Date  
- Description  
- Amount  
- Type  

Compatible with Excel and LibreOffice.

---

## 🔧 Configuration Files

- **config.json** — saves window size & position  
- **accounts.db** — SQLite database  

Both automatically created at first launch.

---

## 🧩 Future Improvements (Optional)

- Add phone/address for customers  
- Backup/restore functionality  
- Advanced filtering and sorting  
- Dark mode  
- Packaging as `.exe` or `.AppImage`

---

## 📜 License

You may apply your preferred license (MIT recommended).

---

## ❤️ Author

Developed by **Abdallah**.
