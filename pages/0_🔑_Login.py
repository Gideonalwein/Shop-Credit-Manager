import streamlit as st

# Page config
st.set_page_config(page_title="Login", page_icon="🔑", layout="centered")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

USERNAME = "Admin"
PASSWORD = "!23qweASD"

# If already logged in → show logout button
if st.session_state.logged_in:
    st.success("✅ You are already logged in!")

    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.switch_page("pages/0_🔑_Login.py")
    else:
        st.switch_page("Home.py")

# If not logged in → show login form
else:
    st.markdown("## 🔑 Please Login to Continue")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == USERNAME and password == PASSWORD:
            st.session_state.logged_in = True
            st.success("✅ Login successful! Redirecting...")
            st.switch_page("Home.py")
        else:
            st.error("❌ Invalid username or password")
