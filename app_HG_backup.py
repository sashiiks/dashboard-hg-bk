import streamlit as st
import pandas as pd


from google_sheet import connect_google_sheet, get_sales_hg
from transaction_HG import build_transaction_HG
from target_agent_HG import build_target_actual_HG
from kpi_HG import (
    build_kpi_HG,
    build_daily_performance_HG,
    build_agent_performance_HG
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Healthy Go — Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# CUSTOM STYLE
# =========================================================

st.markdown(
    """
    <style>

    /* Main background */
    .stApp {
        background-color: #F8F9FC;
    }

    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Title */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #25283D;
        margin-bottom: 0.2rem;
    }

    .main-subtitle {
        font-size: 1rem;
        color: #7A7F95;
        margin-bottom: 1.5rem;
    }

    /* Section title */
    .section-title {
        font-size: 1.25rem;
        font-weight: 650;
        color: #25283D;
        margin-top: 0.4rem;
        margin-bottom: 0.8rem;
    }

    /* KPI Card */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E8EAF0;
        border-radius: 14px;
        padding: 1.15rem 1.25rem;
        min-height: 125px;
        box-shadow: 0 2px 8px rgba(37, 40, 61, 0.04);
    }

    .kpi-label {
        font-size: 0.85rem;
        color: #7A7F95;
        margin-bottom: 0.45rem;
    }

    .kpi-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: #25283D;
        line-height: 1.2;
    }

    .kpi-caption {
        font-size: 0.78rem;
        color: #9A9EAE;
        margin-top: 0.4rem;
    }

    /* Info cards */
    .info-card {
        background: #FFFFFF;
        border: 1px solid #E8EAF0;
        border-radius: 14px;
        padding: 1rem 1.15rem;
        box-shadow: 0 2px 8px rgba(37, 40, 61, 0.03);
    }

    /* Tables */
    .dataframe {
        border-radius: 10px;
    }

    /* Divider */
    hr {
        margin-top: 1.8rem;
        margin-bottom: 1.8rem;
        border: none;
        border-top: 1px solid #E8EAF0;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #9A9EAE;
        font-size: 0.78rem;
        padding-top: 2rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_rupiah(value):
    """Format angka menjadi Rupiah yang readable."""
    value = float(value)

    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        formatted = f"Rp {value / 1_000_000_000:.2f} M"
    elif abs_value >= 1_000_000:
        formatted = f"Rp {value / 1_000_000:.2f} Jt"
    elif abs_value >= 1_000:
        formatted = f"Rp {value / 1_000:.1f} Rb"
    else:
        formatted = f"Rp {value:,.0f}"

    return formatted


def format_rupiah_full(value):
    """Format Rupiah lengkap untuk tabel."""
    return f"Rp {float(value):,.0f}"


def format_percent(value):
    """Format percentage."""
    if pd.isna(value):
        return "-"
    return f"{float(value):.2f}%"


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">Healthy Go — Sales Performance Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="main-subtitle">September 2026 · Sales Performance Overview</div>',
    unsafe_allow_html=True
)


# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data(ttl=300)
def load_dashboard_data():

    spreadsheet = connect_google_sheet()

    # -----------------------------------------------------
    # TARGET AGENT
    # -----------------------------------------------------

    target_df = pd.DataFrame(
        spreadsheet
        .worksheet("TARGET AGENT")
        .get_all_records()
    )

    # -----------------------------------------------------
    # SALES HG
    # -----------------------------------------------------

    sales_df = pd.DataFrame(
        get_sales_hg()
    )

    # -----------------------------------------------------
    # TRANSACTION LAYER
    # -----------------------------------------------------

    transaction_df = build_transaction_HG(
        sales_df
    )

    # -----------------------------------------------------
    # TARGET VS ACTUAL
    # -----------------------------------------------------

    target_actual_df = build_target_actual_HG(
        target_df,
        transaction_df
    )

    # -----------------------------------------------------
    # KPI
    # -----------------------------------------------------

    result = build_kpi_HG(
        target_actual_df
    )

    # -----------------------------------------------------
    # AGENT PERFORMANCE
    # -----------------------------------------------------

    agent_performance = build_agent_performance_HG(
        target_actual_df
    )

    result["agent_performance"] = agent_performance

    result["top_agents"] = (
        agent_performance
        .sort_values(
            "achievement",
            ascending=False
        )
        .head(10)
    )

    result["bottom_agents"] = (
        agent_performance
        .sort_values(
            "achievement",
            ascending=True
        )
        .head(10)
    )

    # -----------------------------------------------------
    # DAILY PERFORMANCE
    # -----------------------------------------------------

    daily = build_daily_performance_HG(
        target_df,
        transaction_df
    )

    result["daily_performance"] = daily

    return result


# =========================================================
# RUN
# =========================================================

result = load_dashboard_data()

kpi = result["kpi"]


# =========================================================
# OVERALL PERFORMANCE
# =========================================================

st.markdown(
    '<div class="section-title">Overall Performance</div>',
    unsafe_allow_html=True
)

col1, col2, col3, col4 = st.columns(4)


with col1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Target</div>
            <div class="kpi-value">
                {format_rupiah(kpi["total_target"])}
            </div>
            <div class="kpi-caption">
                September target
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


with col2:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Actual Sales</div>
            <div class="kpi-value">
                {format_rupiah(kpi["total_actual"])}
            </div>
            <div class="kpi-caption">
                Successful transactions
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


with col3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Achievement</div>
            <div class="kpi-value">
                {format_percent(kpi["overall_achievement"])}
            </div>
            <div class="kpi-caption">
                Actual vs target
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


with col4:
    gap_value = kpi["total_gap"]

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Gap to Target</div>
            <div class="kpi-value">
                {format_rupiah(gap_value)}
            </div>
            <div class="kpi-caption">
                Actual − Target
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# AGENT SUMMARY
# =========================================================

st.divider()

st.markdown(
    '<div class="section-title">Agent Summary</div>',
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)


with col1:

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Agents Achieved Target</div>
            <div class="kpi-value">
                {kpi["agents_achieved"]} / {kpi["total_agents"]}
            </div>
            <div class="kpi-caption">
                Agents reaching ≥ 100% achievement
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


with col2:

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Agent Achievement Rate</div>
            <div class="kpi-value">
                {format_percent(kpi["agent_achievement_rate"])}
            </div>
            <div class="kpi-caption">
                Achieved agents / total agents
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# DAILY PERFORMANCE
# =========================================================

st.divider()

st.markdown(
    '<div class="section-title">Daily Performance</div>',
    unsafe_allow_html=True
)

daily = result["daily_performance"].copy()

daily_chart = daily.set_index("day")[
    ["target", "actual"]
]

st.line_chart(
    daily_chart,
    height=350
)


# =========================================================
# ROLE & TIER PERFORMANCE
# =========================================================

st.divider()

col1, col2 = st.columns(2)


with col1:

    st.markdown(
        '<div class="section-title">Role Performance</div>',
        unsafe_allow_html=True
    )

    role = result["role_performance"].copy()

    role_chart = role.set_index("Role")[
        ["target", "actual"]
    ]

    st.bar_chart(
        role_chart,
        height=320
    )


with col2:

    st.markdown(
        '<div class="section-title">Tier Performance</div>',
        unsafe_allow_html=True
    )

    tier = result["tier_performance"].copy()

    tier_chart = tier.set_index("Tier")[
        ["target", "actual"]
    ]

    st.bar_chart(
        tier_chart,
        height=320
    )


# =========================================================
# TOP & BOTTOM PERFORMERS
# =========================================================

st.divider()

col1, col2 = st.columns(2)


with col1:

    st.markdown(
        '<div class="section-title">🏆 Top Performers</div>',
        unsafe_allow_html=True
    )

    top_agents = result["top_agents"].copy()

    top_display = top_agents[
        [
            "Nama Agent",
            "Role",
            "Tier",
            "achievement"
        ]
    ].copy()

    top_display["achievement"] = (
        top_display["achievement"]
        .map(format_percent)
    )

    st.dataframe(
        top_display,
        hide_index=True,
        use_container_width=True,
        height=390
    )


with col2:

    st.markdown(
        '<div class="section-title">📉 Bottom Performers</div>',
        unsafe_allow_html=True
    )

    bottom_agents = result["bottom_agents"].copy()

    bottom_display = bottom_agents[
        [
            "Nama Agent",
            "Role",
            "Tier",
            "achievement"
        ]
    ].copy()

    bottom_display["achievement"] = (
        bottom_display["achievement"]
        .map(format_percent)
    )

    st.dataframe(
        bottom_display,
        hide_index=True,
        use_container_width=True,
        height=390
    )


# =========================================================
# AGENT PERFORMANCE DETAIL
# =========================================================

st.divider()

st.markdown(
    '<div class="section-title">Agent Performance Detail</div>',
    unsafe_allow_html=True
)

agent_detail = result["agent_performance"].copy()

agent_detail = agent_detail[
    [
        "rank",
        "Nama Agent",
        "Role",
        "Tier",
        "target",
        "actual",
        "achievement",
        "gap",
        "performance_status"
    ]
].copy()


# Format table
agent_detail["target"] = (
    agent_detail["target"]
    .map(format_rupiah_full)
)

agent_detail["actual"] = (
    agent_detail["actual"]
    .map(format_rupiah_full)
)

agent_detail["achievement"] = (
    agent_detail["achievement"]
    .map(format_percent)
)

agent_detail["gap"] = (
    agent_detail["gap"]
    .map(format_rupiah_full)
)


# Rename columns for presentation
agent_detail = agent_detail.rename(
    columns={
        "rank": "Rank",
        "Nama Agent": "Agent",
        "Role": "Role",
        "Tier": "Tier",
        "target": "Target",
        "actual": "Actual",
        "achievement": "Achievement",
        "gap": "Gap",
        "performance_status": "Status"
    }
)


st.dataframe(
    agent_detail,
    hide_index=True,
    use_container_width=True,
    height=650
)


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        Healthy Go · Sales Performance Dashboard · September 2026
    </div>
    """,
    unsafe_allow_html=True
)
