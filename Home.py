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

# ---------- Full-page gradient background ----------
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
        background: linear-gradient(135deg, #4facfe 0%, #FFECDB 40%, #9be7ff 100%); /* cool blue -> aqua */
    }
    #bg::after {
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at 10% 10%, rgba(255,255,255,0.03), transparent 10%),
                    radial-gradient(circle at 90% 90%, rgba(0,0,0,0.02), transparent 10%);
        mix-blend-mode: overlay;
        pointer-events: none;
    }

    /* ==== Card Styles ==== */
    .stButton > button {
        width: 100%;
        height: 170px; /* fixed height for equal size */
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
        white-space: normal; /* allow wrapping */
        line-height: 1.3;
        transition: transform 0.22s ease, box-shadow 0.22s ease;
    }
    .stButton > button:hover {
        transform: translateY(-6px);
        box-shadow: 0 12px 30px rgba(8, 30, 60, 0.18);
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
    {"icon": "👥", "label": "1_📇_Customers",           "bg": "linear-gradient(135deg,#4facfe,#00f2fe)"},
    {"icon": "📦", "label": "2_📦_Products",            "bg": "linear-gradient(135deg,#43e97b,#38f9d7)"},
    {"icon": "💳", "label": "3_💳_Credit_Transactions", "bg": "linear-gradient(135deg,#f093fb,#f5576c)"},
    {"icon": "💰", "label": "4_💰_Payments",            "bg": "linear-gradient(135deg,#fad0c4,#ff9a9e)"},
]

cols = st.columns(2, gap="large")

for i, card in enumerate(cards):
    with cols[i % 2]:
        if st.button(f"{card['icon']}\n{card['label']}", key=card['label'], help=f"Go to {card['label']}"):
            st.switch_page(f"pages/{card['label']}.py")
        st.markdown(
            f"<style>div.stButton > button[key='{card['label']}'] {{ background: {card['bg']}; }}</style>",
            unsafe_allow_html=True
        )
