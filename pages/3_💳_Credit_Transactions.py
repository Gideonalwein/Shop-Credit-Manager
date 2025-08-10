# 3_💳_Credit_Transactions.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
from io import BytesIO
import os

# Try to import PDF libraries
_pdf_backend = None
try:
    # ReportLab preferred, import platypus helpers too
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    _pdf_backend = "reportlab"
except Exception:
    try:
        from fpdf import FPDF
        _pdf_backend = "fpdf"
    except Exception:
        _pdf_backend = None

# ---------- Config ----------
DB_PATH = "data/shop.db"
if not os.path.exists("data"):
    os.makedirs("data")

st.set_page_config(page_title="Credit Transactions", page_icon="💳", layout="wide")
st.title("💳 Credit Transactions — All-in-One")

# ---------- DB helpers & migration ----------
def create_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def migrate_schema():
    conn = create_connection()
    c = conn.cursor()

    # customers
    c.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # products
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # credit_transactions
    c.execute("""
    CREATE TABLE IF NOT EXISTS credit_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Unpaid',
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )""")

    # credit_items
    c.execute("""
    CREATE TABLE IF NOT EXISTS credit_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        FOREIGN KEY (transaction_id) REFERENCES credit_transactions(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )""")

    # payments
    c.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (transaction_id) REFERENCES credit_transactions(id)
    )""")

    conn.commit()
    conn.close()

# Recalculate and update transaction status
def recalc_balance(transaction_id):
    conn = create_connection()
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(total_price),0) FROM credit_items WHERE transaction_id=?", (transaction_id,))
    total_credit = c.fetchone()[0] or 0.0
    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE transaction_id=?", (transaction_id,))
    total_paid = c.fetchone()[0] or 0.0
    balance = round(total_credit - total_paid, 2)
    if balance <= 0:
        c.execute("UPDATE credit_transactions SET status='Paid' WHERE id=?", (transaction_id,))
    elif 0 < total_paid < total_credit:
        c.execute("UPDATE credit_transactions SET status='Partially Paid' WHERE id=?", (transaction_id,))
    else:
        c.execute("UPDATE credit_transactions SET status='Unpaid' WHERE id=?", (transaction_id,))
    conn.commit()
    conn.close()
    return balance

# Insert a transaction and items (reuses open transaction)
def save_credit_items_for_customer(customer_id, lending_date, items):
    """items: list of dicts with keys product_id, qty, unit_price"""
    conn = create_connection()
    c = conn.cursor()
    # find open transaction for this customer (Unpaid or Partially Paid) - use latest
    c.execute("SELECT id FROM credit_transactions WHERE customer_id=? AND status!='Paid' ORDER BY date DESC LIMIT 1", (customer_id,))
    row = c.fetchone()
    if row:
        tx_id = row[0]
    else:
        c.execute("INSERT INTO credit_transactions (customer_id, date, status) VALUES (?, ?, 'Unpaid')", (customer_id, lending_date))
        tx_id = c.lastrowid

    for it in items:
        total_price = round(it['qty'] * it['unit_price'], 2)
        c.execute("""
            INSERT INTO credit_items (transaction_id, product_id, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?)
        """, (tx_id, it['product_id'], it['qty'], it['unit_price'], total_price))
    conn.commit()
    conn.close()
    recalc_balance(tx_id)
    return tx_id

# Insert payment and auto-recalc
def record_payment(transaction_id, amount, method, payment_date):
    conn = create_connection()
    c = conn.cursor()
    c.execute("INSERT INTO payments (transaction_id, amount, method, date) VALUES (?, ?, ?, ?)",
              (transaction_id, amount, method, payment_date))
    pid = c.lastrowid
    conn.commit()
    conn.close()
    recalc_balance(transaction_id)
    return pid

def delete_payment(payment_id):
    conn = create_connection()
    c = conn.cursor()
    c.execute("SELECT transaction_id FROM payments WHERE id=?", (payment_id,))
    row = c.fetchone()
    tid = row[0] if row else None
    c.execute("DELETE FROM payments WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()
    if tid:
        recalc_balance(tid)
    return tid

def update_credit_item(item_id, qty, unit_price):
    conn = create_connection()
    c = conn.cursor()
    total_price = round(qty * unit_price, 2)
    c.execute("SELECT transaction_id FROM credit_items WHERE id=?", (item_id,))
    row = c.fetchone()
    tid = row[0] if row else None
    c.execute("UPDATE credit_items SET quantity=?, unit_price=?, total_price=? WHERE id=?", (qty, unit_price, total_price, item_id))
    conn.commit()
    conn.close()
    if tid:
        recalc_balance(tid)
    return tid

def delete_transaction(transaction_id):
    conn = create_connection()
    c = conn.cursor()
    c.execute("DELETE FROM credit_items WHERE transaction_id=?", (transaction_id,))
    c.execute("DELETE FROM payments WHERE transaction_id=?", (transaction_id,))
    c.execute("DELETE FROM credit_transactions WHERE id=?", (transaction_id,))
    conn.commit()
    conn.close()

# Fetchers
def fetch_customers():
    conn = create_connection()
    df = pd.read_sql("SELECT id, name FROM customers ORDER BY name", conn)
    conn.close()
    return df

def fetch_products():
    conn = create_connection()
    df = pd.read_sql("SELECT id, name, price FROM products ORDER BY name", conn)
    conn.close()
    return df

def fetch_grouped_accounts(customer_filter=None, status_filter=None, start_date=None, end_date=None):
    conn = create_connection()
    query = """
    SELECT
      ct.id AS transaction_id,
      cu.id AS customer_id,
      cu.name AS customer_name,
      ct.date,
      ct.status,
      COALESCE((SELECT SUM(ci.total_price) FROM credit_items ci WHERE ci.transaction_id = ct.id),0) AS total_amount,
      COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.transaction_id = ct.id),0) AS total_paid,
      COALESCE((SELECT SUM(ci.total_price) FROM credit_items ci WHERE ci.transaction_id = ct.id),0) - COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.transaction_id = ct.id),0) AS balance
    FROM credit_transactions ct
    JOIN customers cu ON ct.customer_id = cu.id
    WHERE 1=1
    """
    params = []
    if customer_filter and customer_filter != "All":
        query += " AND cu.name = ?"
        params.append(customer_filter)
    if status_filter and status_filter != "All":
        query += " AND ct.status = ?"
        params.append(status_filter)
    if start_date:
        query += " AND ct.date >= ?"
        params.append(start_date.strftime("%Y-%m-%d"))
    if end_date:
        query += " AND ct.date <= ?"
        params.append(end_date.strftime("%Y-%m-%d"))
    query += " ORDER BY ct.date DESC"
    df = pd.read_sql(query, create_connection(), params=params)
    return df

def fetch_items(transaction_id):
    conn = create_connection()
    df = pd.read_sql("SELECT id, product_id, quantity, unit_price, total_price FROM credit_items WHERE transaction_id = ?", conn, params=(transaction_id,))
    conn.close()
    return df

def fetch_items_with_names(transaction_id):
    conn = create_connection()
    df = pd.read_sql("""
        SELECT ci.id, ci.product_id, p.name AS product, ci.quantity, ci.unit_price, ci.total_price
        FROM credit_items ci JOIN products p ON ci.product_id = p.id
        WHERE ci.transaction_id = ?
    """, conn, params=(transaction_id,))
    conn.close()
    return df

def fetch_payments(transaction_id):
    conn = create_connection()
    df = pd.read_sql("SELECT id, amount, method, date FROM payments WHERE transaction_id = ? ORDER BY date DESC", conn, params=(transaction_id,))
    conn.close()
    return df

# ----------------- NEW / UPDATED RECEIPT FUNCTIONS -----------------
def generate_payment_receipt_bytes(payment_id):
    """
    Generate a styled PDF receipt for a payment, including the list of products in that transaction.
    Returns bytes or None.
    """
    conn = create_connection()
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.amount, p.method, p.date, p.transaction_id, cu.name, ct.status
        FROM payments p
        JOIN credit_transactions ct ON p.transaction_id = ct.id
        JOIN customers cu ON ct.customer_id = cu.id
        WHERE p.id = ?
    """, (payment_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    pid, amount, method, pdate, txid, customer_name, tx_status = row

    # fetch items for this transaction (include transaction date for purchase date)
    conn2 = create_connection()
    c2 = conn2.cursor()
    c2.execute("""
        SELECT p.name, ci.quantity, ci.unit_price, ci.total_price, ct.date
        FROM credit_items ci
        JOIN products p ON ci.product_id = p.id
        JOIN credit_transactions ct ON ci.transaction_id = ct.id
        WHERE ci.transaction_id = ?
        ORDER BY ct.date ASC, p.name ASC
    """, (txid,))
    items = c2.fetchall()

    # totals for the whole transaction
    c2.execute("SELECT COALESCE(SUM(total_price),0) FROM credit_items WHERE transaction_id=?", (txid,))
    total_tx = c2.fetchone()[0] or 0.0
    c2.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE transaction_id=?", (txid,))
    total_paid = c2.fetchone()[0] or 0.0
    conn2.close()

    # Build PDF with ReportLab (preferred) or FPDF fallback
    if _pdf_backend == "reportlab":
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=12*mm, rightMargin=12*mm,
                                topMargin=12*mm, bottomMargin=12*mm)
        styles = getSampleStyleSheet()
        elements = []

        # Customer name at top (Title)
        elements.append(Paragraph(customer_name, styles['Title']))
        elements.append(Spacer(1, 6))

        # Payment & transaction details (small)
        small = styles['Normal']
        small.spaceAfter = 2
        elements.append(Paragraph(f"<b>Receipt ID:</b> {pid}", small))
        elements.append(Paragraph(f"<b>Transaction ID:</b> {txid}", small))
        elements.append(Paragraph(f"<b>Status:</b> {tx_status}", small))
        elements.append(Paragraph(f"<b>Payment Method:</b> {method}", small))
        elements.append(Paragraph(f"<b>Payment Date:</b> {pdate}", small))
        elements.append(Paragraph(f"<b>Amount Paid:</b> Kshs {amount:,.2f}", small))
        elements.append(Spacer(1, 8))

        # Products table header + rows
        data = [["Product", "Qty", "Unit Price", "Total", "Date Purchased"]]
        for it in items:
            pname, qty, up, totp, datep = it
            data.append([pname, str(qty), f"Kshs {up:,.2f}", f"Kshs {totp:,.2f}", str(datep)])

        # Totals rows
        data.append(["", "", "Total Transaction:", f"Kshs {total_tx:,.2f}", ""])
        data.append(["", "", "Total Paid (incl this):", f"Kshs {total_paid:,.2f}", ""])

        # wide column widths to create a modern wide invoice look
        col_widths = [80*mm, 20*mm, 30*mm, 30*mm, 30*mm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style = TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f2f2f2")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("ALIGN", (1,1), (-2,-1), "CENTER"),
            ("ALIGN", (-3,1), (-1,-1), "RIGHT"),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1, -1), 9),
            ("BOTTOMPADDING", (0,0), (-1,0), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0,1), (-1,-1), colors.white),
            ("ROWBACKGROUNDS", (1,1), (-1,-1), [colors.white, colors.HexColor("#fbfbfb")]),
            ("SPAN", (0, len(data)-2), (1, len(data)-2)),  # merge for total label (layout friendly)
            ("SPAN", (0, len(data)-1), (1, len(data)-1)),
            ("ALIGN", (2, len(data)-2), (3, len(data)-2), "RIGHT"),
            ("ALIGN", (2, len(data)-1), (3, len(data)-1), "RIGHT"),
            ("FONTNAME", (2, len(data)-2), (3, len(data)-1), "Helvetica-Bold")
        ])
        table.setStyle(style)
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    elif _pdf_backend == "fpdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        # Header - customer name
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, customer_name, ln=True)
        pdf.ln(2)

        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f"Receipt ID: {pid}    Transaction ID: {txid}", ln=True)
        pdf.cell(0, 6, f"Status: {tx_status}    Method: {method}    Payment Date: {pdate}", ln=True)
        pdf.cell(0, 6, f"Amount Paid: Kshs {amount:,.2f}", ln=True)
        pdf.ln(4)

        # Table header
        pdf.set_font("Arial", "B", 10)
        w_prod = 80
        w_qty = 18
        w_unit = 30
        w_total = 30
        w_date = 32
        pdf.cell(w_prod, 8, "Product", border=1)
        pdf.cell(w_qty, 8, "Qty", border=1, align="C")
        pdf.cell(w_unit, 8, "Unit Price", border=1, align="R")
        pdf.cell(w_total, 8, "Total", border=1, align="R")
        pdf.cell(w_date, 8, "Date", border=1, align="C")
        pdf.ln()

        pdf.set_font("Arial", size=9)
        for it in items:
            pname, qty, up, totp, datep = it
            pdf.cell(w_prod, 7, str(pname)[:40], border=1)  # truncated to fit
            pdf.cell(w_qty, 7, str(qty), border=1, align="C")
            pdf.cell(w_unit, 7, f"Kshs {up:,.2f}", border=1, align="R")
            pdf.cell(w_total, 7, f"Kshs {totp:,.2f}", border=1, align="R")
            pdf.cell(w_date, 7, str(datep), border=1, align="C")
            pdf.ln()

        # Totals
        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        # Position totals on the right
        pdf.set_x(w_prod + w_qty)
        pdf.cell(w_unit, 7, "Total Transaction:", border=0)
        pdf.cell(w_total, 7, f"Kshs {total_tx:,.2f}", border=1, align="R")
        pdf.ln()
        pdf.set_x(w_prod + w_qty)
        pdf.cell(w_unit, 7, "Total Paid (incl this):", border=0)
        pdf.cell(w_total, 7, f"Kshs {total_paid:,.2f}", border=1, align="R")

        pdf_bytes = pdf.output(dest='S').encode('latin1')
        return pdf_bytes

    else:
        return None


