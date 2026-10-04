import streamlit as st
import pandas as pd

from google_sheet import connect_google_sheet, get_sales_hg
from transaction_HG import build_transaction_HG
from target_agent_HG import build_target_actual_HG
from kpi_HG import (
    build_kpi_HG,
    build_daily_performance_HG,
    build_agent_performance_HG,
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_rupiah(value):
    """Format angka menjadi Rupiah compact."""
    value = float(value)
    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        return f"Rp{value / 1_000_000_000:.2f} M".replace(".", ",")
    elif abs_value >= 1_000_000:
        return f"Rp{value / 1_000_000:.2f} Jt".replace(".", ",")
    elif abs_value >= 1_000:
        return f"Rp{value / 1_000:.1f} Rb".replace(".", ",")
    else:
        return f"Rp{value:,.0f}".replace(",", ".")


def format_rupiah_full(value):
    """Format Rupiah lengkap."""
    return f"Rp{float(value):,.0f}".replace(",", ".")


def format_percent(value):
    """Format percentage."""
    if pd.isna(value):
        return "-"
    return f"{float(value):.2f}%".replace(".", ",")


# =========================================================
# HEADER
# =========================================================

st.title("🏥 Healthy Go")
st.caption("September 2026 • Sales Performance Dashboard")

st.markdown("---")


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


result = load_dashboard_data()
kpi = result["kpi"]


# =========================================================
# OVERALL PERFORMANCE
# =========================================================

st.subheader("Overall Performance")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Target",
        format_rupiah(kpi["total_target"]),
        "September target",
    )

with col2:
    st.metric(
        "Actual Sales",
        format_rupiah(kpi["total_actual"]),
        "Successful transactions",
    )

with col3:
    st.metric(
        "Achievement",
        format_percent(kpi["overall_achievement"]),
        "Actual vs target",
    )

with col4:
    st.metric(
        "Gap to Target",
        format_rupiah(kpi["total_gap"]),
        "Actual − Target",
    )


# =========================================================
# AGENT SUMMARY
# =========================================================

st.markdown("---")

st.subheader("Agent Summary")

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Agents Achieved Target",
        f'{kpi["agents_achieved"]} / {kpi["total_agents"]}',
        "Agents reaching ≥ 100%",
    )

with col2:
    st.metric(
        "Agent Achievement Rate",
        format_percent(kpi["agent_achievement_rate"]),
        "Achieved agents / total agents",
    )


# =========================================================
# DAILY PERFORMANCE
# =========================================================

st.markdown("---")

st.subheader("Daily Performance")
st.caption("Target vs Actual Sales selama September 2026.")

daily = result["daily_performance"].copy()

daily_chart = daily.set_index("day")[
    ["target", "actual"]
]

st.line_chart(
    daily_chart,
    height=350,
)


# =========================================================
# ROLE & TIER PERFORMANCE
# =========================================================

st.markdown("---")

col1, col2 = st.columns(2)

with col1:

    st.subheader("Role Performance")

    role = result["role_performance"].copy()

    role_chart = role.set_index("Role")[
        ["target", "actual"]
    ]

    st.bar_chart(
        role_chart,
        height=320,
    )


with col2:

    st.subheader("Tier Performance")

    tier = result["tier_performance"].copy()

    tier_chart = tier.set_index("Tier")[
        ["target", "actual"]
    ]

    st.bar_chart(
        tier_chart,
        height=320,
    )


# =========================================================
# TOP & BOTTOM PERFORMERS
# =========================================================

st.markdown("---")

col1, col2 = st.columns(2)

with col1:

    st.subheader("🏆 Top Performers")
    st.caption("Agent dengan achievement tertinggi.")

    top_agents = result["top_agents"].copy()

    top_display = top_agents[
        [
            "Nama Agent",
            "Role",
            "Tier",
            "achievement",
        ]
    ].copy()

    top_display["Achievement"] = (
        top_display["achievement"]
        .map(format_percent)
    )

    top_display = top_display[
        [
            "Nama Agent",
            "Role",
            "Tier",
            "Achievement",
        ]
    ]

    st.dataframe(
        top_display,
        hide_index=True,
        use_container_width=True,
        height=390,
    )


with col2:

    st.subheader("📉 Bottom Performers")
    st.caption("Agent yang membutuhkan perhatian lebih.")

    bottom_agents = result["bottom_agents"].copy()

    bottom_display = bottom_agents[
        [
            "Nama Agent",
            "Role",
            "Tier",
            "achievement",
        ]
    ].copy()

    bottom_display["Achievement"] = (
        bottom_display["achievement"]
        .map(format_percent)
    )

    bottom_display = bottom_display[
        [
            "Nama Agent",
            "Role",
            "Tier",
            "Achievement",
        ]
    ]

    st.dataframe(
        bottom_display,
        hide_index=True,
        use_container_width=True,
        height=390,
    )


# =========================================================
# AGENT PERFORMANCE DETAIL
# =========================================================

st.markdown("---")

st.subheader("Agent Performance Detail")
st.caption("Detail pencapaian target setiap agent Healthy Go.")

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
        "performance_status",
    ]
].copy()


agent_detail["Target"] = (
    agent_detail["target"]
    .map(format_rupiah_full)
)

agent_detail["Actual"] = (
    agent_detail["actual"]
    .map(format_rupiah_full)
)

agent_detail["Achievement"] = (
    agent_detail["achievement"]
    .map(format_percent)
)

agent_detail["Gap"] = (
    agent_detail["gap"]
    .map(format_rupiah_full)
)


agent_detail = agent_detail.rename(
    columns={
        "rank": "Rank",
        "Nama Agent": "Agent",
        "performance_status": "Status",
    }
)


agent_detail = agent_detail[
    [
        "Rank",
        "Agent",
        "Role",
        "Tier",
        "Target",
        "Actual",
        "Achievement",
        "Gap",
        "Status",
    ]
]


st.dataframe(
    agent_detail,
    hide_index=True,
    use_container_width=True,
    height=650,
)


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "Healthy Go · Sales Performance Dashboard · September 2026"
)
