import sys
import sqlite3
import csv
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QDialog,
    QLineEdit, QRadioButton, QButtonGroup, QFormLayout, QMessageBox,
    QHeaderView, QDateEdit, QSpacerItem, QSizePolicy, QStackedWidget,
    QFileDialog
)
from PySide6.QtCore import Qt, QDate, QSize, QPoint
from PySide6.QtGui import QFont, QKeySequence, QShortcut

# PDF generation imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Application data paths
APP_DIR = Path.home() / ".daftar_accounts"
DB_PATH = APP_DIR / "accounts.db"
CONFIG_PATH = APP_DIR / "config.json"
APP_DIR.mkdir(exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            kind TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)
    conn.commit()
    return conn


def format_amount(amount):
    # format with thousands separator and two decimals, keep parentheses for negative
    if amount >= 0:
        return f"{amount:,.2f}"
    else:
        return f"({abs(amount):,.2f})"


from PySide6.QtWidgets import QMessageBox

def styled_message_box(parent, title, text, icon=QMessageBox.Information,buttons=QMessageBox.Ok, default_button=QMessageBox.NoButton):
    mb = QMessageBox(parent)
    mb.setWindowTitle(title)
    mb.setText(text)
    mb.setIcon(icon)
    mb.setStandardButtons(buttons)
    if default_button != QMessageBox.NoButton:
        mb.setDefaultButton(default_button)

    mb.setStyleSheet("""
        QMessageBox {
            background-color: #ffffff;
            color: #1e272e;
            font-family: 'Noto Naskh Arabic', 'Amiri', 'Sans';
            font-size: 14pt;
        }
        QMessageBox QLabel {
            color: #1e272e;
            font-size: 14pt;
            font-weight: bold;
        }
        QMessageBox QPushButton {
            min-width: 110px;
            min-height: 36px;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13pt;
            font-weight: bold;
        }
        QPushButton#yesBtn    { background-color: #27ae60; color: white; }
        QPushButton#noBtn     { background-color: #e74c3c; color: white; }
        QPushButton#okBtn     { background-color: #3498db; color: white; }
        QPushButton#cancelBtn { background-color: #95a5a6; color: white; }
    """)

    btn_map = {}
    if buttons & QMessageBox.Yes:
        b = mb.button(QMessageBox.Yes)
        b.setText("نعم")
        b.setObjectName("yesBtn")
        btn_map['yes'] = b
    if buttons & QMessageBox.No:
        b = mb.button(QMessageBox.No)
        b.setText("لا")
        b.setObjectName("noBtn")
        btn_map['no'] = b
    if buttons & QMessageBox.Ok:
        b = mb.button(QMessageBox.Ok)
        b.setText("موافق")
        b.setObjectName("okBtn")
        btn_map['ok'] = b
    if buttons & QMessageBox.Cancel:
        b = mb.button(QMessageBox.Cancel)
        b.setText("إلغاء")
        b.setObjectName("cancelBtn")
        btn_map['cancel'] = b

    return mb.exec(), btn_map