def generate_transaction_receipt_bytes(transaction_id):
    """
    Generate a transaction-level invoice/receipt (transaction may be unpaid).
    Includes product list and totals. Always returns raw PDF bytes.
    """
    conn = create_connection()
    c = conn.cursor()
    c.execute("""
        SELECT ct.id, cu.name, ct.date, ct.status
        FROM credit_transactions ct
        JOIN customers cu ON ct.customer_id = cu.id
        WHERE ct.id = ?
    """, (transaction_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return b""  # Always return bytes

    txid, customer_name, tx_date, tx_status = row

    # Fetch items
    conn2 = create_connection()
    c2 = conn2.cursor()
    c2.execute("""
        SELECT p.name, ci.quantity, ci.unit_price, ci.total_price, ct.date
        FROM credit_items ci
        JOIN products p ON ci.product_id = p.id
        JOIN credit_transactions ct ON ci.transaction_id = ct.id
        WHERE ci.transaction_id = ?
        ORDER BY ct.date ASC, p.name ASC
    """, (txid,))
    items = c2.fetchall()
    c2.execute("SELECT COALESCE(SUM(total_price),0) FROM credit_items WHERE transaction_id=?", (txid,))
    total_tx = c2.fetchone()[0] or 0.0
    c2.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE transaction_id=?", (txid,))
    total_paid = c2.fetchone()[0] or 0.0
    conn2.close()

    # PDF generation
    if _pdf_backend == "reportlab":
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=12*mm, rightMargin=12*mm,
                                topMargin=12*mm, bottomMargin=12*mm)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(customer_name, styles['Title']))
        elements.append(Spacer(1, 6))
        small = styles['Normal']
        elements.append(Paragraph(f"<b>Transaction ID:</b> {txid}", small))
        elements.append(Paragraph(f"<b>Transaction Date:</b> {tx_date}", small))
        elements.append(Paragraph(f"<b>Status:</b> {tx_status}", small))
        elements.append(Spacer(1, 8))

        data = [["Product", "Qty", "Unit Price", "Total", "Date Purchased"]]
        for pname, qty, up, totp, datep in items:
            data.append([pname, str(qty), f"Kshs {up:,.2f}", f"Kshs {totp:,.2f}", str(datep)])
        data.append(["", "", "Total Transaction:", f"Kshs {total_tx:,.2f}", ""])
        data.append(["", "", "Total Paid:", f"Kshs {total_paid:,.2f}", ""])

        col_widths = [80*mm, 20*mm, 30*mm, 30*mm, 30*mm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style = TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f2f2f2")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("ALIGN", (1,1), (-2,-1), "CENTER"),
            ("ALIGN", (-3,1), (-1,-1), "RIGHT"),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("BOTTOMPADDING", (0,0), (-1,0), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("BACKGROUND", (0,1), (-1,-1), colors.white),
            ("ROWBACKGROUNDS", (1,1), (-1,-1), [colors.white, colors.HexColor("#fbfbfb")]),
            ("SPAN", (0, len(data)-2), (1, len(data)-2)),
            ("SPAN", (0, len(data)-1), (1, len(data)-1)),
            ("ALIGN", (2, len(data)-2), (3, len(data)-1), "RIGHT"),
            ("FONTNAME", (2, len(data)-2), (3, len(data)-1), "Helvetica-Bold")
        ])
        table.setStyle(style)
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()  # Always bytes

    elif _pdf_backend == "fpdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, customer_name, ln=True)
        pdf.ln(2)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f"Transaction ID: {txid}    Date: {tx_date}    Status: {tx_status}", ln=True)
        pdf.ln(4)

        pdf.set_font("Arial", "B", 10)
        w_prod, w_qty, w_unit, w_total, w_date = 80, 18, 30, 30, 32
        pdf.cell(w_prod, 8, "Product", border=1)
        pdf.cell(w_qty, 8, "Qty", border=1, align="C")
        pdf.cell(w_unit, 8, "Unit Price", border=1, align="R")
        pdf.cell(w_total, 8, "Total", border=1, align="R")
        pdf.cell(w_date, 8, "Date", border=1, align="C")
        pdf.ln()

        pdf.set_font("Arial", size=9)
        for pname, qty, up, totp, datep in items:
            pdf.cell(w_prod, 7, str(pname)[:40], border=1)
            pdf.cell(w_qty, 7, str(qty), border=1, align="C")
            pdf.cell(w_unit, 7, f"Kshs {up:,.2f}", border=1, align="R")
            pdf.cell(w_total, 7, f"Kshs {totp:,.2f}", border=1, align="R")
            pdf.cell(w_date, 7, str(datep), border=1, align="C")
            pdf.ln()

        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        pdf.set_x(w_prod + w_qty)
        pdf.cell(w_unit, 7, "Total:", border=0)
        pdf.cell(w_total, 7, f"Kshs {total_tx:,.2f}", border=1, align="R")
        pdf.ln()
        pdf.set_x(w_prod + w_qty)
        pdf.cell(w_unit, 7, "Total Paid:", border=0)
        pdf.cell(w_total, 7, f"Kshs {total_paid:,.2f}", border=1, align="R")

        return pdf.output(dest='S').encode('latin1')  # Always bytes

    return b""  # Fallback to bytes

