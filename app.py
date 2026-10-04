import streamlit as st


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Sales Performance Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# PAGE DEFINITIONS
# =========================================================

overview = st.Page(
    "pages/overview.py",
    title="Overview",
    icon="🏠",
)

healthy_go = st.Page(
    "pages/healthy_go.py",
    title="Healthy Go",
    icon="🏥",
)

bekelin = st.Page(
    "pages/bekelin.py",
    title="Bekelin",
    icon="🛍️",
)


# =========================================================
# NAVIGATION
# =========================================================

pg = st.navigation(
    {
        "SALES PERFORMANCE": [
            overview,
            healthy_go,
            bekelin,
        ]
    }
)


# =========================================================
# RUN
# =========================================================

pg.run()
