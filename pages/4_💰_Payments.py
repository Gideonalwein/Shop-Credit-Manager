import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ====================
# DB CONNECTION
# ====================
def create_connection():
    return sqlite3.connect("data/shop.db", check_same_thread=False)

# ====================
# HELPER FUNCTIONS
# ====================
def get_customers():
    conn = create_connection()
    df = pd.read_sql("SELECT id, name FROM customers ORDER BY name", conn)
    conn.close()
    return df

def get_customer_balance(customer_id):
    conn = create_connection()
    query = """
        SELECT 
            ct.id AS transaction_id,
            ct.date,
            SUM(ci.total_price) AS total_credit,
            IFNULL(SUM(p.amount), 0) AS total_paid,
            (SUM(ci.total_price) - IFNULL(SUM(p.amount), 0)) AS balance
        FROM credit_transactions ct
        JOIN credit_items ci ON ci.transaction_id = ct.id
        LEFT JOIN payments p ON p.transaction_id = ct.id
        WHERE ct.customer_id = ?
        GROUP BY ct.id
        HAVING balance > 0
        ORDER BY ct.date
    """
    df = pd.read_sql(query, conn, params=(customer_id,))
    conn.close()
    return df

def insert_payment(transaction_id, amount, method, date):
    conn = create_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO payments (transaction_id, amount, method, date)
        VALUES (?, ?, ?, ?)
    """, (transaction_id, amount, method, date))
    conn.commit()
    conn.close()

def get_payment_history(customer_id):
    conn = create_connection()
    query = """
        SELECT p.id, p.transaction_id, p.amount, p.method, p.date
        FROM payments p
        JOIN credit_transactions ct ON p.transaction_id = ct.id
        WHERE ct.customer_id = ?
        ORDER BY p.date DESC
    """
    df = pd.read_sql(query, conn, params=(customer_id,))
    conn.close()
    return df

def delete_payment(payment_id):
    conn = create_connection()
    c = conn.cursor()
    c.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()

# ====================
# PAGE UI
# ====================
st.set_page_config(page_title="Payments", page_icon="💰", layout="wide")
st.title("💰 Payments Management")

# 1. Select Customer
customers_df = get_customers()
if customers_df.empty:
    st.warning("No customers found in the system.")
    st.stop()

customer_name_map = dict(zip(customers_df["name"], customers_df["id"]))
selected_customer = st.selectbox("Select Customer", customers_df["name"])

if selected_customer:
    customer_id = customer_name_map[selected_customer]

    # 2. Show Outstanding Credits
    st.subheader(f"Outstanding Credits for {selected_customer}")
    credits_df = get_customer_balance(customer_id)

    if credits_df.empty:
        st.info("No outstanding credits for this customer.")
    else:
        st.dataframe(credits_df[["transaction_id", "date", "total_credit", "total_paid", "balance"]])

        # Total Balance
        total_balance = credits_df["balance"].sum()
        st.metric("Total Outstanding Balance", f"Kshs {total_balance:,.2f}")

        # 3. Record Payment
        st.subheader("Record Payment")
        transaction_options = {f"Transaction {row.transaction_id} (Bal: {row.balance:,.2f})": row.transaction_id
                               for row in credits_df.itertuples()}
        selected_transaction_label = st.selectbox("Select Credit Transaction", list(transaction_options.keys()))
        selected_transaction_id = transaction_options[selected_transaction_label]

        pay_amount = st.number_input("Amount (Kshs)", min_value=0.01, value=0.01, step=0.01, format="%.2f")
        pay_method = st.selectbox("Payment Method", ["Cash", "Mpesa", "Bank", "Other"])
        pay_date = st.date_input("Payment Date", value=datetime.today())

        if st.button("💾 Save Payment"):
            if pay_amount > 0:
                insert_payment(selected_transaction_id, pay_amount, pay_method, pay_date.strftime("%Y-%m-%d"))
                st.success("Payment recorded successfully!")
                st.rerun()

            else:
                st.error("Amount must be greater than 0.")

    # 4. Payment History
    st.subheader("Payment History")
    history_df = get_payment_history(customer_id)
    if history_df.empty:
        st.info("No payments found for this customer.")
    else:
        for row in history_df.itertuples():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            col1.write(f"Txn ID: {row.transaction_id}")
            col2.write(f"Kshs {row.amount:,.2f}")
            col3.write(row.method)
            col4.write(row.date)
            if col5.button("❌", key=f"del_{row.id}"):
                delete_payment(row.id)
                st.warning("Payment deleted!")
                st.rerun()