# ---------- UI Implementation ----------
migrate_schema()

# load datasets
customers_df = fetch_customers()
products_df = fetch_products()

# session state for cart
if "cart" not in st.session_state:
    st.session_state.cart = []

# Tabs
tab_new, tab_manage = st.tabs(["➕ Add Credit", "📊 Dashboard & Manage"])

# ---------------- Tab: Add Credit ----------------
with tab_new:
    st.header("Record New Credit Transaction")
    if customers_df.empty:
        st.warning("No customers found. Add customers first.")
    elif products_df.empty:
        st.warning("No products found. Add products first.")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_customer = st.selectbox("Select Customer", options=customers_df.to_dict("records"), format_func=lambda x: x['name'])
            cust_id = selected_customer['id']
            # live balance for customer
            cust_balance_df = pd.read_sql("""
                SELECT COALESCE(SUM(ci.total_price),0) - COALESCE((SELECT SUM(amount) FROM payments p WHERE p.transaction_id = ct.id),0) AS balance
                FROM credit_transactions ct
                LEFT JOIN credit_items ci ON ci.transaction_id = ct.id
                WHERE ct.customer_id = ?
            """, create_connection(), params=(cust_id,))
            bal_val = cust_balance_df.iloc[0,0] or 0.0
            if bal_val > 0:
                st.info(f"💰 Current Outstanding Balance: Kshs {bal_val:,.2f}")
            else:
                st.success("✅ No outstanding balance")

            lending_date = st.date_input("Date of Lending", value=date.today())

        with col2:
            st.markdown("**Add product to cart**")
            prod_choice = st.selectbox("Product", options=products_df.to_dict("records"), format_func=lambda x: f"{x['name']} - Kshs {x['price']:.2f}")
            qty = st.number_input("Quantity", min_value=1, value=1)
            unit_price = st.number_input("Unit Price", min_value=0.00, value=float(prod_choice['price']), format="%.2f")
            if st.button("➕ Add Product"):
                # append to cart
                st.session_state.cart.append({
                    "product_id": prod_choice['id'],
                    "product_name": prod_choice['name'],
                    "qty": int(qty),
                    "unit_price": float(unit_price),
                    "total_price": round(int(qty) * float(unit_price), 2)
                })
                st.rerun()

        # show cart
        st.markdown("### Cart")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            cart_df_display = cart_df.copy()
            cart_df_display['unit_price'] = cart_df_display['unit_price'].map(lambda x: f"Kshs {x:,.2f}")
            cart_df_display['total_price'] = cart_df_display['total_price'].map(lambda x: f"Kshs {x:,.2f}")
            st.table(cart_df_display[['product_name','qty','unit_price','total_price']])
            grand_total = sum([x['total_price'] for x in st.session_state.cart])
            st.markdown(f"**Grand Total:** Kshs {grand_total:,.2f}")

            col_save, col_clear = st.columns([1,1])
            with col_save:
                if st.button("💾 Save Transaction"):
                    # build items
                    items = [{"product_id": x['product_id'], "qty": x['qty'], "unit_price": x['unit_price']} for x in st.session_state.cart]
                    tx_id = save_credit_items_for_customer(cust_id, lending_date.strftime("%Y-%m-%d"), items)
                    st.success(f"Saved to transaction ID {tx_id}.")
                    st.session_state.cart = []
                    st.rerun()
            with col_clear:
                if st.button("🗑️ Clear Cart"):
                    st.session_state.cart = []
                    st.rerun()

        else:
            st.info("Cart is empty.")

