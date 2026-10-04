import streamlit as st

st.title("📊 Sales Performance Hub")
st.caption("September 2026 • Healthy Go & Bekelin")

st.markdown("---")

# =========================================================
# BUSINESS OVERVIEW
# =========================================================

st.subheader("Business Overview")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏥 Healthy Go")

    st.metric(
        "Achievement",
        "80,75%"
    )

    st.write("Actual Sales")
    st.markdown("### Rp14,54 M")
    st.caption("Rp14.535.010.000")

    st.caption("52 agents • 5 achieved")


with col2:
    st.markdown("### 🛍️ Bekelin")

    st.metric(
        "Achievement",
        "81,46%"
    )

    st.write("Actual Sales")
    st.markdown("### Rp2,44 M")
    st.caption("Rp2.443.764.000")

    st.caption("20 agents • 7 achieved")


st.markdown("---")


# =========================================================
# OVERALL SALES SNAPSHOT
# =========================================================

st.subheader("Overall Sales Snapshot")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**Total Target**")
    st.markdown("### Rp21,00 M")
    st.caption("Rp21.000.105.250")

with col2:
    st.markdown("**Actual Sales**")
    st.markdown("### Rp16,98 M")
    st.caption("Rp16.978.774.000")

with col3:
    st.markdown("**Achievement**")
    st.markdown("### 80,85%")
    st.caption("Overall achievement")

with col4:
    st.markdown("**Gap**")
    st.markdown("### -Rp4,02 M")
    st.caption("-Rp4.021.331.250")


st.markdown("---")


# =========================================================
# ACHIEVEMENT BY BUSINESS UNIT
# =========================================================

st.subheader("Achievement by Business Unit")

st.caption(
    "Perbandingan pencapaian target antara Healthy Go dan Bekelin."
)

chart_data = {
    "Business Unit": ["Healthy Go", "Bekelin"],
    "Achievement": [80.75, 81.46],
}

st.bar_chart(
    chart_data,
    x="Business Unit",
    y="Achievement",
    color="Business Unit",
)
