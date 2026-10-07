# ============================================================
# HEALTHY GO PERFORMANCE DASHBOARD
# Native Streamlit version - tanpa HTML / div
# ============================================================

# ============================================================
# 1. IMPORT
# ============================================================

import inspect
from datetime import timedelta

import pandas as pd
import streamlit as st

from build_dashboard_performance import (
    build_dashboard_performance,
    build_range_performance,
    build_daily_performance,
    build_agent_ranking,
    clear_dashboard_cache,
)


# ============================================================
# 2. PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Healthy Go Performance Dashboard",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# 3. LIGHTWEIGHT PAGE STYLE
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    /* ========================================================
       COMPACT KPI
       ======================================================== */

    .st-key-hg_kpi div[data-testid="stMetric"] {
        padding: 0.45rem 0.55rem !important;
        min-height: 0 !important;
    }

    .st-key-hg_kpi div[data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        line-height: 1.1 !important;
    }

    .st-key-hg_kpi div[data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
        line-height: 1.1 !important;
        white-space: nowrap !important;
        overflow: visible !important;
        letter-spacing: -0.02em !important;
    }

    .st-key-hg_kpi div[data-testid="stMetricValue"] > div {
        font-size: inherit !important;
    }

    .st-key-hg_kpi div[data-testid="stMetricDelta"] {
        font-size: 0.7rem !important;
    }

    /* ========================================================
       AGENT ASSIGNMENT COLUMN
       ======================================================== */

    .st-key-hg_agent_ranking [data-testid="stDataFrame"] {
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 4. HELPER FORMAT
# ============================================================

def rupiah(value):
    """Format angka menjadi Rupiah."""
    try:
        value = float(value or 0)
    except Exception:
        value = 0

    return f"Rp {value:,.0f}".replace(",", ".")


def number(value):
    """Format angka biasa."""
    try:
        value = float(value or 0)
    except Exception:
        value = 0

    return f"{value:,.0f}".replace(",", ".")


def pct(value):
    """Format percentage."""
    try:
        value = float(value or 0)
    except Exception:
        value = 0

    return f"{value:.2f}%"


def safe_float(value):
    """Konversi value menjadi float dengan aman."""
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def normalize_text(value):
    """Normalisasi text."""
    if pd.isna(value):
        return ""

    return str(value).strip()


def clean_agent_name(value):
    """Membersihkan nama agent / team leader."""
    value = normalize_text(value)

    if not value:
        return "-"

    return value


def first_or_none(values):
    """Mengambil value pertama dari list."""
    if not values:
        return None

    return values[0]


def to_bool_series(series):
    """Konversi berbagai format boolean menjadi boolean."""
    if series is None:
        return pd.Series(dtype=bool)

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).ne(0)

    return (
        series.astype("string")
        .str.strip()
        .str.casefold()
        .isin(
            [
                "true",
                "1",
                "1.0",
                "yes",
                "y",
                "ya",
            ]
        )
    )


# ============================================================
# 5. COLUMN HELPERS
# ============================================================

def find_column(df, candidates):
    """Mencari kolom pertama yang tersedia."""
    if df is None or df.empty:
        return None

    for col in candidates:
        if col in df.columns:
            return col

    return None


# ============================================================
# 6. LOAD DATA
# ============================================================

@st.cache_data(show_spinner=False)
def load_data():
    perf, target = build_dashboard_performance()

    return perf.copy(), target.copy()


# ============================================================
# 7. GENERIC BUILDER CALLER
# ============================================================

def call_dashboard_builder(
    builder,
    perf,
    target,
    start_date,
    end_date,
    company,
    team_leader=None,
    agent=None,
    role=None,
    tier=None,
):
    """
    Memanggil builder hanya dengan parameter yang tersedia.

    Ini mencegah error:
    got multiple values for argument ...
    """

    signature = inspect.signature(builder)
    params = signature.parameters

    kwargs = {}

    if "perf" in params:
        kwargs["perf"] = perf

    if "target" in params:
        kwargs["target"] = target

    if "start_date" in params:
        kwargs["start_date"] = start_date

    if "end_date" in params:
        kwargs["end_date"] = end_date

    if "company" in params:
        kwargs["company"] = company

    if "team_leader" in params:
        kwargs["team_leader"] = team_leader

    if "agent" in params:
        kwargs["agent"] = agent

    if "role" in params:
        kwargs["role"] = role

    if "tier" in params:
        kwargs["tier"] = tier

    return builder(**kwargs)


# ============================================================
# 8. FILTER PERFORMANCE
# ============================================================

