import streamlit as st
from database import init_db

st.set_page_config(page_title="Shop Credit Manager", layout="wide")
init_db()

# ---------- Hide sidebar ----------
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        display: none !important;
    }
    [data-testid="stAppViewContainer"] {
        margin-left: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- Background ----------
st.markdown(
    """
    <style>
    html, body, .stApp, .main, .block-container {
        background: transparent !important;
    }
    #bg {
        position: fixed;
        inset: 0;
        z-index: -999999;
        pointer-events: none;
        background: linear-gradient(135deg, #57B4BA 0%, #d9e4ec 100%);
    }
    #bg::after {
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at 10% 10%, rgba(255,255,255,0.05), transparent 10%),
                    radial-gradient(circle at 90% 90%, rgba(0,0,0,0.03), transparent 10%);
        mix-blend-mode: overlay;
    }

    /* ==== Card Styles ==== */
    .stButton > button {
        width: 100%;
        height: 180px;
        border-radius: 20px;
        color: white;
        font-weight: 700;
        font-size: 18px;
        border: none;
        cursor: pointer;
        padding: 16px;
        display: flex !important;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        line-height: 1.3;
        transition: transform 0.25s ease, box-shadow 0.25s ease, filter 0.25s ease;
    }
    .stButton > button:hover {
        transform: translateY(-6px);
        filter: brightness(1.15);
    }

    /* Icon Styling */
    .card-icon {
        font-size: 48px;
        margin-bottom: 10px;
        display: block;
        transition: color 0.3s ease;
    }

    /* Icon hover colors + glow matching gradient */
    div.stButton > button[key='Customers']:hover {
        box-shadow: 0 0 20px rgba(0,242,254,0.6);
    }
    div.stButton > button[key='Customers']:hover .card-icon {
        color: #00f2fe;
    }

    div.stButton > button[key='Products']:hover {
        box-shadow: 0 0 20px rgba(56,249,215,0.6);
    }
    div.stButton > button[key='Products']:hover .card-icon {
        color: #38f9d7;
    }

    div.stButton > button[key='Transactions']:hover {
        box-shadow: 0 0 20px rgba(240,147,251,0.6);
    }
    div.stButton > button[key='Transactions']:hover .card-icon {
        color: #f093fb;
    }

    div.stButton > button[key='Payments']:hover {
        box-shadow: 0 0 20px rgba(255,154,158,0.6);
    }
    div.stButton > button[key='Payments']:hover .card-icon {
        color: #ff9a9e;
    }
    </style>
    <div id="bg"></div>
    """,
    unsafe_allow_html=True
)

# ---------- Page content ----------
st.title("🛍️ Shop Credit Manager")
st.markdown("### Welcome to your credit management dashboard")
st.markdown("Click a card below to navigate:")

# ==== CARD DATA ====
cards = [
    {"icon": "👥", "label": "Customers",    "file": "1_📇_Customers.py",           "bg": "linear-gradient(135deg,#4facfe,#00f2fe)"},
    {"icon": "📦", "label": "Products",     "file": "2_📦_Products.py",            "bg": "linear-gradient(135deg,#43e97b,#38f9d7)"},
    {"icon": "💳", "label": "Transactions", "file": "3_💳_Credit_Transactions.py", "bg": "linear-gradient(135deg,#f093fb,#f5576c)"},
    {"icon": "💰", "label": "Payments",     "file": "4_💰_Payments.py",            "bg": "linear-gradient(135deg,#fad0c4,#ff9a9e)"},
]

cols = st.columns(2, gap="large")

# ==== Render Cards ====
for i, card in enumerate(cards):
    with cols[i % 2]:
        if st.button(f"{card['icon']}\n{card['label']}", key=card['label'], help=f"Go to {card['label']} page"):
                     st.switch_page(f"pages/{card['file']}")
                     
            
        st.markdown(
            f"<style>div.stButton > button[key='{card['label']}'] {{ background: {card['bg']}; }}</style>",
            unsafe_allow_html=True
        )
