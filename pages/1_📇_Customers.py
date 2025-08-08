import streamlit as st
import pandas as pd
from database import create_connection

# Connect to the database
conn = create_connection()

# --- Database Functions ---
def add_customer(name, phone):
    conn.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", (name, phone))
    conn.commit()

def get_customers():
    return pd.read_sql_query("SELECT * FROM customers ORDER BY created_at DESC", conn)

def delete_customer(customer_id):
    conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()

# --- Streamlit UI ---
st.title("📇 Customer Management")

# Form to add a new customer
with st.form("add_customer_form"):
    st.subheader("➕ Add New Customer")
    name = st.text_input("Customer Name")
    phone = st.text_input("Phone Number")
    submitted = st.form_submit_button("Add Customer")

    if submitted:
        if name.strip() == "" or phone.strip() == "":
            st.warning("Both Customer Name and Phone Number are required.")
        else:
            add_customer(name.strip(), phone.strip())
            st.success(f"Customer '{name}' added successfully.")

st.markdown("---")

# Display customer list
st.subheader("📋 List of Customers")
customers = get_customers()

if not customers.empty:
    st.dataframe(customers, use_container_width=True)

    with st.expander("🗑️ Delete Customer"):
        customer_names = customers["name"] + " (ID: " + customers["id"].astype(str) + ")"
        selected = st.selectbox("Select Customer", customer_names)
        if st.button("Delete Selected Customer"):
            selected_id = int(selected.split("ID: ")[1].replace(")", ""))
            delete_customer(selected_id)
            st.success("Customer deleted. Refresh the page to update the list.")
else:
    st.info("No customers found.")
