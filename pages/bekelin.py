import streamlit as st
from google_sheet import connect_google_sheet
from transaction_BK import build_transaction_BK
from target_agent_BK import build_target_actual_BK
from kpi_BK import build_daily_performance_BK
from kpi_BK import build_kpi_BK

# =========================================================
# PAGE HEADER
# =========================================================

st.title("🛍️ Bekelin")
st.caption("September 2026 • Sales Performance Dashboard")

st.markdown("---")


# =========================================================
# KPI
# =========================================================

st.subheader("Performance Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Target",
        "Rp3,00 M",
        "Rp3.000.104.970"
    )

with col2:
    st.metric(
        "Actual Sales",
        "Rp2,44 M",
        "Rp2.443.764.000"
    )

with col3:
    st.metric(
        "Achievement",
        "81,46%",
        "7 of 20 agents achieved"
    )

with col4:
    st.metric(
        "Gap",
        "-Rp556,34 Jt",
        "Actual − Target"
    )

# =========================================================
# AGENT SUMMARY
# =========================================================

st.markdown("---")

st.subheader("Agent Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 20")
    st.caption("Total Agents")

with col2:
    st.markdown("### 7")
    st.caption("Achieved")

with col3:
    st.markdown("### 2")
    st.caption("Near Target")

with col4:
    st.markdown("### 11")
    st.caption("Below Target")


st.caption("35% of Bekelin agents have achieved their monthly target.")

# =========================================================
# DAILY PERFORMANCE
# =========================================================

st.markdown("---")

st.subheader("Daily Performance")
st.caption("Target vs Actual Sales Bekelin selama September 2026.")


@st.cache_data
def load_bekelin_data():
    import pandas as pd

    spreadsheet = connect_google_sheet()

    target_df = pd.DataFrame(
        spreadsheet.worksheet("TARGET AGENT").get_all_records()
    )

    sales_df = pd.DataFrame(
        spreadsheet.worksheet("SALES BK").get_all_records()
    )

    transaction_df = build_transaction_BK(sales_df)

    target_actual_df = build_target_actual_BK(
        target_df,
        transaction_df
    )

    daily_df = build_daily_performance_BK(
        target_df,
        transaction_df
    )

    kpi_result = build_kpi_BK(
        target_actual_df
    )

    return target_actual_df, daily_df, kpi_result


target_actual_df, daily_df, kpi_result = load_bekelin_data()

chart_data = daily_df[
    ["day", "target", "actual"]
].copy()

chart_data["day"] = chart_data["day"].astype(int)

chart_data = chart_data.sort_values("day")

chart_data = chart_data.set_index("day")

st.line_chart(
    chart_data,
    y=["target", "actual"]
)

# =========================================================
# ROLE PERFORMANCE
# =========================================================

st.markdown("---")

st.subheader("Performance by Role")
st.caption("Perbandingan target dan actual berdasarkan role agent.")

role_performance = kpi_result["role_performance"].copy()

role_chart = role_performance[
    ["Role", "target", "actual"]
].copy()

role_chart = role_chart.rename(
    columns={
        "target": "Target",
        "actual": "Actual",
    }
)

role_chart = role_chart.set_index("Role")

st.bar_chart(
    role_chart,
    height=320,
)

# =========================================================
# TIER PERFORMANCE
# =========================================================

st.markdown("---")

st.subheader("Performance by Tier")
st.caption("Perbandingan target dan actual berdasarkan tier agent.")

tier_performance = kpi_result["tier_performance"].copy()

tier_chart = tier_performance[
    ["Tier", "target", "actual"]
].copy()

tier_chart = tier_chart.rename(
    columns={
        "target": "Target",
        "actual": "Actual",
    }
)

tier_chart = tier_chart.set_index("Tier")

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

    top_agents = kpi_result["top_agents"].copy()

    top_display = top_agents[
        ["Nama Agent", "Role", "Tier", "achievement"]
    ].copy()

    top_display["Achievement"] = top_display["achievement"].apply(
        lambda x: f"{x:.2f}%".replace(".", ",")
    )

    top_display = top_display[
        ["Nama Agent", "Role", "Tier", "Achievement"]
    ]

    st.dataframe(
        top_display,
        use_container_width=True,
        hide_index=True
    )


with col2:
    st.subheader("📉 Bottom Performers")
    st.caption("Agent yang membutuhkan perhatian lebih.")

    bottom_agents = kpi_result["bottom_agents"].copy()

    bottom_display = bottom_agents[
        ["Nama Agent", "Role", "Tier", "achievement"]
    ].copy()

    bottom_display["Achievement"] = bottom_display["achievement"].apply(
        lambda x: f"{x:.2f}%".replace(".", ",")
    )

    bottom_display = bottom_display[
        ["Nama Agent", "Role", "Tier", "Achievement"]
    ]

    st.dataframe(
        bottom_display,
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# AGENT PERFORMANCE DETAIL
# =========================================================

st.markdown("---")

st.subheader("Agent Performance Detail")
st.caption(
    "Detail pencapaian target setiap agent Bekelin."
)

agent_detail = kpi_result["agent_performance"].copy()

# Pastikan rank tersedia
if "rank" not in agent_detail.columns:
    agent_detail = agent_detail.sort_values(
        "achievement",
        ascending=False
    ).reset_index(drop=True)

    agent_detail.insert(
        0,
        "rank",
        range(1, len(agent_detail) + 1)
    )

agent_display = agent_detail[
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

# Format angka
agent_display["Target"] = agent_display["target"].apply(
    lambda x: f"Rp{x:,.0f}".replace(",", ".")
)

agent_display["Actual"] = agent_display["actual"].apply(
    lambda x: f"Rp{x:,.0f}".replace(",", ".")
)

agent_display["Achievement"] = agent_display["achievement"].apply(
    lambda x: f"{x:.2f}%".replace(".", ",")
)

agent_display["Gap"] = agent_display["gap"].apply(
    lambda x: f"Rp{x:,.0f}".replace(",", ".")
)

# Rename kolom
agent_display = agent_display[
    [
        "rank",
        "Nama Agent",
        "Role",
        "Tier",
        "Target",
        "Actual",
        "Achievement",
        "Gap",
        "performance_status"
    ]
].rename(
    columns={
        "rank": "Rank",
        "performance_status": "Status"
    }
)

st.dataframe(
    agent_display,
    use_container_width=True,
    hide_index=True,
    height=600
)