# ---------------- Tab: Dashboard & Manage ----------------
with tab_manage:
    st.header("Dashboard — Top Owed Customers")
    # top owed customers
    conn = create_connection()
    owed_df = pd.read_sql("""
        SELECT cu.id, cu.name, COALESCE(SUM(ci.total_price),0) - COALESCE(SUM(p.amount),0) AS balance
        FROM customers cu
        LEFT JOIN credit_transactions ct ON ct.customer_id = cu.id
        LEFT JOIN credit_items ci ON ci.transaction_id = ct.id
        LEFT JOIN payments p ON p.transaction_id = ct.id
        GROUP BY cu.id
        HAVING balance > 0
        ORDER BY balance DESC
        LIMIT 10
    """, conn)
    conn.close()

    if not owed_df.empty:
        owed_df_display = owed_df.copy()
        owed_df_display['balance'] = owed_df_display['balance'].map(lambda x: f"Kshs {x:,.2f}")
        st.table(owed_df_display.rename(columns={'name':'Customer'}))
    else:
        st.info("No outstanding balances to show.")

    st.markdown("---")
    st.subheader("Manage Customer Accounts (expand one to view details)")

    # filters
    cust_list = ["All"] + customers_df['name'].tolist() if not customers_df.empty else ["All"]
    colf1, colf2, colf3 = st.columns([2,1,1])
    with colf1:
        filter_customer = st.selectbox("Filter by Customer", cust_list, index=0)
    with colf2:
        filter_status = st.selectbox("Filter by Status", ["All","Unpaid","Partially Paid","Paid"], index=0)
    with colf3:
        show_only_with_balance = st.checkbox("Only show accounts with balance", value=False)

    # fetch grouped accounts (transactions)
    grouped = fetch_grouped_accounts(customer_filter=filter_customer, status_filter=filter_status)

    # optionally filter out zero balances
    if show_only_with_balance:
        grouped = grouped[grouped['balance'] > 0]

    if grouped.empty:
        st.info("No accounts match the selected filters.")
    else:
        # Display grouped rows (one row per transaction)
        for _, row in grouped.iterrows():
            tid = int(row['transaction_id'])
            cust_name = row['customer_name']
            tdate = row['date']
            status = row['status']
            total_amt = float(row['total_amount'])
            total_paid = float(row['total_paid'])
            balance = float(row['balance'])

            cols = st.columns([3,1,1,1,1,2])
            with cols[0]:
                st.markdown(f"**{cust_name}**")
                st.write(f"Transaction: {tid} — Date: {tdate}")
            with cols[1]:
                st.write(f"**Total:** Kshs {total_amt:,.2f}")
            with cols[2]:
                st.write(f"**Paid:** Kshs {total_paid:,.2f}")
            with cols[3]:
                st.write(f"**Balance:** Kshs {balance:,.2f}")
            with cols[4]:
                st.write(f"**Status:** {status}")
            with cols[5]:
                # Transaction-level Download button (visible in table row)
                tx_pdf = generate_transaction_receipt_bytes(tid)

                if tx_pdf:
                    # Store raw bytes in session state to avoid .bin reference issues
                    st.session_state[f"tx_receipt_{tid}"] = tx_pdf

                # Always read from session_state to keep consistent behavior
                if st.session_state.get(f"tx_receipt_{tid}"):
                    st.download_button(
                        label="📥 Download Receipt",
                        data=st.session_state[f"tx_receipt_{tid}"],
                        file_name=f"receipt_tx{tid}.pdf",
                        mime="application/pdf",
                        key=f"dl_tx_{tid}"
                    )




                if st.button("✅ Mark as Paid", key=f"markpaid_{tid}"):
                    # create balancing payment if needed
                    if balance > 0:
                        pid = record_payment(tid, balance, "Manual", date.today().strftime("%Y-%m-%d"))
                    else:
                        pid = None
                    recalc_balance(tid)
                    st.success("Marked as Paid.")
                    st.rerun()

                if st.button("🗑️ Delete", key=f"del_{tid}"):
                    delete_transaction(tid)
                    st.warning("Transaction deleted.")
                    st.rerun()


            # details expander
            with st.expander("View items & payments", expanded=False):
                items_df = fetch_items_with_names(tid)
                if not items_df.empty:
                    display_items = items_df.copy()
                    display_items['unit_price'] = display_items['unit_price'].map(lambda x: f"Kshs {x:,.2f}")
                    display_items['total_price'] = display_items['total_price'].map(lambda x: f"Kshs {x:,.2f}")
                    st.write("**Items**")
                    st.dataframe(display_items.rename(columns={'id':'item_id'}), use_container_width=True)

                    # Edit inline
                    st.markdown("**Edit Items**")
                    for idx, it in items_df.iterrows():
                        item_id = int(it['id'])
                        prod_id = int(it['product_id'])
                        prod_name = it['product']
                        col_a, col_b, col_c, col_d = st.columns([3,1,1,1])
                        with col_a:
                            st.write(prod_name)
                        with col_b:
                            new_qty = st.number_input(f"Qty item {item_id}", min_value=1, value=int(it['quantity']), key=f"iq_{item_id}")
                        with col_c:
                            new_up = st.number_input(f"Unit item {item_id}", min_value=0.00, value=float(it['unit_price']), format="%.2f", key=f"ip_{item_id}")
                        with col_d:
                            if st.button("Save", key=f"save_item_{item_id}"):
                                         update_credit_item(item_id, int(new_qty), float(new_up))
                                         st.success("Item updated.")
                                         st.rerun()
                payments_df = fetch_payments(tid)
                if not payments_df.empty:
                    display_payments = payments_df.copy()
                    display_payments['amount'] = display_payments['amount'].map(lambda x: f"Kshs {x:,.2f}")
                    st.write("**Payments**")
                    st.dataframe(display_payments, use_container_width=True)
                    st.markdown("**Undo Payments**")
                    for idx, p in payments_df.iterrows():
                        pay_id = int(p['id'])
                        colx, coly = st.columns([3,1])
                        with coly:
                            if st.button("Undo", key=f"undo_{pay_id}"):
                                delete_payment(pay_id)
                                st.warning(f"Payment {pay_id} deleted.")
                                st.rerun()
                        pdf_bytes = generate_payment_receipt_bytes(pay_id)
                        if pdf_bytes:
                            st.download_button(
                                label="📥 Download Receipt (PDF)",
                                data=pdf_bytes,
                                file_name=f"receipt_{pay_id}.pdf",
                                mime="application/pdf",
                                key=f"dl_receipt_{tid}_{idx}"    
                            )
                # ----------------- HERE IS THE UPDATED PAYMENT FORM AND DOWNLOAD BUTTON -----------------
                with st.form(f"payment_form_{tid}", clear_on_submit=True):
                    st.markdown("**Record Payment**")
                    pcol1, pcol2, pcol3 = st.columns([2,1,1])
                    with pcol1:
                        pay_amount = st.number_input("Amount (Kshs)", min_value=0.00, value=0.0, format="%.2f", key=f"payamt_{tid}")
                    with pcol2:
                        pay_method = st.selectbox("Method", ["Cash","Mpesa","Card","Bank"], key=f"paymeth_{tid}")
                    with pcol3:
                        pay_date = st.date_input("Payment Date", value=date.today(), key=f"paydate_{tid}")
                    pay_submit = st.form_submit_button("Save Payment")
                    if pay_submit:
                        if pay_amount > 0:
                            pid = record_payment(tid, float(pay_amount), pay_method, pay_date.strftime("%Y-%m-%d"))
                            st.success("Payment recorded.")
                            pdf_bytes = generate_payment_receipt_bytes(pid)
                            if pdf_bytes:
                                st.download_button(
                                    label="📥 Download Receipt (PDF)",
                                    data=pdf_bytes,
                                    file_name=f"receipt_{pid}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_receipt_{pid}"
                                )
                                
                            else:
                                st.info("PDF receipt not available — install reportlab or fpdf.")
                          

                        else:
                            st.warning("Enter amount > 0")

                # Outside the form: show download button if receipt available in session state
                # for key in list(st.session_state.keys()):
                #     if key.startswith("receipt_") and st.session_state[key] is not None:
                #         st.download_button(
                #             label="📥 Download Receipt (PDF)",
                #             data=st.session_state[key],
                #             file_name=f"{key}.pdf",
                #             mime="application/pdf",
                #             key=f"dl_{key}"
                #         )
                #         # Uncomment below if you want to clear the receipt after download to clean up UI
                #         # del st.session_state[key]
            
    # Export grouped view to excel
    st.markdown("---")
    export_df = []
    for _, r in grouped.iterrows():
        export_df.append({
            "Transaction ID": int(r['transaction_id']),
            "Customer": r['customer_name'],
            "Date": r['date'],
            "Status": r['status'],
            "Total": float(r['total_amount']),
            "Paid": float(r['total_paid']),
            "Balance": float(r['balance'])
        })
    if export_df:
        export_df = pd.DataFrame(export_df)
        excel_buf = BytesIO()
        with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name="Accounts")
        excel_bytes = excel_buf.getvalue()
        st.download_button("📥 Export Accounts (Excel)", data=excel_bytes, file_name="credit_accounts.xlsx")

# End of script
          