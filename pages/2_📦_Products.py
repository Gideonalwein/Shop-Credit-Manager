import streamlit as st
import pandas as pd
from database import create_connection

# Connect to the database
conn = create_connection()

# --- Database Functions ---
def add_product(name, price):
    conn.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
    conn.commit()

def get_products():
    return pd.read_sql_query("SELECT * FROM products ORDER BY created_at DESC", conn)

def delete_product(product_id):
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()

# --- Streamlit UI ---
st.title("📦 Product Management")

# Form to add a new product
with st.form("add_product_form"):
    st.subheader("➕ Add New Product")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.text_input("Product Name")
    with col2:
        price = st.number_input("Price (Kshs.)", min_value=0.00, format="%.2f", step=0.50)
    
    submitted = st.form_submit_button("Add Product")

    if submitted:
        if name.strip() == "" or price <= 0:
            st.warning("Both Product Name and Price are required.")
        else:
            add_product(name.strip(), price)
            st.success(f"Product '{name}' added successfully at Kshs. {price:.2f}.")

st.markdown("---")

# Display product list
st.subheader("📋 List of Products")
products = get_products()

if not products.empty:
    # Format price with Kshs. and 2 decimals
    products["price"] = products["price"].apply(lambda x: f"Kshs. {x:,.2f}")
    st.dataframe(products, use_container_width=True)

    with st.expander("🗑️ Delete Product"):
        product_names = products["name"] + " (ID: " + products["id"].astype(str) + ")"
        selected = st.selectbox("Select Product", product_names)
        if st.button("Delete Selected Product"):
            selected_id = int(selected.split("ID: ")[1].replace(")", ""))
            delete_product(selected_id)
            st.success("Product deleted. Refresh the page to update the list.")
else:
    st.info("No products found.")