class TextInputDialog(QDialog):
    def __init__(self, title, label_text, initial_text=""):
        super().__init__()
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(420, 180)

        layout = QVBoxLayout(self)
        header = QLabel(title)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("background-color:#3498db; color:white; padding:8px;")
        header.setFont(QFont("Sans", 14, QFont.Bold))
        layout.addWidget(header)

        form = QVBoxLayout()
        lbl = QLabel(label_text)
        lbl.setAlignment(Qt.AlignRight)
        lbl.setFont(QFont("Sans", 12))
        form.addWidget(lbl)

        self.edit = QLineEdit()
        self.edit.setLayoutDirection(Qt.RightToLeft)
        self.edit.setAlignment(Qt.AlignRight)
        self.edit.setText(initial_text)
        self.edit.setFont(QFont("Sans", 13, QFont.Bold))
        self.edit.setStyleSheet("padding:6px;")
        form.addWidget(self.edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("حفظ")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.edit.setFocus()

    def get_text(self):
        if self.exec() == QDialog.Accepted:
            return self.edit.text().strip()
        return None


class TransactionDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("إضافة عملية جديدة")
        self.setModal(True)
        self.resize(650, 550)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("إضافة عملية جديدة")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            background-color:#3498db; 
            color:white; 
            padding:20px; 
            border-radius:12px;
            font-size:28pt;
            font-weight:bold;
        """)
        main_layout.addWidget(header)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(25)
        form_layout.setContentsMargins(20, 20, 20, 20)

        kind_label = QLabel("نوع العملية:")
        kind_label.setStyleSheet("font-size:22pt; font-weight:bold; color:#2c3e50;")

        self.kind_group = QButtonGroup(self)
        buy_radio = QRadioButton("شراء (يزيد على الحساب)")
        pay_radio = QRadioButton("دفع (ينقص من الحساب)")
        buy_radio.setChecked(True)

        for r in (buy_radio, pay_radio):
            r.setStyleSheet("font-size:22pt; font-weight:bold; color:#2c3e50;")

        self.kind_group.addButton(buy_radio, 1)
        self.kind_group.addButton(pay_radio, 2)

        kind_box = QVBoxLayout()
        kind_box.addWidget(buy_radio)
        kind_box.addWidget(pay_radio)
        form_layout.addRow(kind_label, kind_box)

        self.desc_edit = QLineEdit()
        self.desc_edit.setStyleSheet(
            "padding:18px; font-size:22pt; font-weight:bold; border:3px solid #bdc3c7; border-radius:12px;"
        )
        form_layout.addRow(QLabel("البيان:"), self.desc_edit)

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setStyleSheet(
            "padding:18px; font-size:22pt; font-weight:bold; border:3px solid #bdc3c7; border-radius:12px;"
        )
        form_layout.addRow(QLabel("المبلغ:"), self.amount_edit)

        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setStyleSheet(
            "padding:18px; font-size:22pt; font-weight:bold; border:3px solid #bdc3c7; border-radius:12px;"
        )
        form_layout.addRow(QLabel("التاريخ:"), self.date_edit)

        main_layout.addWidget(form_widget)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("حفظ العملية")
        save_btn.setObjectName("saveBtn")
        save_btn.setStyleSheet("font-size:24pt; padding:20px 60px; min-width:220px;")
        save_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setStyleSheet("font-size:24pt; padding:20px 60px; min-width:220px;")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)
        self.desc_edit.setFocus()
        # Enter To save Transaction
        self.desc_edit.returnPressed.connect(self.accept)
        self.amount_edit.returnPressed.connect(self.accept)
        self.date_edit.returnPressed.connect(self.accept)

        # Escape to cancel
        QShortcut(QKeySequence("Escape"), self, activated=self.reject)

    def get_data(self):
        if self.exec() != QDialog.Accepted:
            return None

        desc = self.desc_edit.text().strip()
        amount_str = self.amount_edit.text().strip()
        date_str = self.date_edit.date().toString("yyyy-MM-dd")

        if not desc or not amount_str:
            styled_message_box(self, "تنبيه", "الرجاء ملء البيان والمبلغ",icon=QMessageBox.Warning, buttons=QMessageBox.Ok)
            return None

        try:
            amount = float(amount_str.replace(",", "."))
            if amount <= 0:
                raise ValueError
        except ValueError:
            styled_message_box(self, "خطأ", "المبلغ يجب أن يكون رقماً أكبر من صفر",icon=QMessageBox.Critical, buttons=QMessageBox.Ok)
            return None

        kind_id = self.kind_group.checkedId()
        kind = "شراء" if kind_id == 1 else "دفع"
        signed_amount = amount if kind == "شراء" else -amount
        return date_str, desc, signed_amount, kind
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.accept()
            return

        if event.key() == Qt.Key_Escape:
            self.reject()
            return

        super().keyPressEvent(event)



class MainWindow(QMainWindow):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.current_customer_id = None

        self.setWindowTitle("Daftar Accounts")
        self.resize(1100, 720)

        self.load_window_geometry()

        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        self.page_list = QWidget()
        self.setup_list_page()
        self.stacked.addWidget(self.page_list)

        self.page_customer = QWidget()
        self.setup_customer_page()
        self.stacked.addWidget(self.page_customer)

        self.stacked.setCurrentWidget(self.page_list)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.add_customer)
        QShortcut(QKeySequence("Delete"), self, activated=self.global_delete_shortcut)

    def save_window_geometry(self):
        cfg = {}
        try:
            geom = self.geometry()
            cfg["x"] = geom.x()
            cfg["y"] = geom.y()
            cfg["w"] = geom.width()
            cfg["h"] = geom.height()
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def load_window_geometry(self):
        try:
            if CONFIG_PATH.exists():
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if all(k in cfg for k in ("x", "y", "w", "h")):
                    self.setGeometry(cfg["x"], cfg["y"], cfg["w"], cfg["h"])
        except Exception:
            pass

    def closeEvent(self, event):
        res, _ = styled_message_box(self, "تأكيد الخروج", "هل تريد الخروج؟",
                                    icon=QMessageBox.Question,
                                    buttons=QMessageBox.Yes | QMessageBox.No,
                                    default_button=QMessageBox.No)
        if res == QMessageBox.Yes:
            try:
                self.conn.close()
            except Exception:
                pass
            self.save_window_geometry()
            event.accept()
        else:
            event.ignore()

    def setup_list_page(self):
        layout = QVBoxLayout(self.page_list)

        top_bar = QWidget()
        top_bar.setStyleSheet("background-color:#1a252f;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 8, 12, 8)

        self.btn_add_customer = QPushButton("إضافة زبون ➕")
        self.btn_add_customer.setObjectName("addBtn")
        self.btn_add_customer.clicked.connect(self.add_customer)

        self.btn_rename_customer = QPushButton("تعديل الاسم ✏️")
        self.btn_rename_customer.setObjectName("renameBtn")
        self.btn_rename_customer.clicked.connect(self.rename_customer)

        self.btn_delete_customer = QPushButton("حذف زبون 🗑️")
        self.btn_delete_customer.setObjectName("deleteBtn")
        self.btn_delete_customer.clicked.connect(self.delete_customer)

        title_label = QLabel("حسابات الزبائن")
        title_label.setFont(QFont("Sans", 18, QFont.Bold))
        title_label.setStyleSheet("color:#ecf0f1;")

        top_layout.addWidget(self.btn_add_customer)
        top_layout.addWidget(self.btn_rename_customer)
        top_layout.addWidget(self.btn_delete_customer)
        top_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        top_layout.addWidget(title_label)

        layout.addWidget(top_bar)

        # search bar
        search_bar = QWidget()
        search_layout = QHBoxLayout(search_bar)
        search_layout.setContentsMargins(12, 6, 12, 6)
        lbl_search = QLabel("بحث:")
        lbl_search.setFixedWidth(40)
        lbl_search.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("اكتب اسم الزبون للبحث...")
        self.search_edit.textChanged.connect(self.load_customers)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(lbl_search)
        layout.addWidget(search_bar)

        list_label = QLabel("قائمة الزبائن وحساباتهم")
        list_label.setFont(QFont("Sans", 14, QFont.Bold))
        list_label.setAlignment(Qt.AlignRight)
        list_label.setStyleSheet("color:#2c3e50; margin:6px 12px 0 12px;")
        layout.addWidget(list_label)

        self.table_customers = QTableWidget()
        self.table_customers.setColumnCount(2)
        self.table_customers.setHorizontalHeaderLabels(["الاسم", "الإجمالي (جنيه)"])
        self.table_customers.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_customers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_customers.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_customers.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_customers.setAlternatingRowColors(True)
        self.table_customers.setFont(QFont("Sans", 13, QFont.Bold))
        self.table_customers.verticalHeader().setVisible(False)
        self.table_customers.doubleClicked.connect(self.open_customer)
        layout.addWidget(self.table_customers)

        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("background-color:#2c3e50;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(12, 8, 12, 8)

        self.btn_open = QPushButton("فتح الحساب 📂")
        self.btn_open.setObjectName("openBtn")
        self.btn_open.setFixedWidth(220)
        self.btn_open.clicked.connect(self.open_customer)
        bottom_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        bottom_layout.addWidget(self.btn_open)
        layout.addWidget(bottom_bar)

        self.load_customers()

    def setup_customer_page(self):
        layout = QVBoxLayout(self.page_customer)

        top_bar = QWidget()
        top_bar.setStyleSheet("background-color:#16a085;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 8, 12, 8)

        btn_back = QPushButton("الرجوع إلى القائمة")
        btn_back.setObjectName("addBtn")
        btn_back.setFixedWidth(220)
        btn_back.clicked.connect(self.back_to_list)

        self.name_label = QLabel("حساب الزبون")
        self.name_label.setObjectName("name_label")
        self.name_label.setFont(QFont("Sans", 18, QFont.Bold))
        self.name_label.setStyleSheet("color:white;")

        btn_add = QPushButton("إضافة عملية ➕")
        btn_add.setObjectName("addBtn")
        btn_add.clicked.connect(self.add_transaction)
        # Shortcut Ctrl+T to add transaction
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self.add_transaction)

        btn_del = QPushButton("حذف عملية 🗑️")
        btn_del.setObjectName("deleteBtn")
        btn_del.clicked.connect(self.delete_transaction)

        btn_print = QPushButton("طباعة كشف الحساب")
        btn_print.setStyleSheet("""
            background-color:#e67e22; color:white; padding:8px 12px;
            border-radius:8px; font-weight:bold; font-size:12pt;
        """)
        btn_print.clicked.connect(self.print_account_statement)

        btn_export_csv = QPushButton("تصدير CSV")
        btn_export_csv.setStyleSheet("background-color:#2d98da; color:white; padding:8px 12px; border-radius:8px;")
        btn_export_csv.clicked.connect(self.export_transactions_csv)

        top_layout.addWidget(btn_back)
        top_layout.addWidget(btn_add)
        top_layout.addWidget(btn_del)
        top_layout.addWidget(btn_print)
        top_layout.addWidget(btn_export_csv)
        top_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        top_layout.addWidget(self.name_label)
        layout.addWidget(top_bar)

        self.table_transactions = QTableWidget()
        self.table_transactions.setColumnCount(4)
        self.table_transactions.setHorizontalHeaderLabels(["التاريخ", "البيان", "المبلغ (جنيه)", "النوع"])
        self.table_transactions.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_transactions.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_transactions.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_transactions.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_transactions.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_transactions.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_transactions.setAlternatingRowColors(True)
        self.table_transactions.setFont(QFont("Sans", 12, QFont.Bold))
        self.table_transactions.verticalHeader().setVisible(False)
        layout.addWidget(self.table_transactions)

        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("background-color:#2c3e50;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(12, 8, 12, 8)

        self.total_label = QLabel("الإجمالي الحالي: 0.00 جنيه")
        self.total_label.setFont(QFont("Sans", 16, QFont.Bold))
        self.total_label.setStyleSheet("color:white;")

        bottom_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        bottom_layout.addWidget(self.total_label)
        layout.addWidget(bottom_bar)

    def back_to_list(self):
        self.stacked.setCurrentWidget(self.page_list)
        self.load_customers()

    def open_customer(self):
        row = self.table_customers.currentRow()
        if row < 0:
            styled_message_box(self, "تنبيه", "الرجاء اختيار زبون أولاً",
                               icon=QMessageBox.Warning, buttons=QMessageBox.Ok)
            return

        item = self.table_customers.item(row, 0)
        self.current_customer_id = item.data(Qt.UserRole)

        c = self.conn.cursor()
        c.execute("SELECT name FROM customers WHERE id = ?", (self.current_customer_id,))
        r = c.fetchone()
        if not r:
            styled_message_box(self, "خطأ", "الزبون غير موجود", icon=QMessageBox.Critical, buttons=QMessageBox.Ok)
            return
        name = r[0]
        self.name_label.setText(f"حساب الزبون: {name}")
        self.load_transactions()
        self.stacked.setCurrentWidget(self.page_customer)

    def load_customers(self):
        search = self.search_edit.text().strip() if hasattr(self, "search_edit") else ""
        c = self.conn.cursor()
        if search:
            # Simple protection against SQL injection via parameters
            q = """
                SELECT customers.id, customers.name,
                IFNULL(SUM(transactions.amount), 0) as total
                FROM customers
                LEFT JOIN transactions ON customers.id = transactions.customer_id
                WHERE customers.name LIKE ?
                GROUP BY customers.id, customers.name
                ORDER BY customers.id DESC
            """
            rows = c.execute(q, (f"%{search}%",)).fetchall()
        else:
            q = """
                SELECT customers.id, customers.name,
                IFNULL(SUM(transactions.amount), 0) as total
                FROM customers
                LEFT JOIN transactions ON customers.id = transactions.customer_id
                GROUP BY customers.id, customers.name
                ORDER BY customers.id DESC
            """
            rows = c.execute(q).fetchall()

        self.table_customers.setRowCount(len(rows))
        for row_idx, (cid, name, total) in enumerate(rows):
            item_name = QTableWidgetItem(name)
            item_name.setData(Qt.UserRole, cid)
            item_name.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            item_name.setFont(QFont("Noto Naskh Arabic", 22, QFont.Bold))

            item_total = QTableWidgetItem(format_amount(total))
            item_total.setTextAlignment(Qt.AlignCenter)
            item_total.setFont(QFont("Sans", 18, QFont.Bold))

            self.table_customers.setItem(row_idx, 0, item_name)
            self.table_customers.setItem(row_idx, 1, item_total)

    def load_transactions(self):
        if not self.current_customer_id:
            return

        c = self.conn.cursor()
        c.execute("""
            SELECT id, date, description, amount, kind
            FROM transactions
            WHERE customer_id = ?
            ORDER BY date DESC, id DESC
        """, (self.current_customer_id,))
        rows = c.fetchall()

        self.table_transactions.setRowCount(len(rows))
        total = 0.0

        for row_idx, (tid, date, desc, amount, kind) in enumerate(rows):
            total += amount

            item_date = QTableWidgetItem(date)
            item_desc = QTableWidgetItem(desc)
            amount_str = f"+ {format_amount(amount)}" if amount > 0 else f"- {format_amount(abs(amount))}"
            item_amount = QTableWidgetItem(amount_str)
            item_kind = QTableWidgetItem(kind)

            item_date.setData(Qt.UserRole, tid)

            for it in (item_date, item_amount, item_kind):
                it.setTextAlignment(Qt.AlignCenter)
                it.setFont(QFont("Noto Naskh Arabic", 18, QFont.Bold))

            item_desc.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            item_desc.setFont(QFont("Noto Naskh Arabic", 20, QFont.Bold))

            self.table_transactions.setItem(row_idx, 0, item_date)
            self.table_transactions.setItem(row_idx, 1, item_desc)
            self.table_transactions.setItem(row_idx, 2, item_amount)
            self.table_transactions.setItem(row_idx, 3, item_kind)

        if total > 0:
            text = f"المبلغ المستحق: {format_amount(total)} جنيه"
            color = "#e74c3c"
        elif total < 0:
            text = f"رصيد زائد للزبون: {format_amount(abs(total))} جنيه"
            color = "#27ae60"
        else:
            text = "الحساب متساوي"
            color = "#95a5a6"

        self.total_label.setText(text)
        self.total_label.setStyleSheet(f"color:{color};")

    def add_transaction(self):
        if not self.current_customer_id:
            styled_message_box(self, "تنبيه", "افتح حساب زبون أولاً", QMessageBox.Warning)
            return
        dlg = TransactionDialog()
        data = dlg.get_data()
        if not data:
            return
        date_str, desc, amount, kind = data

        c = self.conn.cursor()
        c.execute(
            "INSERT INTO transactions (customer_id, date, description, amount, kind) VALUES (?, ?, ?, ?, ?)",
            (self.current_customer_id, date_str, desc, amount, kind)
        )
        self.conn.commit()
        self.load_transactions()

    def delete_transaction(self):
        row = self.table_transactions.currentRow()
        if row < 0:
            styled_message_box(self, "تنبيه", "اختر عملية لحذفها",
                               icon=QMessageBox.Warning, buttons=QMessageBox.Ok)
            return

        res, _ = styled_message_box(
            self, "تأكيد", "حذف العملية؟",
            icon=QMessageBox.Question,
            buttons=QMessageBox.Yes | QMessageBox.No,
            default_button=QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return

        tid = self.table_transactions.item(row, 0).data(Qt.UserRole)
        c = self.conn.cursor()
        c.execute("DELETE FROM transactions WHERE id = ?", (tid,))
        self.conn.commit()
        self.load_transactions()

    def add_customer(self):
        dlg = TextInputDialog("إضافة زبون", "اسم الزبون الجديد:")
        name = dlg.get_text()
        if name:
            # Simple duplicate prevention
            c = self.conn.cursor()
            c.execute("SELECT id FROM customers WHERE name = ?", (name,))
            if c.fetchone():
                styled_message_box(self, "تنبيه", "اسم الزبون موجود بالفعل", QMessageBox.Warning)
                return
            c.execute("INSERT INTO customers (name) VALUES (?)", (name,))
            self.conn.commit()
            self.load_customers()

    def rename_customer(self):
        row = self.table_customers.currentRow()
        if row < 0:
            styled_message_box(self, "تنبيه", "الرجاء اختيار زبون أولاً", QMessageBox.Warning)
            return

        cid = self.table_customers.item(row, 0).data(Qt.UserRole)

        c = self.conn.cursor()
        c.execute("SELECT name FROM customers WHERE id = ?", (cid,))
        r = c.fetchone()
        if not r:
            styled_message_box(self, "خطأ", "الزبون غير موجود", icon=QMessageBox.Critical, buttons=QMessageBox.Ok)
            return

        old_name = r[0]
        dlg = TextInputDialog("تعديل الاسم", "الاسم الجديد:", old_name)
        new_name = dlg.get_text()

        if new_name and new_name != old_name:
            # Check to ensure there is no duplicate name
            c.execute("SELECT id FROM customers WHERE name = ? AND id != ?", (new_name, cid))
            if c.fetchone():
                styled_message_box(self, "تنبيه", "اسم آخر بنفس الاسم موجود بالفعل", QMessageBox.Warning)
                return
            c.execute("UPDATE customers SET name = ? WHERE id = ?", (new_name, cid))
            self.conn.commit()
            self.load_customers()

    def delete_customer(self):
        row = self.table_customers.currentRow()
        if row < 0:
            styled_message_box(self, "تنبيه", "الرجاء اختيار زبون أولاً", QMessageBox.Warning)
            return

        cid = self.table_customers.item(row, 0).data(Qt.UserRole)

        res, _ = styled_message_box(
            self, "تأكيد الحذف", "حذف الزبون وكل عملياته؟",
            icon=QMessageBox.Question,
            buttons=QMessageBox.Yes | QMessageBox.No,
            default_button=QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return

        c = self.conn.cursor()
        c.execute("DELETE FROM transactions WHERE customer_id = ?", (cid,))
        c.execute("DELETE FROM customers WHERE id = ?", (cid,))
        self.conn.commit()
        self.load_customers()

    def print_account_statement(self):
        # Same as before — same PDF logic (better to keep as is)
        if not self.current_customer_id:
            styled_message_box(self, "تنبيه", "افتح حساب زبون أولاً", QMessageBox.Warning)
            return

        c = self.conn.cursor()
        c.execute("SELECT name FROM customers WHERE id = ?", (self.current_customer_id,))
        customer_name = c.fetchone()[0]

        c.execute("SELECT date, description, amount, kind FROM transactions WHERE customer_id = ? ORDER BY date ASC, id ASC",
                  (self.current_customer_id,))
        transactions = c.fetchall()

        if not transactions:
            styled_message_box(self, "تنبيه", "لا توجد عمليات لطباعتها", QMessageBox.Warning)
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ كشف الحساب", f"كشف حساب - {customer_name}.pdf", "ملفات PDF (*.pdf)"
        )
        if not file_path:
            return

        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
        except Exception:
            styled_message_box(self, "خطأ", "مكتبات arabic_reshaper و python-bidi مطلوبة للطباعة بشكل صحيح",
                               QMessageBox.Critical)
            return

        def ar(text):
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)

        # For Arabic font support
        noto_paths = [
            "fonts/NotoNaskhArabic-Regular.ttf",
            "fonts/NotoSansArabic-Regular.ttf",
            "fonts/DejaVuSans.ttf",
        ]
        font_path = next((p for p in noto_paths if Path(p).exists()), None)
        if not font_path:
            styled_message_box(self, "خطأ", "مش لاقي خط عربي! ركّب fonts-noto-arabic", QMessageBox.Critical)
            return

        pdfmetrics.registerFont(TTFont("Arabic", font_path))

        doc = SimpleDocTemplate(file_path, pagesize=A4,
                                rightMargin=18*mm, leftMargin=18*mm,
                                topMargin=20*mm, bottomMargin=20*mm)
        elements = []

        title_style = ParagraphStyle(
            name='Title',
            fontName='Arabic',
            fontSize=30,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor("#2c3e50"),
            leading=36
        )
        elements.append(Paragraph(ar(f"كشف حساب {customer_name}"), title_style))
        elements.append(Spacer(1, 8*mm))  # Small space before the table

        # Table data
        data = [[ar("التاريخ"), ar("البيان"), ar("المبلغ"), ar("النوع")]]
        total = 0.0
        for date, desc, amount, kind in transactions:
            total += amount
            amount_str = f"{amount:.2f}" if amount >= 0 else f"({abs(amount):.2f})"

            y, m, d = date.split("-")
            raw_date = f"{int(y):02d} / {int(m):02d} / {d}"
            nice_date = f"\u202A{raw_date}\u202C"

            data.append([
                ar(nice_date),
                ar(desc),
                ar(amount_str),
                ar(kind)
            ])

        total_str = f"{total:.2f} جنيه" if total >= 0 else f"({abs(total):.2f}) جنيه"
        data.append(["", ar(total_str), ar("إجمالي الحساب"), ""])

        table = Table(data, colWidths=[48*mm, 82*mm, 38*mm, 32*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Arabic'),
            ('FONTSIZE', (0, 0), (-1, 0), 16),
            ('FONTSIZE', (0, 1), (-1, -2), 15),
            ('FONTSIZE', (0, -1), (-1, -1), 18),
            ('GRID', (0, 0), (-1, -1), 1.4, colors.black),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor("#f8f9fa")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(table)

        try:
            doc.build(elements)
            styled_message_box(self, "تم بنجاح", f"تم حفظ كشف الحساب بنجاح!\n{file_path}", QMessageBox.Information)
        except Exception as e:
            styled_message_box(self, "خطأ", f"فشل في إنشاء الملف:\n{str(e)}", QMessageBox.Critical)

    def export_transactions_csv(self):
        if not self.current_customer_id:
            styled_message_box(self, "تنبيه", "افتح حساب زبون أولاً", QMessageBox.Warning)
            return

        c = self.conn.cursor()
        c.execute("SELECT name FROM customers WHERE id = ?", (self.current_customer_id,))
        customer_name = c.fetchone()[0]

        c.execute("SELECT date, description, amount, kind FROM transactions WHERE customer_id = ? ORDER BY date ASC, id ASC",
                  (self.current_customer_id,))
        transactions = c.fetchall()
        if not transactions:
            styled_message_box(self, "تنبيه", "لا توجد عمليات للتصدير", QMessageBox.Warning)
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "حفظ CSV", f"{customer_name}.csv", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["التاريخ", "البيان", "المبلغ", "النوع"])
                for date, desc, amount, kind in transactions:
                    writer.writerow([date, desc, f"{amount:.2f}", kind])
            styled_message_box(self, "تم", f"تم تصدير العمليات إلى:\n{file_path}", QMessageBox.Information)
        except Exception as e:
            styled_message_box(self, "خطأ", f"فشل في حفظ الملف:\n{str(e)}", QMessageBox.Critical)

    def global_delete_shortcut(self):
        # If the customer list page is visible → delete customer; if the customer account page is visible → delete transaction
        if self.stacked.currentWidget() == self.page_list:
            self.delete_customer()
        else:
            self.delete_transaction()


def main():
    conn = init_db()
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setFont(QFont("Noto Naskh Arabic", 20, QFont.Bold))

    app.setStyleSheet("""
        QWidget {
            background-color: #f8f9fa;
            color: #1e272e;
            font-family: 'Noto Naskh Arabic', 'Amiri', 'Tahoma', sans-serif;
        }
        QLabel {
            color: #1e272e;
            font-weight: bold;
        }
        QTableWidget {
            background-color: white;
            gridline-color: #dee2e6;
            alternate-background-color: #f1f3f5;
            selection-background-color: #3498db;
            selection-color: white;
        }
        QTableWidget::item {
            padding: 12px 8px;
            color: #1e272e;
        }
        QHeaderView::section {
            background-color: #2c3e50;
            color: white;
            padding: 14px;
            font-weight: bold;
            font-size: 18pt;
            border: none;
        }
        QPushButton {
            color: white;
            padding: 16px 28px;
            border-radius: 8px;
            border: none;
            font-weight: bold;
            font-size: 18pt;
            min-height: 50px;
        }
        QPushButton#addBtn      { background-color: #27ae60; }
        QPushButton#renameBtn   { background-color: #3498db; }
        QPushButton#deleteBtn   { background-color: #e74c3c; }
        QPushButton#openBtn     { background-color: #9b59b6; }
        QPushButton#saveBtn     { background-color: #27ae60; }
        QPushButton#cancelBtn   { background-color: #95a5a6; }
        QLineEdit, QDateEdit {
            padding: 14px;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            background: white;
            font-size: 18pt;
            color: #1e272e;
            font-weight: bold;
        }
        QLineEdit:focus, QDateEdit:focus {
            border: 2px solid #3498db;
        }
        QTableWidget::item, QLabel, QRadioButton, QDialog {
            color: #1e272e !important;
        }
        #name_label {
            color: white !important;
            font-size: 24pt !important;
        }
    """)

    window = MainWindow(conn)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
