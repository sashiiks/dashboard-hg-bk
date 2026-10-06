import pandas as pd
import streamlit as st

from build_dashboard_performance import (
    build_dashboard_performance,
    build_range_performance,
    clear_dashboard_cache,
)


# =========================================================
# 1. APP CONFIG
# =========================================================

st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# 2. HELPER
# =========================================================

def safe_float(value):
    """Konversi value ke float dengan aman."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def format_rupiah(value):
    """Format angka menjadi Rupiah."""
    value = safe_float(value)
    return f"Rp{value:,.0f}".replace(",", ".")


def format_pct(value):
    """Format angka percentage."""
    value = safe_float(value)
    return f"{value:.2f}%".replace(".", ",")


def get_latest_update(perf):
    """
    Mengambil timestamp update source terbaru
    dari data performance.
    """
    if perf is None or perf.empty:
        return None

    if "source_updated_at" in perf.columns:
        source_update = pd.to_datetime(
            perf["source_updated_at"],
            errors="coerce",
        ).dropna()

        if not source_update.empty:
            return source_update.max()

    if "performance_datetime" in perf.columns:
        performance_update = pd.to_datetime(
            perf["performance_datetime"],
            errors="coerce",
        ).dropna()

        if not performance_update.empty:
            return performance_update.max()

    return None


def get_company_period(target_company):
    """
    Mengambil periode aktif berdasarkan target date
    yang tersedia untuk company.
    """
    if target_company.empty:
        return None, None

    target_dates = pd.to_datetime(
        target_company["target_date"],
        errors="coerce",
    ).dropna()

    if target_dates.empty:
        return None, None

    target_dates = target_dates.dt.normalize()

    return (
        target_dates.min(),
        target_dates.max(),
    )


def get_company_summary(
    perf,
    target,
    company,
):
    """
    Mengambil summary performance untuk satu company.

    Periode:
    - start = tanggal pertama target;
    - end   = tanggal terakhir target.
    """

    empty_summary = {
        "target": 0,
        "paid": 0,
        "unpaid": 0,
        "achievement_pct": 0,
        "projection_pct": 0,
        "start_date": None,
        "end_date": None,
    }

    if target is None or target.empty:
        return empty_summary

    if "company" not in target.columns:
        return empty_summary

    target_company = target.copy()

    target_company["_company_filter"] = (
        target_company["company"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    target_company = target_company[
        target_company["_company_filter"].eq(
            str(company).casefold()
        )
    ].copy()

    if target_company.empty:
        return empty_summary

    start_date, end_date = get_company_period(
        target_company
    )

    if start_date is None or end_date is None:
        return empty_summary

    try:
        summary = build_range_performance(
            start_date=start_date,
            end_date=end_date,
            company=company,
            team_leader="All",
            agent="All",
            role="All",
            tier="All",
        )
    except Exception:
        summary = None

    if not summary:
        return {
            **empty_summary,
            "start_date": start_date,
            "end_date": end_date,
        }

    return {
        "target": safe_float(
            summary.get("target", 0)
        ),
        "paid": safe_float(
            summary.get("paid", 0)
        ),
        "unpaid": safe_float(
            summary.get("unpaid", 0)
        ),
        "achievement_pct": safe_float(
            summary.get("achievement_pct", 0)
        ),
        "projection_pct": safe_float(
            summary.get("projection_pct", 0)
        ),
        "start_date": start_date,
        "end_date": end_date,
    }


# =========================================================
# 3. LIGHTWEIGHT CSS
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1450px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 4. SESSION STATE
# =========================================================

if "refresh_key" not in st.session_state:
    st.session_state.refresh_key = 0


# =========================================================
# 5. LOAD DATA
# =========================================================

try:
    with st.spinner("Mengambil data dashboard..."):
        perf, target = build_dashboard_performance()

except Exception as e:
    st.error(
        f"Gagal mengambil data dashboard: {e}"
    )
    st.stop()


# =========================================================
# 6. BASIC DATA SAFETY
# =========================================================

if perf is None or perf.empty:
    st.warning(
        "Data performance belum tersedia."
    )
    st.stop()


if target is None or target.empty:
    st.warning(
        "Data target belum tersedia."
    )
    st.stop()


# =========================================================
# 7. HEADER
# =========================================================

st.title(
    "Executive Performance Dashboard"
)

st.write(
    "Ringkasan performa Healthy Go dan Bekelin "
    "berdasarkan data terbaru dari Google Sheets."
)


# =========================================================
# 8. LIVE SOURCE STATUS
# =========================================================

latest_update = get_latest_update(perf)

if latest_update is not None:
    st.success(
        "🟢 LIVE · Last source update: "
        f"{latest_update.strftime('%d %b %Y, %H:%M:%S')}"
    )
else:
    st.info(
        "🟢 LIVE · Source update time unavailable"
    )


# =========================================================
# 9. REFRESH DATA
# =========================================================

refresh_col, spacer_col = st.columns(
    [1.2, 5]
)

with refresh_col:
    if st.button(
        "🔄 Refresh Data",
        use_container_width=True,
    ):
        with st.spinner(
            "Mengambil data terbaru dari Google Sheets..."
        ):
            clear_dashboard_cache()
            st.session_state.refresh_key += 1

        st.rerun()


st.divider()


# =========================================================
# 10. COMPANY PERFORMANCE
# =========================================================

st.subheader(
    "Company Performance"
)

st.caption(
    "Executive KPI berdasarkan data performance terbaru."
)


# =========================================================
# 11. COMPANY CARD RENDERER
# =========================================================

def render_company_card(
    company,
    company_name,
    icon,
):
    """
    Render executive KPI untuk satu company
    menggunakan native Streamlit.
    """

    summary = get_company_summary(
        perf=perf,
        target=target,
        company=company,
    )

    start_date = summary.get(
        "start_date"
    )

    end_date = summary.get(
        "end_date"
    )

    target_value = safe_float(
        summary.get("target", 0)
    )

    paid = safe_float(
        summary.get("paid", 0)
    )

    unpaid = safe_float(
        summary.get("unpaid", 0)
    )

    achievement = safe_float(
        summary.get("achievement_pct", 0)
    )

    projection = safe_float(
        summary.get("projection_pct", 0)
    )

    # -----------------------------------------------------
    # PERIOD
    # -----------------------------------------------------

    if (
        start_date is not None
        and end_date is not None
    ):
        if start_date == end_date:
            period_text = start_date.strftime(
                "%d %b %Y"
            )
        else:
            period_text = (
                f"{start_date.strftime('%d %b %Y')}"
                f" – "
                f"{end_date.strftime('%d %b %Y')}"
            )
    else:
        period_text = "Periode tidak tersedia"

    # -----------------------------------------------------
    # COMPANY CONTAINER
    # -----------------------------------------------------

    with st.container(border=True):

        # -------------------------------------------------
        # COMPANY HEADER
        # -------------------------------------------------

        header_left, header_right = st.columns(
            [5, 1]
        )

        with header_left:
            st.subheader(
                f"{icon} {company_name}"
            )

            st.caption(
                f"Performance period · {period_text}"
            )

        with header_right:
            st.success(
                "🟢 LIVE"
            )

        # -------------------------------------------------
        # KPI ROW
        # -------------------------------------------------

        kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

        with kpi_1:
            st.metric(
                label="PAID",
                value=format_rupiah(paid),
            )

        with kpi_2:
            st.metric(
                label="UNPAID",
                value=format_rupiah(unpaid),
            )

        with kpi_3:
            st.metric(
                label="ACHIEVEMENT",
                value=format_pct(achievement),
            )

        with kpi_4:
            st.metric(
                label="PROJECTION",
                value=format_pct(projection),
            )

        # -------------------------------------------------
        # TARGET
        # -------------------------------------------------

        st.caption(
            f"Target periode: {format_rupiah(target_value)}"
        )

        # -------------------------------------------------
        # ACHIEVEMENT PROGRESS
        # -------------------------------------------------

        progress_value = min(
            max(achievement / 100, 0),
            1,
        )

        st.progress(
            progress_value,
            text=(
                f"Achievement Progress · "
                f"{format_pct(achievement)}"
            ),
        )

    # -----------------------------------------------------
    # NAVIGATION
    # -----------------------------------------------------

    if company == "HG":
        page_path = "pages/healthy_go.py"
        button_label = "Open Healthy Go Dashboard"
    else:
        page_path = "pages/bekelin.py"
        button_label = "Open Bekelin Dashboard"

    st.page_link(
        page_path,
        label=button_label,
        icon="📊",
        use_container_width=True,
    )

    st.write("")


# =========================================================
# 12. HEALTHY GO
# =========================================================

render_company_card(
    company="HG",
    company_name="Healthy Go",
    icon="🥗",
)


# =========================================================
# 13. BEKELIN
# =========================================================

render_company_card(
    company="BK",
    company_name="Bekelin",
    icon="🛒",
)


# =========================================================
# 14. LAST UPDATE
# =========================================================

st.divider()

if latest_update is not None:
    st.caption(
        "Sales Performance Dashboard · "
        "🟢 LIVE · "
        f"Last update "
        f"{latest_update.strftime('%d %b %Y, %H:%M:%S')}"
    )
else:
    st.caption(
        "Sales Performance Dashboard · 🟢 LIVE"
    )