def filter_performance(
    perf,
    company,
    start_date,
    end_date,
    selected_team_leader=None,
    selected_agent=None,
    selected_role=None,
    selected_tier=None,
):
    df = perf.copy()

    if df.empty:
        return df

    # --------------------------------------------------------
    # COMPANY
    # --------------------------------------------------------

    if "company" in df.columns:
        df = df[
            df["company"]
            .astype("string")
            .str.strip()
            .str.casefold()
            == str(company).casefold()
        ]

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    date_col = find_column(
        df,
        [
            "performance_date",
            "dashboard_date",
            "tanggal",
        ],
    )

    if date_col:
        df[date_col] = pd.to_datetime(
            df[date_col],
            errors="coerce",
        ).dt.date

        if start_date:
            df = df[df[date_col] >= start_date]

        if end_date:
            df = df[df[date_col] <= end_date]

    # --------------------------------------------------------
    # TEAM LEADER
    # --------------------------------------------------------

    if selected_team_leader and "team_leader" in df.columns:
        allowed = {
            normalize_text(x).casefold()
            for x in selected_team_leader
        }

        df = df[
            df["team_leader"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(allowed)
        ]

    # --------------------------------------------------------
    # AGENT
    # --------------------------------------------------------

    if selected_agent and "agent" in df.columns:
        allowed = {
            normalize_text(x).casefold()
            for x in selected_agent
        }

        df = df[
            df["agent"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(allowed)
        ]

    # --------------------------------------------------------
    # ROLE
    # --------------------------------------------------------

    if selected_role and "role" in df.columns:
        allowed = {
            normalize_text(x).casefold()
            for x in selected_role
        }

        df = df[
            df["role"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(allowed)
        ]

    # --------------------------------------------------------
    # TIER
    # --------------------------------------------------------

    if selected_tier and "tier" in df.columns:
        allowed = {
            normalize_text(x).casefold()
            for x in selected_tier
        }

        df = df[
            df["tier"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(allowed)
        ]

    return df


# ============================================================
# 9. FILTER TARGET
# ============================================================

def filter_target(
    target,
    company,
    start_date=None,
    end_date=None,
    selected_team_leader=None,
    selected_agent=None,
    selected_role=None,
    selected_tier=None,
):
    df = target.copy()

    if df.empty:
        return df

    # --------------------------------------------------------
    # COMPANY
    # --------------------------------------------------------

    if "company" in df.columns:
        df = df[
            df["company"]
            .astype("string")
            .str.strip()
            .str.casefold()
            == str(company).casefold()
        ]

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if "target_date" in df.columns:
        df["target_date"] = pd.to_datetime(
            df["target_date"],
            errors="coerce",
        ).dt.date

        if start_date:
            df = df[df["target_date"] >= start_date]

        if end_date:
            df = df[df["target_date"] <= end_date]

    # --------------------------------------------------------
    # TEAM LEADER
    # --------------------------------------------------------

    if selected_team_leader and "team_leader" in df.columns:
        allowed = {
            normalize_text(x).casefold()
            for x in selected_team_leader
        }

        df = df[
            df["team_leader"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(allowed)
        ]

    # --------------------------------------------------------
    # AGENT
    # --------------------------------------------------------

    if selected_agent and "agent" in df.columns:
        allowed = {
            normalize_text(x).casefold()
            for x in selected_agent
        }

        df = df[
            df["agent"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(allowed)
        ]

    # --------------------------------------------------------
    # ROLE
    # --------------------------------------------------------

    if selected_role and "role" in df.columns:
        allowed = {
            normalize_text(x).casefold()
            for x in selected_role
        }

        df = df[
            df["role"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(allowed)
        ]

    # --------------------------------------------------------
    # TIER
    # --------------------------------------------------------

    if selected_tier and "tier" in df.columns:
        allowed = {
            normalize_text(x).casefold()
            for x in selected_tier
        }

        df = df[
            df["tier"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(allowed)
        ]

    return df


# ============================================================
# 10. CALCULATE UNIQUE INVOICE QUANTITY
# ============================================================

def calculate_invoice_quantity(perf):
    if perf is None or perf.empty:
        return pd.DataFrame(
            columns=[
                "company",
                "agent",
                "role",
                "team_leader",
                "tier",
                "Qty Invoice Paid",
                "Qty Invoice Unpaid",
            ]
        )

    df = perf.copy()

    required_identity = [
        "company",
        "agent",
        "role",
        "team_leader",
        "tier",
        "invoice_no",
    ]

    for col in required_identity:
        if col not in df.columns:
            df[col] = ""

    if "is_paid" not in df.columns:
        df["is_paid"] = False

    if "is_unpaid" not in df.columns:
        df["is_unpaid"] = False

    if "is_excluded" not in df.columns:
        df["is_excluded"] = False

    df["is_paid"] = to_bool_series(
        df["is_paid"]
    )

    df["is_unpaid"] = to_bool_series(
        df["is_unpaid"]
    )

    df["is_excluded"] = to_bool_series(
        df["is_excluded"]
    )

    df["invoice_no"] = (
        df["invoice_no"]
        .astype("string")
        .str.strip()
    )

    valid = df[
        (~df["is_excluded"])
        & df["invoice_no"].notna()
        & df["invoice_no"].ne("")
        & df["invoice_no"].ne("nan")
    ].copy()

    if valid.empty:
        return pd.DataFrame(
            columns=[
                "company",
                "agent",
                "role",
                "team_leader",
                "tier",
                "Qty Invoice Paid",
                "Qty Invoice Unpaid",
            ]
        )

    # --------------------------------------------------------
    # SATUKAN STATUS PER INVOICE
    # --------------------------------------------------------

    invoice_state = (
        valid.groupby(
            [
                "company",
                "agent",
                "role",
                "team_leader",
                "tier",
                "invoice_no",
            ],
            dropna=False,
        )
        .agg(
            is_paid=("is_paid", "max"),
            is_unpaid=("is_unpaid", "max"),
        )
        .reset_index()
    )

    invoice_state["is_paid"] = (
        invoice_state["is_paid"].astype(bool)
    )

    invoice_state["is_unpaid"] = (
        invoice_state["is_unpaid"].astype(bool)
        & ~invoice_state["is_paid"]
    )

    # --------------------------------------------------------
    # HITUNG QTY INVOICE
    # --------------------------------------------------------

    qty = (
        invoice_state.groupby(
            [
                "company",
                "agent",
                "role",
                "team_leader",
                "tier",
            ],
            dropna=False,
        )
        .agg(
            **{
                "Qty Invoice Paid": (
                    "is_paid",
                    "sum",
                ),
                "Qty Invoice Unpaid": (
                    "is_unpaid",
                    "sum",
                ),
            }
        )
        .reset_index()
    )

    return qty


# ============================================================
# 11. MERGE QTY KE AGENT RANKING
# ============================================================

def merge_invoice_quantity(ranking, perf):
    ranking = (
        ranking.copy()
        if ranking is not None
        else pd.DataFrame()
    )

    qty = calculate_invoice_quantity(perf)

    identity = [
        "company",
        "agent",
        "role",
        "team_leader",
        "tier",
    ]

    for col in identity:
        if col not in ranking.columns:
            ranking[col] = ""

        if col not in qty.columns:
            qty[col] = ""

    qty_columns = [
        "Qty Invoice Paid",
        "Qty Invoice Unpaid",
    ]

    if qty.empty:
        for col in qty_columns:
            ranking[col] = 0

        return ranking

    ranking = ranking.drop(
        columns=qty_columns,
        errors="ignore",
    )

    ranking = ranking.merge(
        qty[
            identity + qty_columns
        ],
        on=identity,
        how="left",
    )

    ranking["Qty Invoice Paid"] = (
        pd.to_numeric(
            ranking["Qty Invoice Paid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    ranking["Qty Invoice Unpaid"] = (
        pd.to_numeric(
            ranking["Qty Invoice Unpaid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    return ranking


# ============================================================
# 12. CALCULATE AGENT MTD
# ============================================================

def calculate_agent_mtd(
    perf,
    target,
    company,
    start_date,
    end_date,
    selected_team_leader=None,
    selected_agent=None,
    selected_role=None,
    selected_tier=None,
):
    if not end_date:
        return pd.DataFrame()

    month_start = end_date.replace(day=1)

    target_period_df = filter_target(
        target,
        company,
        start_date,
        end_date,
        selected_team_leader,
        selected_agent,
        selected_role,
        selected_tier,
    )

    target_month_df = filter_target(
        target,
        company,
        month_start,
        None,
        selected_team_leader,
        selected_agent,
        selected_role,
        selected_tier,
    )

    target_mtd_df = filter_target(
        target,
        company,
        month_start,
        end_date,
        selected_team_leader,
        selected_agent,
        selected_role,
        selected_tier,
    )

    for df in [
        target_period_df,
        target_month_df,
        target_mtd_df,
    ]:
        if not df.empty:
            df["daily_target"] = pd.to_numeric(
                df["daily_target"],
                errors="coerce",
            ).fillna(0)

    if target_period_df.empty:
        return pd.DataFrame()

    identity_cols = [
        "agent",
        "role",
        "team_leader",
        "tier",
    ]

    for col in identity_cols:
        for df in [
            target_period_df,
            target_month_df,
            target_mtd_df,
        ]:
            if col not in df.columns:
                df[col] = ""

    period_target = (
        target_period_df
        .groupby(
            identity_cols,
            dropna=False,
        )["daily_target"]
        .sum()
        .reset_index(name="Target Periode")
    )

    monthly_target = (
        target_month_df
        .groupby(
            identity_cols,
            dropna=False,
        )["daily_target"]
        .sum()
        .reset_index(name="Target Bulanan")
    )

    mtd_target = (
        target_mtd_df
        .groupby(
            identity_cols,
            dropna=False,
        )["daily_target"]
        .sum()
        .reset_index(name="Target MTD")
    )

    result = period_target.merge(
        monthly_target,
        on=identity_cols,
        how="left",
    )

    result = result.merge(
        mtd_target,
        on=identity_cols,
        how="left",
    )

    # --------------------------------------------------------
    # PERFORMANCE MTD
    # --------------------------------------------------------

    perf_mtd = filter_performance(
        perf,
        company,
        month_start,
        end_date,
        selected_team_leader,
        selected_agent,
        selected_role,
        selected_tier,
    )

    if perf_mtd.empty:
        result["MTD Paid"] = 0
        result["MTD Unpaid"] = 0

    else:
        for col in [
            "paid",
            "unpaid",
        ]:
            if col not in perf_mtd.columns:
                perf_mtd[col] = 0

            perf_mtd[col] = pd.to_numeric(
                perf_mtd[col],
                errors="coerce",
            ).fillna(0)

        performance = (
            perf_mtd
            .groupby(
                identity_cols,
                dropna=False,
            )
            .agg(
                **{
                    "MTD Paid": (
                        "paid",
                        "sum",
                    ),
                    "MTD Unpaid": (
                        "unpaid",
                        "sum",
                    ),
                }
            )
            .reset_index()
        )

        result = result.merge(
            performance,
            on=identity_cols,
            how="left",
        )

    for col in [
        "Target MTD",
        "MTD Paid",
        "MTD Unpaid",
    ]:
        result[col] = pd.to_numeric(
            result[col],
            errors="coerce",
        ).fillna(0)

    result["% Achievement"] = (
        result["MTD Paid"]
        .div(result["Target MTD"])
        .replace(
            [
                float("inf"),
                -float("inf"),
            ],
            0,
        )
        .fillna(0)
        * 100
    )

    result["% Projection"] = (
        (
            result["MTD Paid"]
            + result["MTD Unpaid"]
        )
        .div(result["Target MTD"])
        .replace(
            [
                float("inf"),
                -float("inf"),
            ],
            0,
        )
        .fillna(0)
        * 100
    )

    return result


# ============================================================
# 13. CALCULATE TEAM LEADER MTD
# ============================================================

def calculate_team_leader_mtd(
    perf,
    target,
    company,
    end_date,
    selected_team_leader=None,
    selected_agent=None,
    selected_role=None,
    selected_tier=None,
):
    if not end_date:
        return pd.DataFrame()

    month_start = end_date.replace(day=1)

    target_month = filter_target(
        target,
        company,
        month_start,
        None,
        selected_team_leader,
        selected_agent,
        selected_role,
        selected_tier,
    )

    if target_month.empty:
        return pd.DataFrame()

    target_month["target_date"] = pd.to_datetime(
        target_month["target_date"],
        errors="coerce",
    ).dt.date

    month_end = (
        month_start
        + pd.offsets.MonthEnd(0)
    ).date()

    target_month = target_month[
        target_month["target_date"].notna()
        & (
            target_month["target_date"]
            >= month_start
        )
        & (
            target_month["target_date"]
            <= month_end
        )
    ].copy()

    target_month["daily_target"] = pd.to_numeric(
        target_month["daily_target"],
        errors="coerce",
    ).fillna(0)

    if "team_leader" not in target_month.columns:
        target_month["team_leader"] = "-"

    monthly_target = (
        target_month
        .groupby(
            "team_leader",
            dropna=False,
        )["daily_target"]
        .sum()
        .reset_index(name="Target Bulanan")
    )

    # --------------------------------------------------------
    # JUMLAH AGENT
    # --------------------------------------------------------

    if "agent" not in target_month.columns:
        target_month["agent"] = ""

    agent_count = (
        target_month
        .assign(
            agent_clean=(
                target_month["agent"]
                .astype("string")
                .str.strip()
            )
        )
        .query("agent_clean != ''")
        .groupby(
            "team_leader",
            dropna=False,
        )["agent_clean"]
        .nunique()
        .reset_index(name="Jumlah Agent")
    )

    # --------------------------------------------------------
    # TARGET MTD
    # --------------------------------------------------------

    target_mtd = filter_target(
        target,
        company,
        month_start,
        end_date,
        selected_team_leader,
        selected_agent,
        selected_role,
        selected_tier,
    )

    if target_mtd.empty:
        target_mtd_team = pd.DataFrame(
            columns=[
                "team_leader",
                "Target MTD",
            ]
        )

    else:
        target_mtd["daily_target"] = pd.to_numeric(
            target_mtd["daily_target"],
            errors="coerce",
        ).fillna(0)

        target_mtd_team = (
            target_mtd
            .groupby(
                "team_leader",
                dropna=False,
            )["daily_target"]
            .sum()
            .reset_index(name="Target MTD")
        )

    # --------------------------------------------------------
    # PERFORMANCE MTD
    # --------------------------------------------------------

    perf_mtd = filter_performance(
        perf,
        company,
        month_start,
        end_date,
        selected_team_leader,
        selected_agent,
        selected_role,
        selected_tier,
    )

    if perf_mtd.empty:
        performance_mtd = pd.DataFrame(
            columns=[
                "team_leader",
                "MTD Paid Team",
                "MTD Unpaid",
            ]
        )

    else:
        for col in [
            "paid",
            "unpaid",
        ]:
            if col not in perf_mtd.columns:
                perf_mtd[col] = 0

            perf_mtd[col] = pd.to_numeric(
                perf_mtd[col],
                errors="coerce",
            ).fillna(0)

        performance_mtd = (
            perf_mtd
            .groupby(
                "team_leader",
                dropna=False,
            )
            .agg(
                **{
                    "MTD Paid Team": (
                        "paid",
                        "sum",
                    ),
                    "MTD Unpaid": (
                        "unpaid",
                        "sum",
                    ),
                }
            )
            .reset_index()
        )

    # --------------------------------------------------------
    # MERGE
    # --------------------------------------------------------

    result = monthly_target.merge(
        agent_count,
        on="team_leader",
        how="left",
    )

    result = result.merge(
        target_mtd_team,
        on="team_leader",
        how="left",
    )

    result = result.merge(
        performance_mtd,
        on="team_leader",
        how="left",
    )

    numeric_cols = [
        "Target Bulanan",
        "Jumlah Agent",
        "Target MTD",
        "MTD Paid Team",
        "MTD Unpaid",
    ]

    for col in numeric_cols:
        result[col] = pd.to_numeric(
            result[col],
            errors="coerce",
        ).fillna(0)

    result["MTD Achievement"] = (
        result["MTD Paid Team"]
        .div(result["Target MTD"])
        .replace(
            [
                float("inf"),
                -float("inf"),
            ],
            0,
        )
        .fillna(0)
        * 100
    )

    result["MTD Projection"] = (
        (
            result["MTD Paid Team"]
            + result["MTD Unpaid"]
        )
        .div(result["Target MTD"])
        .replace(
            [
                float("inf"),
                -float("inf"),
            ],
            0,
        )
        .fillna(0)
        * 100
    )

    return result


# ============================================================
# 14. CALCULATE PERIOD ACHIEVEMENT
# ============================================================

def calculate_period_achievement(
    perf,
    target,
    company,
    end_date,
    selected_team_leader=None,
    selected_agent=None,
    selected_role=None,
    selected_tier=None,
):
    if not end_date:
        return {}

    team_leader = first_or_none(
        selected_team_leader
    )

    agent = first_or_none(
        selected_agent
    )

    role = first_or_none(
        selected_role
    )

    tier = first_or_none(
        selected_tier
    )

    # --------------------------------------------------------
    # DAILY
    # --------------------------------------------------------

    daily = call_dashboard_builder(
        build_range_performance,
        perf,
        target,
        end_date,
        end_date,
        company,
        team_leader,
        agent,
        role,
        tier,
    )

    # --------------------------------------------------------
    # WEEKLY
    # --------------------------------------------------------

    week_start = (
        end_date
        - timedelta(
            days=end_date.weekday()
        )
    )

    weekly = call_dashboard_builder(
        build_range_performance,
        perf,
        target,
        week_start,
        end_date,
        company,
        team_leader,
        agent,
        role,
        tier,
    )

    # --------------------------------------------------------
    # MONTHLY
    # --------------------------------------------------------

    month_start = end_date.replace(day=1)

    monthly = call_dashboard_builder(
        build_range_performance,
        perf,
        target,
        month_start,
        end_date,
        company,
        team_leader,
        agent,
        role,
        tier,
    )

    return {
        "daily": daily or {},
        "weekly": weekly or {},
        "monthly": monthly or {},
    }


# ============================================================
# 15. KPI SECTION
# ============================================================

def show_kpi_cards(
    paid,
    unpaid,
    achievement,
    projection,
    updated_at,
):
    with st.container(key="hg_kpi"):
        cols = st.columns(
            5,
            gap="small",
        )

        # ----------------------------------------------------
        # PAID
        # ----------------------------------------------------

        with cols[0]:
            st.metric(
                label="PAID",
                value=rupiah(paid),
                help="Total paid performance pada periode dan filter terpilih.",
            )

        # ----------------------------------------------------
        # UNPAID
        # ----------------------------------------------------

        with cols[1]:
            st.metric(
                label="UNPAID",
                value=rupiah(unpaid),
                help="Total unpaid performance pada periode dan filter terpilih.",
            )

        # ----------------------------------------------------
        # ACHIEVEMENT
        # ----------------------------------------------------

        with cols[2]:
            st.metric(
                label="ACHIEVEMENT",
                value=pct(achievement),
                help="Paid dibandingkan target.",
            )

        # ----------------------------------------------------
        # PROJECTION
        # ----------------------------------------------------

        with cols[3]:
            st.metric(
                label="PROJECTION",
                value=pct(projection),
                help="Paid + Unpaid dibandingkan target.",
            )

        # ----------------------------------------------------
        # LIVE
        # ----------------------------------------------------

        with cols[4]:
            st.metric(
                label="DATA STATUS",
                value="🟢 LIVE",
            )

            if updated_at:
                st.caption(
                    f"Last update: {updated_at}"
                )
            else:
                st.caption(
                    "Timestamp update belum tersedia."
                )


# ============================================================
# 16. AGENT RANKING TABLE
# ============================================================

def render_agent_ranking_table(df):
    if df is None or df.empty:
        st.info(
            "Belum ada data Agent Ranking untuk filter yang dipilih."
        )
        return

    display = df.copy()

    # --------------------------------------------------------
    # AGENT / ASSIGNMENT
    # --------------------------------------------------------

    if "agent" in display.columns:
        agent_name = display["agent"].map(
            clean_agent_name
        )
    else:
        agent_name = pd.Series(
            "-",
            index=display.index,
        )

    if "tier" in display.columns:
        tier_name = display["tier"].map(
            clean_agent_name
        )
    else:
        tier_name = pd.Series(
            "-",
            index=display.index,
        )

    if "role" in display.columns:
        role_name = display["role"].map(
            clean_agent_name
        )
    else:
        role_name = pd.Series(
            "-",
            index=display.index,
        )

    if "team_leader" in display.columns:
        team_leader_name = display[
            "team_leader"
        ].map(
            clean_agent_name
        )
    else:
        team_leader_name = pd.Series(
            "-",
            index=display.index,
        )

    display["Agent / Assignment"] = (
        agent_name
        + "\n"
        + tier_name
        + " · "
        + role_name
        + " · TL: "
        + team_leader_name
    )

    # --------------------------------------------------------
    # TARGET
    # --------------------------------------------------------

    if "target" in display.columns:
        display["Target"] = pd.to_numeric(
            display["target"],
            errors="coerce",
        ).fillna(0)

    elif "Target" not in display.columns:
        display["Target"] = 0

    # --------------------------------------------------------
    # INVOICE QUANTITY
    # --------------------------------------------------------

    if "Qty Invoice Paid" not in display.columns:
        display["Qty Invoice Paid"] = 0

    if "Qty Invoice Unpaid" not in display.columns:
        display["Qty Invoice Unpaid"] = 0

    display["Qty Invoice Paid"] = (
        pd.to_numeric(
            display["Qty Invoice Paid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    display["Qty Invoice Unpaid"] = (
        pd.to_numeric(
            display["Qty Invoice Unpaid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    # --------------------------------------------------------
    # ACHIEVEMENT / PROJECTION
    # --------------------------------------------------------

    if "achievement_pct" in display.columns:
        display["Achievement"] = pd.to_numeric(
            display["achievement_pct"],
            errors="coerce",
        ).fillna(0)

    else:
        display["Achievement"] = 0

    if "projection_pct" in display.columns:
        display["Projection"] = pd.to_numeric(
            display["projection_pct"],
            errors="coerce",
        ).fillna(0)

    else:
        display["Projection"] = 0

    # --------------------------------------------------------
    # ACHIEVEMENT CVR
    # CRM BELUM TERSEDIA
    # --------------------------------------------------------

    display["Achievement CVR"] = "—"

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    display = display.sort_values(
        "Achievement",
        ascending=False,
    )

    # --------------------------------------------------------
    # FINAL COLUMNS
    # --------------------------------------------------------

    final_columns = [
        "Agent / Assignment",
        "Target",
        "Qty Invoice Paid",
        "Qty Invoice Unpaid",
        "Achievement",
        "Projection",
        "Achievement CVR",
    ]

    display = display[
        [
            col
            for col in final_columns
            if col in display.columns
        ]
    ].copy()

    # --------------------------------------------------------
    # FORMAT FOR DISPLAY
    # --------------------------------------------------------

    display["Target"] = display[
        "Target"
    ].map(rupiah)

    display["Qty Invoice Paid"] = (
        display["Qty Invoice Paid"]
        .fillna(0)
        .astype(int)
    )

    display["Qty Invoice Unpaid"] = (
        display["Qty Invoice Unpaid"]
        .fillna(0)
        .astype(int)
    )

    # --------------------------------------------------------
    # SAVE NUMERIC ACHIEVEMENT
    # --------------------------------------------------------

    achievement_numeric = pd.to_numeric(
        display["Achievement"],
        errors="coerce",
    ).fillna(0)

    projection_numeric = pd.to_numeric(
        display["Projection"],
        errors="coerce",
    ).fillna(0)

    display["Achievement"] = achievement_numeric.map(
        pct
    )

    display["Projection"] = projection_numeric.map(
        pct
    )

    # --------------------------------------------------------
    # HIGHLIGHT < 80%
    # --------------------------------------------------------

    def highlight_achievement(value):
        try:
            numeric = float(
                str(value)
                .replace("%", "")
                .replace(",", ".")
            )
        except Exception:
            numeric = 0

        if numeric < 80:
            return "⚠️ " + str(value)

        return str(value)

    display["Achievement"] = display[
        "Achievement"
    ].map(
        highlight_achievement
    )

    with st.container(key="hg_agent_ranking"):
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# 17. MTD TEAM LEADER
# ============================================================

def render_team_leader_cards(
    team_mtd,
    period_data,
):
    if team_mtd is None or team_mtd.empty:
        st.info(
            "Belum ada data MTD Team Leader untuk filter yang dipilih."
        )
        return

    # --------------------------------------------------------
    # CARD PER TEAM LEADER
    # --------------------------------------------------------

    for start in range(
        0,
        len(team_mtd),
        2,
    ):
        cols = st.columns(2)

        for col_idx in range(2):
            idx = start + col_idx

            if idx >= len(team_mtd):
                break

            row = team_mtd.iloc[idx]

            team_leader = clean_agent_name(
                row.get(
                    "team_leader",
                    "-",
                )
            )

            with cols[col_idx]:
                with st.container(
                    border=True
                ):
                    st.subheader(
                        f"👥 {team_leader}"
                    )

                    st.caption(
                        "MTD Team Performance"
                    )

                    # ------------------------------------------------
                    # TOP KPI
                    # ------------------------------------------------

                    top1, top2 = st.columns(2)

                    with top1:
                        st.metric(
                            "Jumlah Agent",
                            number(
                                row.get(
                                    "Jumlah Agent",
                                    0,
                                )
                            ),
                        )

                    with top2:
                        st.metric(
                            "Target Bulanan",
                            rupiah(
                                row.get(
                                    "Target Bulanan",
                                    0,
                                )
                            ),
                        )

                    st.divider()

                    # ------------------------------------------------
                    # PERFORMANCE
                    # ------------------------------------------------

                    k1, k2 = st.columns(2)

                    with k1:
                        st.metric(
                            "MTD Paid",
                            rupiah(
                                row.get(
                                    "MTD Paid Team",
                                    0,
                                )
                            ),
                        )

                    with k2:
                        st.metric(
                            "MTD Unpaid",
                            rupiah(
                                row.get(
                                    "MTD Unpaid",
                                    0,
                                )
                            ),
                        )

                    k3, k4 = st.columns(2)

                    achievement = safe_float(
                        row.get(
                            "MTD Achievement",
                            0,
                        )
                    )

                    projection = safe_float(
                        row.get(
                            "MTD Projection",
                            0,
                        )
                    )

                    with k3:
                        st.metric(
                            "Achievement",
                            pct(achievement),
                        )

                    with k4:
                        st.metric(
                            "Projection",
                            pct(projection),
                        )

                    # ------------------------------------------------
                    # PERIOD ACHIEVEMENT
                    # ------------------------------------------------

                    if period_data:
                        st.divider()

                        st.caption(
                            "Period Achievement"
                        )

                        daily = period_data.get(
                            "daily",
                            {},
                        )

                        weekly = period_data.get(
                            "weekly",
                            {},
                        )

                        monthly = period_data.get(
                            "monthly",
                            {},
                        )

                        p1, p2, p3 = st.columns(3)

                        with p1:
                            st.metric(
                                "Hari",
                                pct(
                                    daily.get(
                                        "achievement_pct",
                                        0,
                                    )
                                ),
                            )

                        with p2:
                            st.metric(
                                "Minggu",
                                pct(
                                    weekly.get(
                                        "achievement_pct",
                                        0,
                                    )
                                ),
                            )

                        with p3:
                            st.metric(
                                "MTD",
                                pct(
                                    monthly.get(
                                        "achievement_pct",
                                        0,
                                    )
                                ),
                            )


# ============================================================
# 18. MTD AGENT TABLE
# ============================================================

def render_mtd_agent_table(df):
    if df is None or df.empty:
        st.info(
            "Belum ada data MTD Agent untuk filter yang dipilih."
        )
        return

    display = df.copy()

    # --------------------------------------------------------
    # AGENT
    # --------------------------------------------------------

    if "agent" in display.columns:
        display["Agent"] = (
            display["agent"]
            .map(clean_agent_name)
        )
    else:
        display["Agent"] = "-"

    # --------------------------------------------------------
    # TEAM LEADER
    # --------------------------------------------------------

    if "team_leader" in display.columns:
        display["Team Leader"] = (
            display["team_leader"]
            .map(clean_agent_name)
        )
    else:
        display["Team Leader"] = "-"

    # --------------------------------------------------------
    # NUMERIC
    # --------------------------------------------------------

    numeric_columns = [
        "Target Periode",
        "Target Bulanan",
        "MTD Paid",
        "MTD Unpaid",
        "% Achievement",
        "% Projection",
    ]

    for col in numeric_columns:
        if col not in display.columns:
            display[col] = 0

        display[col] = pd.to_numeric(
            display[col],
            errors="coerce",
        ).fillna(0)

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    display = display.sort_values(
        "% Achievement",
        ascending=False,
    )

    # --------------------------------------------------------
    # FORMAT
    # --------------------------------------------------------

    display["Target Periode"] = display[
        "Target Periode"
    ].map(rupiah)

    display["Target Bulanan"] = display[
        "Target Bulanan"
    ].map(rupiah)

    display["MTD Paid"] = display[
        "MTD Paid"
    ].map(rupiah)

    display["MTD Unpaid"] = display[
        "MTD Unpaid"
    ].map(rupiah)

    achievement_numeric = pd.to_numeric(
        df["% Achievement"],
        errors="coerce",
    ).fillna(0)

    projection_numeric = pd.to_numeric(
        df["% Projection"],
        errors="coerce",
    ).fillna(0)

    display["% Achievement"] = achievement_numeric.map(
        pct
    )

    display["% Projection"] = projection_numeric.map(
        pct
    )

    # --------------------------------------------------------
    # FINAL COLUMNS
    # --------------------------------------------------------

    final_columns = [
        "Agent",
        "Team Leader",
        "Target Periode",
        "Target Bulanan",
        "MTD Paid",
        "MTD Unpaid",
        "% Achievement",
        "% Projection",
    ]

    display = display[
        [
            col
            for col in final_columns
            if col in display.columns
        ]
    ]

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# 19. HEADER
# ============================================================

header_col1, header_col2 = st.columns(
    [5, 1]
)

with header_col1:
    st.caption(
        "SALES PERFORMANCE MONITORING"
    )

    st.title(
        "🥗 Healthy Go Performance Dashboard"
    )

    st.write(
        "Monitoring sales performance, agent productivity, "
        "achievement, projection, dan MTD performance."
    )

with header_col2:
    if st.button(
        "← Dashboard",
        use_container_width=True,
    ):
        st.switch_page("app.py")


# ============================================================
# 20. LOAD DATA
# ============================================================

try:
    perf, target = load_data()

except Exception as exc:
    st.error(
        f"Gagal mengambil data dashboard: {exc}"
    )
    st.stop()


# ============================================================
# 21. BASIC DATA VALIDATION
# ============================================================

if perf is None or perf.empty:
    st.warning(
        "Performance Fact masih kosong."
    )
    st.stop()

if target is None or target.empty:
    st.warning(
        "Target Fact masih kosong."
    )
    st.stop()


if "company" not in perf.columns:
    st.error(
        "Kolom `company` tidak ditemukan pada Performance Fact."
    )
    st.stop()


# ============================================================
# 22. NORMALISASI DATA
# ============================================================

if "performance_date" in perf.columns:
    perf["performance_date"] = pd.to_datetime(
        perf["performance_date"],
        errors="coerce",
    ).dt.date

if "target_date" in target.columns:
    target["target_date"] = pd.to_datetime(
        target["target_date"],
        errors="coerce",
    ).dt.date

if "daily_target" not in target.columns:
    st.error(
        "Kolom `daily_target` tidak ditemukan pada Target Fact."
    )
    st.stop()


# ============================================================
# 23. COMPANY
# ============================================================

company = "HG"


# ============================================================
# 24. FILTER
# ============================================================

st.subheader(
    "🎛️ Dashboard Filter"
)

st.caption(
    "Gunakan filter berikut untuk mengubah seluruh "
    "performance dashboard Healthy Go."
)


# ============================================================
# 25. REFRESH / RESET
# ============================================================

action_col1, action_col2, action_col3 = st.columns(
    [1.2, 1.2, 4]
)

with action_col1:
    refresh_clicked = st.button(
        "🔄 Refresh Data",
        use_container_width=True,
    )

with action_col2:
    reset_clicked = st.button(
        "↩️ Reset Filter",
        use_container_width=True,
    )


if refresh_clicked:
    clear_dashboard_cache()
    st.cache_data.clear()
    st.rerun()


if reset_clicked:
    for key in [
        "hg_period_mode",
        "hg_selected_date",
        "hg_date_range",
        "hg_team_leader",
        "hg_agent",
        "hg_role",
        "hg_tier",
    ]:
        st.session_state.pop(
            key,
            None,
        )

    st.rerun()


# ============================================================
# 26. AVAILABLE DATES
# ============================================================

available_dates = sorted(
    [
        x
        for x in perf["performance_date"]
        .dropna()
        .unique()
    ]
)

if not available_dates:
    st.error(
        "Tidak ada tanggal performance."
    )
    st.stop()

latest_date = max(
    available_dates
)


# ============================================================
# 27. FILTER PERIODE
# ============================================================

filter_col1, filter_col2 = st.columns(
    [1, 2]
)

with filter_col1:
    period_mode = st.radio(
        "Periode",
        [
            "Daily",
            "Range",
        ],
        horizontal=True,
        key="hg_period_mode",
    )


with filter_col2:
    if period_mode == "Daily":

        selected_date = st.date_input(
            "Tanggal",
            value=latest_date,
            min_value=min(available_dates),
            max_value=max(available_dates),
            key="hg_selected_date",
        )

        start_date = selected_date
        end_date = selected_date

    else:

        default_start = max(
            min(available_dates),
            latest_date.replace(day=1),
        )

        date_range = st.date_input(
            "Range Tanggal",
            value=(
                default_start,
                latest_date,
            ),
            min_value=min(available_dates),
            max_value=max(available_dates),
            key="hg_date_range",
        )

        if (
            isinstance(
                date_range,
                (tuple, list),
            )
            and len(date_range) == 2
        ):
            start_date = date_range[0]
            end_date = date_range[1]

        else:
            start_date = latest_date
            end_date = latest_date


# ============================================================
# 28. FILTER DIMENSIONS
# ============================================================

def get_filter_values(df, column):
    if column not in df.columns:
        return []

    return sorted(
        [
            x
            for x in df[column]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            if x
        ]
    )


tl_values = get_filter_values(
    perf,
    "team_leader",
)

agent_values = get_filter_values(
    perf,
    "agent",
)

role_values = get_filter_values(
    perf,
    "role",
)

tier_values = get_filter_values(
    perf,
    "tier",
)


filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)


with filter_col1:
    selected_team_leader = st.multiselect(
        "Team Leader",
        options=tl_values,
        default=[],
        key="hg_team_leader",
    )


with filter_col2:
    selected_agent = st.multiselect(
        "Agent",
        options=agent_values,
        default=[],
        key="hg_agent",
    )


with filter_col3:
    selected_role = st.multiselect(
        "Role",
        options=role_values,
        default=[],
        key="hg_role",
    )


with filter_col4:
    selected_tier = st.multiselect(
        "Tier",
        options=tier_values,
        default=[],
        key="hg_tier",
    )


st.divider()


# ============================================================
# 29. CURRENT FILTER VALUES
# ============================================================

filter_agent = first_or_none(
    selected_agent
)

filter_role = first_or_none(
    selected_role
)

filter_team_leader = first_or_none(
    selected_team_leader
)

filter_tier = first_or_none(
    selected_tier
)


# ============================================================
# 30. DAILY RANGE PERFORMANCE
# ============================================================

st.subheader(
    "📊 Daily Range Performance"
)

st.caption(
    "Ringkasan performa berdasarkan periode dan filter yang dipilih."
)


try:
    range_result = call_dashboard_builder(
        build_range_performance,
        perf,
        target,
        start_date,
        end_date,
        company,
        filter_team_leader,
        filter_agent,
        filter_role,
        filter_tier,
    )

except Exception as exc:
    st.error(
        f"Gagal menghitung Daily Range Performance: {exc}"
    )
    range_result = {}


if not range_result:
    range_result = {}


paid_value = safe_float(
    range_result.get(
        "paid",
        0,
    )
)

unpaid_value = safe_float(
    range_result.get(
        "unpaid",
        0,
    )
)

achievement_value = safe_float(
    range_result.get(
        "achievement_pct",
        0,
    )
)

projection_value = safe_float(
    range_result.get(
        "projection_pct",
        0,
    )
)


# ============================================================
# 31. SOURCE UPDATE
# ============================================================

filtered_for_update = filter_performance(
    perf,
    company,
    start_date,
    end_date,
    selected_team_leader,
    selected_agent,
    selected_role,
    selected_tier,
)


updated_at = None


if (
    not filtered_for_update.empty
    and "source_updated_at_display"
    in filtered_for_update.columns
):
    values = (
        filtered_for_update[
            "source_updated_at_display"
        ]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        values.ne("")
    ]

    if not values.empty:
        updated_at = values.iloc[-1]


# ============================================================
# 32. KPI
# ============================================================

show_kpi_cards(
    paid=paid_value,
    unpaid=unpaid_value,
    achievement=achievement_value,
    projection=projection_value,
    updated_at=updated_at,
)


# ============================================================
# 33. DAILY PERFORMANCE
# ============================================================

st.subheader(
    "📅 Daily Performance"
)


try:
    daily_result = call_dashboard_builder(
        build_daily_performance,
        perf,
        target,
        start_date,
        end_date,
        company,
        filter_team_leader,
        filter_agent,
        filter_role,
        filter_tier,
    )

except Exception as exc:
    st.error(
        f"Gagal mengambil Daily Performance: {exc}"
    )
    daily_result = []


# ------------------------------------------------------------
# NORMALIZE DAILY RESULT
# ------------------------------------------------------------

if isinstance(
    daily_result,
    pd.DataFrame,
):
    daily_df = daily_result.copy()

elif isinstance(
    daily_result,
    list,
):
    daily_df = pd.DataFrame(
        daily_result
    )

elif isinstance(
    daily_result,
    dict,
):
    daily_df = pd.DataFrame(
        [daily_result]
    )

else:
    daily_df = pd.DataFrame()


# ------------------------------------------------------------
# DISPLAY DAILY
# ------------------------------------------------------------

if not daily_df.empty:

    display_daily = daily_df.copy()

    rename_map = {
        "performance_date": "Date",
        "date": "Date",
        "target": "Target",
        "paid": "Paid",
        "unpaid": "Unpaid",
        "paid_invoice_revenue": "Paid Invoice Revenue",
        "unpaid_invoice_revenue": "Unpaid Invoice Revenue",
        "achievement_pct": "Achievement",
        "projection_pct": "Projection",
    }

    display_daily = display_daily.rename(
        columns=rename_map
    )

    wanted = [
        "Date",
        "Target",
        "Paid",
        "Unpaid",
        "Paid Invoice Revenue",
        "Unpaid Invoice Revenue",
        "Achievement",
        "Projection",
    ]

    existing = [
        col
        for col in wanted
        if col in display_daily.columns
    ]

    display_daily = display_daily[
        existing
    ].copy()

    for col in [
        "Target",
        "Paid",
        "Unpaid",
        "Paid Invoice Revenue",
        "Unpaid Invoice Revenue",
    ]:
        if col in display_daily.columns:
            display_daily[col] = (
                pd.to_numeric(
                    display_daily[col],
                    errors="coerce",
                )
                .fillna(0)
                .map(rupiah)
            )

    for col in [
        "Achievement",
        "Projection",
    ]:
        if col in display_daily.columns:
            display_daily[col] = (
                pd.to_numeric(
                    display_daily[col],
                    errors="coerce",
                )
                .fillna(0)
                .map(pct)
            )

    st.dataframe(
        display_daily,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info(
        "Belum ada data Daily Performance."
    )


# ============================================================
# 34. AGENT RANKING
# ============================================================

st.subheader(
    "🏆 Agent Ranking"
)

st.caption(
    "Ranking agent berdasarkan performa pada periode yang dipilih. "
    "Achievement di bawah 80% ditandai sebagai perlu perhatian."
)


try:
    ranking = call_dashboard_builder(
        build_agent_ranking,
        perf,
        target,
        start_date,
        end_date,
        company,
        filter_team_leader,
        filter_agent,
        filter_role,
        filter_tier,
    )

except Exception as exc:
    st.error(
        f"Gagal mengambil Agent Ranking: {exc}"
    )
    ranking = pd.DataFrame()


# ------------------------------------------------------------
# NORMALIZE RANKING
# ------------------------------------------------------------

if isinstance(
    ranking,
    pd.DataFrame,
):
    ranking_df = ranking.copy()

elif isinstance(
    ranking,
    list,
):
    ranking_df = pd.DataFrame(
        ranking
    )

elif isinstance(
    ranking,
    dict,
):
    ranking_df = pd.DataFrame(
        [ranking]
    )

else:
    ranking_df = pd.DataFrame()


# ------------------------------------------------------------
# MERGE INVOICE QUANTITY
# ------------------------------------------------------------

if not ranking_df.empty:

    for col in [
        "company",
        "agent",
        "role",
        "team_leader",
        "tier",
    ]:
        if col not in ranking_df.columns:
            ranking_df[col] = ""

    perf_for_qty = filter_performance(
        perf,
        company,
        start_date,
        end_date,
        selected_team_leader,
        selected_agent,
        selected_role,
        selected_tier,
    )

    ranking_df = merge_invoice_quantity(
        ranking_df,
        perf_for_qty,
    )

    for col in [
        "target",
        "Target",
        "paid_invoice_revenue",
        "unpaid_invoice_revenue",
        "achievement_pct",
        "projection_pct",
    ]:
        if col in ranking_df.columns:
            ranking_df[col] = pd.to_numeric(
                ranking_df[col],
                errors="coerce",
            ).fillna(0)

    if "achievement_pct" in ranking_df.columns:
        ranking_df = ranking_df.sort_values(
            "achievement_pct",
            ascending=False,
        )

    render_agent_ranking_table(
        ranking_df
    )

else:
    st.info(
        "Belum ada data Agent Ranking untuk filter yang dipilih."
    )


# ============================================================
# 35. MTD PERFORMANCE — TEAM LEADER
# ============================================================

st.subheader(
    "👥 MTD Performance — Team Leader"
)

st.caption(
    "Ringkasan performa Team Leader dari awal bulan "
    "sampai tanggal yang dipilih."
)


try:
    team_mtd = calculate_team_leader_mtd(
        perf=perf,
        target=target,
        company=company,
        end_date=end_date,
        selected_team_leader=selected_team_leader,
        selected_agent=selected_agent,
        selected_role=selected_role,
        selected_tier=selected_tier,
    )

except Exception as exc:
    st.error(
        f"Gagal menghitung MTD Team Leader: {exc}"
    )
    team_mtd = pd.DataFrame()


# ============================================================
# 36. PERIOD ACHIEVEMENT
# ============================================================

try:
    period_data = calculate_period_achievement(
        perf=perf,
        target=target,
        company=company,
        end_date=end_date,
        selected_team_leader=selected_team_leader,
        selected_agent=selected_agent,
        selected_role=selected_role,
        selected_tier=selected_tier,
    )

except Exception as exc:
    st.warning(
        f"Period achievement belum dapat dihitung: {exc}"
    )
    period_data = {}


render_team_leader_cards(
    team_mtd=team_mtd,
    period_data=period_data,
)


# ============================================================
# 37. MTD PERFORMANCE — AGENT
# ============================================================

st.subheader(
    "👤 MTD Performance — Agent"
)

st.caption(
    "Performa agent dari awal bulan sampai tanggal yang dipilih."
)


try:
    agent_mtd = calculate_agent_mtd(
        perf=perf,
        target=target,
        company=company,
        start_date=start_date,
        end_date=end_date,
        selected_team_leader=selected_team_leader,
        selected_agent=selected_agent,
        selected_role=selected_role,
        selected_tier=selected_tier,
    )

except Exception as exc:
    st.error(
        f"Gagal menghitung MTD Agent: {exc}"
    )
    agent_mtd = pd.DataFrame()


if not agent_mtd.empty:

    if "% Achievement" in agent_mtd.columns:
        agent_mtd = agent_mtd.sort_values(
            "% Achievement",
            ascending=False,
        )

    render_mtd_agent_table(
        agent_mtd
    )

else:
    st.info(
        "Belum ada data MTD Agent untuk filter yang dipilih."
    )


# ============================================================
# 38. LIVE DATA STATUS
# ============================================================

st.subheader(
    "🟢 Live Data Status"
)

if updated_at:
    st.success(
        f"🟢 LIVE · Updated {updated_at}"
    )

else:
    st.warning(
        "Source update timestamp belum tersedia."
    )


# ============================================================
# 39. FOOTER NAVIGATION
# ============================================================

st.divider()

if st.button(
    "← Kembali ke Dashboard Utama",
    use_container_width=True,
):
    st.switch_page("app.py")
