import streamlit as st

st.set_page_config(
    page_title="Sales Performance Hub",
    page_icon="📊",
    layout="wide",
)

overview_page = st.Page(
    "pages/overview.py",
    title="Overview",
    icon="🏠",
)

hg_page = st.Page(
    "pages/healthy_go.py",
    title="Healthy Go",
    icon="🏥",
)

bk_page = st.Page(
    "pages/bekelin.py",
    title="Bekelin",
    icon="🛍️",
)

pg = st.navigation(
    {
        "Sales Performance": [
            overview_page,
            hg_page,
            bk_page,
        ]
    }
)

pg.run()
