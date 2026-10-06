import pandas as pd

from functools import lru_cache

from build_achievement_fact import build_performance, build_targets


# =========================================================
# CONFIG
# =========================================================

COMPANY_MAP = {
    "Healthy Go": "HG",
    "Bekelin": "BK",
}

VALID_COMPANIES = ["HG", "BK"]


# =========================================================
# HELPER
# =========================================================

def normalize_text(series):
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )


def normalize_date(series):
    return pd.to_datetime(
        series,
        errors="coerce",
    ).dt.normalize()


def to_bool(series):
    """
    Normalisasi boolean dari Google Sheets / pandas.
    """

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    result = numeric.eq(1)

    text = (
        series.astype("string")
        .str.strip()
        .str.casefold()
    )

    result = result | text.isin(
        [
            "true",
            "yes",
            "y",
            "ya",
            "paid",
            "success",
            "successful",
            "sukses",
        ]
    )

    return result.fillna(False)


def clean_invoice_series(series):
    """
    Bersihkan invoice_no.
    Invoice kosong tidak dihitung.
    """

    invoice = (
        series.astype("string")
        .str.strip()
    )

    invalid = {
        "",
        "nan",
        "none",
        "null",
        "nat",
        "<na>",
    }

    invoice = invoice.mask(
        invoice.str.casefold().isin(invalid)
    )

    return invoice


def get_company_key(company):
    return (
        COMPANY_MAP.get(
            company,
            company,
        )
        .strip()
        .casefold()
    )


def safe_pct(numerator, denominator):
    return (
        numerator
        / denominator
        * 100
    ).where(
        denominator > 0,
        0,
    )


# =========================================================
# PREPARE PERFORMANCE
# =========================================================

def prepare_performance(performance):

    required_columns = [
        "agent_key",
        "Nama Agent",
        "Company",
        "Role",
        "Nama Team Leader",
        "Tier",
        "performance_date",
        "status_live",
        "performance_amount",
        "invoice_revenue",
        "paid_invoice_revenue",
        "unpaid_invoice_revenue",
    ]

    missing = [
        col
        for col in required_columns
        if col not in performance.columns
    ]

    if missing:
        raise ValueError(
            "Kolom Performance Fact belum lengkap: "
            + ", ".join(missing)
        )

    df = performance.copy()

    # =====================================================
    # COMPANY
    # =====================================================

    df["company"] = (
        df["Company"]
        .astype("string")
        .str.strip()
        .map(COMPANY_MAP)
        .fillna(
            df["Company"]
            .astype("string")
            .str.strip()
        )
    )

    df["company"] = normalize_text(
        df["company"]
    )

    # =====================================================
    # AGENT KEY
    # =====================================================

    df["agent_key"] = normalize_text(
        df["agent_key"]
    )

    # =====================================================
    # ORIGINAL PERFORMANCE DIMENSIONS
    # =====================================================

    df["agent"] = normalize_text(
        df["Nama Agent"]
    )

    df["role"] = normalize_text(
        df["Role"]
    )

    df["team_leader"] = normalize_text(
        df["Nama Team Leader"]
    )

    df["tier"] = normalize_text(
        df["Tier"]
    )

    # =====================================================
    # INVOICE
    # =====================================================

    if "invoice_no" in df.columns:
        df["invoice_no"] = clean_invoice_series(
            df["invoice_no"]
        )
    else:
        df["invoice_no"] = pd.Series(
            pd.NA,
            index=df.index,
            dtype="string",
        )

    # =====================================================
    # STATUS LIVE
    # =====================================================

    df["status_live"] = (
        df["status_live"]
        .astype("string")
        .str.strip()
        .str.casefold()
    )

    # =====================================================
    # BOOLEAN FLAGS
    # =====================================================

    if "is_paid" in df.columns:
        df["is_paid"] = to_bool(
            df["is_paid"]
        )
    else:
        df["is_paid"] = (
            df["status_live"]
            .str.contains(
                r"paid|success|sukses",
                regex=True,
                na=False,
            )
        )

    if "is_unpaid" in df.columns:
        df["is_unpaid"] = to_bool(
            df["is_unpaid"]
        )
    else:
        df["is_unpaid"] = (
            df["status_live"]
            .str.contains(
                r"unpaid|pending|challenge",
                regex=True,
                na=False,
            )
        )

    if "is_excluded" in df.columns:
        df["is_excluded"] = to_bool(
            df["is_excluded"]
        )
    else:
        df["is_excluded"] = False

    # =====================================================
    # ONLY 3 DASHBOARD STATUS
    #
    # PAID
    # PENDING / UNPAID
    # CHALLENGE / UNPAID
    #
    # CANCEL / EXCLUDED TIDAK MASUK
    # =====================================================

    df["valid_paid"] = (
        df["is_paid"]
        & ~df["is_excluded"]
    )

    df["valid_unpaid"] = (
        df["is_unpaid"]
        & ~df["is_excluded"]
        & ~df["is_paid"]
    )

    # =====================================================
    # DATE LOGIC
    #
    # PAID     -> PAYMENT DATE
    # UNPAID   -> INVOICE DATE
    # =====================================================

    if "payment_date" in df.columns:
        df["payment_date_clean"] = normalize_date(
            df["payment_date"]
        )
    else:
        df["payment_date_clean"] = pd.NaT

    if "tanggal" in df.columns:
        df["invoice_date_clean"] = normalize_date(
            df["tanggal"]
        )
    else:
        df["invoice_date_clean"] = pd.NaT

    df["dashboard_date"] = df[
        "invoice_date_clean"
    ]

    df.loc[
        df["valid_paid"],
        "dashboard_date",
    ] = df.loc[
        df["valid_paid"],
        "payment_date_clean",
    ]

    df["performance_date"] = df[
        "dashboard_date"
    ]

    # =====================================================
    # NUMERIC
    # =====================================================

    numeric_columns = [
        "performance_amount",
        "invoice_revenue",
        "paid_invoice_revenue",
        "unpaid_invoice_revenue",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        ).fillna(0)

    # =====================================================
    # PERFORMANCE AMOUNT
    # =====================================================

    df["paid"] = df[
        "performance_amount"
    ].where(
        df["valid_paid"],
        0,
    )

    df["unpaid"] = df[
        "performance_amount"
    ].where(
        df["valid_unpaid"],
        0,
    )

    # =====================================================
    # REVENUE STATUS
    # =====================================================

    df["paid_invoice_revenue"] = df[
        "paid_invoice_revenue"
    ].where(
        df["valid_paid"],
        0,
    )

    df["unpaid_invoice_revenue"] = df[
        "unpaid_invoice_revenue"
    ].where(
        df["valid_unpaid"],
        0,
    )

    # =====================================================
    # AGENT DISPLAY
    # =====================================================

    df["agent_display"] = (
        df["Nama Agent"]
        .fillna("-")
        .astype("string")
    )

    return df


# =========================================================
# PREPARE TARGET
# =========================================================

def prepare_target(target):

    required_columns = [
        "company",
        "agent",
        "role",
        "team_leader",
        "tier",
        "target_date",
        "daily_target",
    ]

    missing = [
        col
        for col in required_columns
        if col not in target.columns
    ]

    if missing:
        raise ValueError(
            "Kolom Target belum lengkap: "
            + ", ".join(missing)
        )

    df = target.copy()

    # =====================================================
    # COMPANY
    # =====================================================

    df["company"] = (
        df["company"]
        .astype("string")
        .str.strip()
        .map(COMPANY_MAP)
        .fillna(
            df["company"]
            .astype("string")
            .str.strip()
        )
    )

    df["company"] = normalize_text(
        df["company"]
    )

    # =====================================================
    # AGENT MASTER
    # =====================================================

    df["agent"] = (
        df["agent"]
        .astype("string")
        .str.strip()
    )

    df["agent_key"] = normalize_text(
        df["agent"]
    )

    df["role"] = normalize_text(
        df["role"]
    )

    df["team_leader"] = normalize_text(
        df["team_leader"]
    )

    df["tier"] = normalize_text(
        df["tier"]
    )

    # =====================================================
    # TARGET DATE
    # =====================================================

    df["target_date"] = normalize_date(
        df["target_date"]
    )

    # =====================================================
    # TARGET VALUE
    # =====================================================

    df["daily_target"] = pd.to_numeric(
        df["daily_target"],
        errors="coerce",
    ).fillna(0)

    return df


# =========================================================
# COMMON FILTER
# =========================================================

def apply_common_filters(
    df,
    team_leader=None,
    agent=None,
    role=None,
    tier=None,
):

    result = df.copy()

    if (
        team_leader
        and team_leader != "All"
    ):
        value = normalize_text(
            pd.Series([team_leader])
        ).iloc[0]

        result = result[
            result["team_leader"] == value
        ]

    if agent and agent != "All":
        value = normalize_text(
            pd.Series([agent])
        ).iloc[0]

        result = result[
            result["agent"] == value
        ]

    if role and role != "All":
        value = normalize_text(
            pd.Series([role])
        ).iloc[0]

        result = result[
            result["role"] == value
        ]

    if tier and tier != "All":
        value = normalize_text(
            pd.Series([tier])
        ).iloc[0]

        result = result[
            result["tier"] == value
        ]

    return result


# =========================================================
# BUILD DASHBOARD DATA
# =========================================================

@lru_cache(maxsize=1)
def build_dashboard_performance():

    performance_raw = build_performance()
    target_raw = build_targets()

    performance = prepare_performance(
        performance_raw
    )

    target = prepare_target(
        target_raw
    )

    # =====================================================
    # TARGET AGENT = MASTER UTAMA
    # =====================================================

    agent_master = (
        target[
            [
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
            ]
        ]
        .drop_duplicates(
            subset=[
                "company",
                "agent_key",
            ]
        )
        .copy()
    )

    # =====================================================
    # PERFORMANCE COMPANY
    # =====================================================

    performance = performance[
        performance["company"].isin(
            ["hg", "bk"]
        )
    ].copy()

    # =====================================================
    # MERGE KE TARGET AGENT
    #
    # Semua dimensi dashboard berasal
    # dari TARGET AGENT.
    # =====================================================

    performance = performance.merge(
        agent_master,
        on=[
            "company",
            "agent_key",
        ],
        how="inner",
        suffixes=(
            "_transaction",
            "",
        ),
        validate="many_to_one",
    )

    # =====================================================
    # SAFETY NUMERIC
    # =====================================================

    numeric_columns = [
        "paid",
        "unpaid",
        "performance_amount",
        "invoice_revenue",
        "paid_invoice_revenue",
        "unpaid_invoice_revenue",
    ]

    for col in numeric_columns:
        if col in performance.columns:
            performance[col] = pd.to_numeric(
                performance[col],
                errors="coerce",
            ).fillna(0)

    # =====================================================
    # MASTER AGENT DISPLAY
    # =====================================================

    performance["agent_display"] = (
        performance["agent"]
        .fillna("-")
        .astype("string")
    )

    return performance, target


# =========================================================
# CACHE
# =========================================================

def clear_dashboard_cache():
    build_dashboard_performance.cache_clear()


# =========================================================
# INVOICE STATE
# =========================================================

def build_invoice_state(perf):
    """
    Membuat satu record final untuk setiap invoice.

    Aturan:
    - Cancel / excluded tidak masuk.
    - Paid menang atas Unpaid.
    - Invoice yang sama tidak dihitung berkali-kali.
    """

    required = [
        "company",
        "agent_key",
        "agent",
        "role",
        "team_leader",
        "tier",
        "invoice_no",
        "is_paid",
        "is_unpaid",
        "is_excluded",
    ]

    missing = [
        col
        for col in required
        if col not in perf.columns
    ]

    if missing:
        return pd.DataFrame(
            columns=[
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
                "invoice_no",
                "is_paid",
                "is_unpaid",
            ]
        )

    invoice_df = perf.copy()

    invoice_df["invoice_no"] = clean_invoice_series(
        invoice_df["invoice_no"]
    )

    # Excluded / cancel tidak masuk.
    invoice_df = invoice_df[
        invoice_df["invoice_no"].notna()
        & ~invoice_df["is_excluded"]
    ].copy()

    if invoice_df.empty:
        return pd.DataFrame(
            columns=[
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
                "invoice_no",
                "is_paid",
                "is_unpaid",
            ]
        )

    # =====================================================
    # ONE INVOICE = ONE STATE
    # =====================================================

    invoice_state = (
        invoice_df
        .groupby(
            [
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
                "invoice_no",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            is_paid=(
                "is_paid",
                "max",
            ),
            is_unpaid=(
                "is_unpaid",
                "max",
            ),
        )
    )

    # =====================================================
    # PAID PRECEDENCE
    # =====================================================

    invoice_state["is_unpaid"] = (
        invoice_state["is_unpaid"]
        & ~invoice_state["is_paid"]
    )

    return invoice_state


# =========================================================
# BUILD INVOICE QTY
# =========================================================

def build_invoice_quantity(perf):

    invoice_state = build_invoice_state(
        perf
    )

    if invoice_state.empty:
        return pd.DataFrame(
            columns=[
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
                "Qty Invoice Paid",
                "Qty Invoice Unpaid",
            ]
        )

    result = (
        invoice_state
        .groupby(
            [
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
            ],
            dropna=False,
            as_index=False,
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
    )

    result["Qty Invoice Paid"] = (
        pd.to_numeric(
            result["Qty Invoice Paid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    result["Qty Invoice Unpaid"] = (
        pd.to_numeric(
            result["Qty Invoice Unpaid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    return result


# =========================================================
# ACHIEVEMENT CVR
# =========================================================

def calculate_cvr(
    qty_paid,
    qty_unpaid,
):
    total_invoice = (
        qty_paid
        + qty_unpaid
    )

    return (
        qty_paid
        / total_invoice
        * 100
        if total_invoice > 0
        else 0
    )


# =========================================================
# DAILY PERFORMANCE
# =========================================================

def build_daily_performance(
    start_date,
    end_date,
    company,
    team_leader=None,
    agent=None,
    role=None,
    tier=None,
):

    perf, target = build_dashboard_performance()

    company_key = get_company_key(
        company
    )

    start_date = pd.Timestamp(
        start_date
    ).normalize()

    end_date = pd.Timestamp(
        end_date
    ).normalize()

    # =====================================================
    # FILTER PERFORMANCE
    # =====================================================

    perf = perf[
        (
            perf["company"]
            == company_key
        )
        & (
            perf["performance_date"]
            >= start_date
        )
        & (
            perf["performance_date"]
            <= end_date
        )
    ].copy()

    # =====================================================
    # FILTER TARGET
    # =====================================================

    target = target[
        (
            target["company"]
            == company_key
        )
        & (
            target["target_date"]
            >= start_date
        )
        & (
            target["target_date"]
            <= end_date
        )
    ].copy()

    perf = apply_common_filters(
        perf,
        team_leader,
        agent,
        role,
        tier,
    )

    target = apply_common_filters(
        target,
        team_leader,
        agent,
        role,
        tier,
    )

    # =====================================================
    # TARGET DAILY
    # =====================================================

    daily_target = (
        target
        .groupby(
            "target_date",
            as_index=False,
        )["daily_target"]
        .sum()
        .rename(
            columns={
                "target_date": "date",
                "daily_target": "target",
            }
        )
    )

    # =====================================================
    # PERFORMANCE DAILY
    # =====================================================

    daily_perf = (
        perf
        .groupby(
            "performance_date",
            as_index=False,
        )[
            [
                "paid",
                "unpaid",
                "paid_invoice_revenue",
                "unpaid_invoice_revenue",
            ]
        ]
        .sum()
        .rename(
            columns={
                "performance_date": "date",
            }
        )
    )

    # =====================================================
    # DAILY INVOICE QTY
    # =====================================================

    daily_invoice = pd.DataFrame(
        columns=[
            "date",
            "Qty Invoice Paid",
            "Qty Invoice Unpaid",
        ]
    )

    if not perf.empty:
        invoice_state = build_invoice_state(
            perf
        )

        if not invoice_state.empty:
            # Ambil tanggal dari transaksi
            # sesuai dashboard_date/performance_date.
            invoice_dates = (
                perf[
                    [
                        "company",
                        "agent_key",
                        "invoice_no",
                        "performance_date",
                    ]
                ]
                .dropna(
                    subset=["invoice_no"]
                )
                .drop_duplicates(
                    subset=[
                        "company",
                        "agent_key",
                        "invoice_no",
                    ],
                    keep="last",
                )
            )

            invoice_state = invoice_state.merge(
                invoice_dates,
                on=[
                    "company",
                    "agent_key",
                    "invoice_no",
                ],
                how="left",
            )

            daily_invoice = (
                invoice_state
                .groupby(
                    "performance_date",
                    as_index=False,
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
                .rename(
                    columns={
                        "performance_date": "date"
                    }
                )
            )

    # =====================================================
    # MERGE DAILY
    # =====================================================

    result = daily_target.merge(
        daily_perf,
        on="date",
        how="outer",
    )

    result = result.merge(
        daily_invoice,
        on="date",
        how="outer",
    )

    if result.empty:
        return result

    result["date"] = normalize_date(
        result["date"]
    )

    result = result.sort_values(
        "date"
    )

    numeric_columns = [
        "target",
        "paid",
        "unpaid",
        "paid_invoice_revenue",
        "unpaid_invoice_revenue",
        "Qty Invoice Paid",
        "Qty Invoice Unpaid",
    ]

    for col in numeric_columns:
        if col not in result.columns:
            result[col] = 0

        result[col] = (
            pd.to_numeric(
                result[col],
                errors="coerce",
            )
            .fillna(0)
        )

    result["Qty Invoice Paid"] = (
        result["Qty Invoice Paid"]
        .astype(int)
    )

    result["Qty Invoice Unpaid"] = (
        result["Qty Invoice Unpaid"]
        .astype(int)
    )

    # =====================================================
    # ACHIEVEMENT
    # =====================================================

    result["achievement_pct"] = safe_pct(
        result["paid"],
        result["target"],
    )

    # =====================================================
    # PROJECTION
    # =====================================================

    result["projection_pct"] = safe_pct(
        result["paid"]
        + result["unpaid"],
        result["target"],
    )

    # =====================================================
    # ACHIEVEMENT CVR
    # =====================================================

    result["achievement_cvr"] = (
        result["Qty Invoice Paid"]
        / (
            result["Qty Invoice Paid"]
            + result["Qty Invoice Unpaid"]
        )
        * 100
    ).where(
        (
            result["Qty Invoice Paid"]
            + result["Qty Invoice Unpaid"]
        ) > 0,
        0,
    )

    return result.reset_index(
        drop=True
    )


# =========================================================
# RANGE PERFORMANCE
# =========================================================

def build_range_performance(
    start_date,
    end_date,
    company,
    team_leader=None,
    agent=None,
    role=None,
    tier=None,
):

    perf, target = build_dashboard_performance()

    company_key = get_company_key(
        company
    )

    start_date = pd.Timestamp(
        start_date
    ).normalize()

    end_date = pd.Timestamp(
        end_date
    ).normalize()

    # =====================================================
    # FILTER
    # =====================================================

    perf = perf[
        (
            perf["company"]
            == company_key
        )
        & (
            perf["performance_date"]
            >= start_date
        )
        & (
            perf["performance_date"]
            <= end_date
        )
    ].copy()

    target = target[
        (
            target["company"]
            == company_key
        )
        & (
            target["target_date"]
            >= start_date
        )
        & (
            target["target_date"]
            <= end_date
        )
    ].copy()

    perf = apply_common_filters(
        perf,
        team_leader,
        agent,
        role,
        tier,
    )

    target = apply_common_filters(
        target,
        team_leader,
        agent,
        role,
        tier,
    )

    # =====================================================
    # VALUES
    # =====================================================

    target_value = target[
        "daily_target"
    ].sum()

    paid_value = perf[
        "paid"
    ].sum()

    unpaid_value = perf[
        "unpaid"
    ].sum()

    paid_invoice_value = perf[
        "paid_invoice_revenue"
    ].sum()

    unpaid_invoice_value = perf[
        "unpaid_invoice_revenue"
    ].sum()

    # =====================================================
    # INVOICE QTY
    # =====================================================

    invoice_qty = build_invoice_quantity(
        perf
    )

    qty_paid = (
        invoice_qty["Qty Invoice Paid"].sum()
        if not invoice_qty.empty
        else 0
    )

    qty_unpaid = (
        invoice_qty["Qty Invoice Unpaid"].sum()
        if not invoice_qty.empty
        else 0
    )

    # =====================================================
    # KPI
    # =====================================================

    achievement_pct = (
        paid_value
        / target_value
        * 100
        if target_value > 0
        else 0
    )

    projection_pct = (
        (
            paid_value
            + unpaid_value
        )
        / target_value
        * 100
        if target_value > 0
        else 0
    )

    achievement_cvr = calculate_cvr(
        qty_paid,
        qty_unpaid,
    )

    return {
        "company": company,
        "start_date": start_date,
        "end_date": end_date,
        "target": target_value,
        "paid": paid_value,
        "unpaid": unpaid_value,
        "Qty Invoice Paid": int(qty_paid),
        "Qty Invoice Unpaid": int(qty_unpaid),
        "paid_invoice_revenue": paid_invoice_value,
        "unpaid_invoice_revenue": unpaid_invoice_value,
        "achievement_pct": achievement_pct,
        "projection_pct": projection_pct,
        "achievement_cvr": achievement_cvr,
    }


# =========================================================
# AGENT RANKING
# =========================================================

def build_agent_ranking(
    start_date,
    end_date,
    company,
    team_leader=None,
    agent=None,
    role=None,
    tier=None,
):

    perf, target = build_dashboard_performance()

    company_key = get_company_key(
        company
    )

    start_date = pd.Timestamp(
        start_date
    ).normalize()

    end_date = pd.Timestamp(
        end_date
    ).normalize()

    # =====================================================
    # TARGET
    # =====================================================

    target = target[
        (
            target["company"]
            == company_key
        )
        & (
            target["target_date"]
            >= start_date
        )
        & (
            target["target_date"]
            <= end_date
        )
    ].copy()

    target = apply_common_filters(
        target,
        team_leader,
        agent,
        role,
        tier,
    )

    # =====================================================
    # PERFORMANCE
    # =====================================================

    perf = perf[
        (
            perf["company"]
            == company_key
        )
        & (
            perf["performance_date"]
            >= start_date
        )
        & (
            perf["performance_date"]
            <= end_date
        )
    ].copy()

    perf = apply_common_filters(
        perf,
        team_leader,
        agent,
        role,
        tier,
    )

    # =====================================================
    # TARGET PER AGENT
    # =====================================================

    target_agent = (
        target
        .groupby(
            [
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
            ],
            dropna=False,
            as_index=False,
        )["daily_target"]
        .sum()
        .rename(
            columns={
                "daily_target": "target"
            }
        )
    )

    # =====================================================
    # PERFORMANCE PER AGENT
    # =====================================================

    performance_agent = (
        perf
        .groupby(
            [
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
            ],
            dropna=False,
            as_index=False,
        )[
            [
                "paid",
                "unpaid",
                "paid_invoice_revenue",
                "unpaid_invoice_revenue",
            ]
        ]
        .sum()
    )

    # =====================================================
    # MERGE TARGET + PERFORMANCE
    # =====================================================

    result = target_agent.merge(
        performance_agent,
        on=[
            "company",
            "agent_key",
            "agent",
            "role",
            "team_leader",
            "tier",
        ],
        how="left",
    )

    if result.empty:
        return result

    # =====================================================
    # NUMERIC
    # =====================================================

    numeric_columns = [
        "target",
        "paid",
        "unpaid",
        "paid_invoice_revenue",
        "unpaid_invoice_revenue",
    ]

    for col in numeric_columns:
        result[col] = (
            pd.to_numeric(
                result[col],
                errors="coerce",
            )
            .fillna(0)
        )

    # =====================================================
    # UNIQUE INVOICE
    # =====================================================

    invoice_qty = build_invoice_quantity(
        perf
    )

    if not invoice_qty.empty:

        result = result.merge(
            invoice_qty,
            on=[
                "company",
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
            ],
            how="left",
        )

    else:

        result["Qty Invoice Paid"] = 0
        result["Qty Invoice Unpaid"] = 0

    # =====================================================
    # CLEAN QTY
    # =====================================================

    result["Qty Invoice Paid"] = (
        pd.to_numeric(
            result["Qty Invoice Paid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    result["Qty Invoice Unpaid"] = (
        pd.to_numeric(
            result["Qty Invoice Unpaid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    # =====================================================
    # ACHIEVEMENT
    # =====================================================

    result["achievement_pct"] = safe_pct(
        result["paid"],
        result["target"],
    )

    # =====================================================
    # PROJECTION
    # =====================================================

    result["projection_pct"] = safe_pct(
        result["paid"]
        + result["unpaid"],
        result["target"],
    )

    # =====================================================
    # ACHIEVEMENT CVR
    # =====================================================

    result["achievement_cvr"] = (
        result["Qty Invoice Paid"]
        / (
            result["Qty Invoice Paid"]
            + result["Qty Invoice Unpaid"]
        )
        * 100
    ).where(
        (
            result["Qty Invoice Paid"]
            + result["Qty Invoice Unpaid"]
        ) > 0,
        0,
    )

    # =====================================================
    # AGENT DISPLAY
    # =====================================================

    result["agent_display"] = (
        result["agent"]
        .fillna("-")
        .astype("string")
    )

    # =====================================================
    # SORT
    # =====================================================

    result = result.sort_values(
        [
            "achievement_pct",
            "agent",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(
        drop=True
    )

    return result


# =========================================================
# MTD TEAM
# =========================================================

def build_mtd_team(
    period_end,
    company,
):

    perf, target = build_dashboard_performance()

    period_end = pd.Timestamp(
        period_end
    ).normalize()

    month_start = period_end.replace(
        day=1
    )

    company_key = get_company_key(
        company
    )

    # =====================================================
    # FILTER
    # =====================================================

    perf = perf[
        (
            perf["company"]
            == company_key
        )
        & (
            perf["performance_date"]
            >= month_start
        )
        & (
            perf["performance_date"]
            <= period_end
        )
    ].copy()

    target = target[
        (
            target["company"]
            == company_key
        )
        & (
            target["target_date"]
            >= month_start
        )
        & (
            target["target_date"]
            <= period_end
        )
    ].copy()

    # =====================================================
    # TARGET TEAM
    # =====================================================

    target_team = (
        target
        .groupby(
            "team_leader",
            as_index=False,
        )["daily_target"]
        .sum()
        .rename(
            columns={
                "daily_target": "target"
            }
        )
    )

    # =====================================================
    # PERFORMANCE TEAM
    # =====================================================

    perf_team = (
        perf
        .groupby(
            "team_leader",
            as_index=False,
        )[
            [
                "paid",
                "unpaid",
                "paid_invoice_revenue",
                "unpaid_invoice_revenue",
            ]
        ]
        .sum()
    )

    # =====================================================
    # MERGE
    # =====================================================

    result = target_team.merge(
        perf_team,
        on="team_leader",
        how="left",
    )

    # =====================================================
    # NUMERIC
    # =====================================================

    for col in [
        "target",
        "paid",
        "unpaid",
        "paid_invoice_revenue",
        "unpaid_invoice_revenue",
    ]:

        result[col] = (
            pd.to_numeric(
                result[col],
                errors="coerce",
            )
            .fillna(0)
        )

    # =====================================================
    # ACHIEVEMENT
    # =====================================================

    result["achievement_pct"] = safe_pct(
        result["paid"],
        result["target"],
    )

    # =====================================================
    # PROJECTION
    # =====================================================

    result["projection_pct"] = safe_pct(
        result["paid"]
        + result["unpaid"],
        result["target"],
    )

    return result


# =========================================================
# MTD AGENT
# =========================================================

def build_mtd_agent(
    period_end,
    company,
):

    perf, target = build_dashboard_performance()

    period_end = pd.Timestamp(
        period_end
    ).normalize()

    month_start = period_end.replace(
        day=1
    )

    company_key = get_company_key(
        company
    )

    # =====================================================
    # FILTER PERFORMANCE
    # =====================================================

    perf = perf[
        (
            perf["company"]
            == company_key
        )
        & (
            perf["performance_date"]
            >= month_start
        )
        & (
            perf["performance_date"]
            <= period_end
        )
    ].copy()

    # =====================================================
    # FILTER TARGET
    # =====================================================

    target = target[
        (
            target["company"]
            == company_key
        )
        & (
            target["target_date"]
            >= month_start
        )
        & (
            target["target_date"]
            <= period_end
        )
    ].copy()

    # =====================================================
    # TARGET AGENT
    # =====================================================

    target_agent = (
        target
        .groupby(
            [
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
            ],
            dropna=False,
            as_index=False,
        )["daily_target"]
        .sum()
        .rename(
            columns={
                "daily_target": "target"
            }
        )
    )

    # =====================================================
    # PERFORMANCE AGENT
    # =====================================================

    perf_agent = (
        perf
        .groupby(
            [
                "agent_key",
                "agent",
                "role",
                "team_leader",
                "tier",
            ],
            dropna=False,
            as_index=False,
        )[
            [
                "paid",
                "unpaid",
                "paid_invoice_revenue",
                "unpaid_invoice_revenue",
            ]
        ]
        .sum()
    )

    # =====================================================
    # MERGE
    # =====================================================

    result = target_agent.merge(
        perf_agent,
        on=[
            "agent_key",
            "agent",
            "role",
            "team_leader",
            "tier",
        ],
        how="left",
    )

    if result.empty:
        return result

    # =====================================================
    # NUMERIC
    # =====================================================

    for col in [
        "target",
        "paid",
        "unpaid",
        "paid_invoice_revenue",
        "unpaid_invoice_revenue",
    ]:

        result[col] = (
            pd.to_numeric(
                result[col],
                errors="coerce",
            )
            .fillna(0)
        )

    # =====================================================
    # INVOICE QTY
    # =====================================================

    invoice_qty = build_invoice_quantity(
        perf
    )

    if not invoice_qty.empty:

        result = result.merge(
            invoice_qty[
                [
                    "agent_key",
                    "Qty Invoice Paid",
                    "Qty Invoice Unpaid",
                ]
            ],
            on="agent_key",
            how="left",
        )

    else:

        result["Qty Invoice Paid"] = 0
        result["Qty Invoice Unpaid"] = 0

    result["Qty Invoice Paid"] = (
        pd.to_numeric(
            result["Qty Invoice Paid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    result["Qty Invoice Unpaid"] = (
        pd.to_numeric(
            result["Qty Invoice Unpaid"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    # =====================================================
    # ACHIEVEMENT
    # =====================================================

    result["achievement_pct"] = safe_pct(
        result["paid"],
        result["target"],
    )

    # =====================================================
    # PROJECTION
    # =====================================================

    result["projection_pct"] = safe_pct(
        result["paid"]
        + result["unpaid"],
        result["target"],
    )

    # =====================================================
    # ACHIEVEMENT CVR
    # =====================================================

    result["achievement_cvr"] = (
        result["Qty Invoice Paid"]
        / (
            result["Qty Invoice Paid"]
            + result["Qty Invoice Unpaid"]
        )
        * 100
    ).where(
        (
            result["Qty Invoice Paid"]
            + result["Qty Invoice Unpaid"]
        ) > 0,
        0,
    )

    return result


# =========================================================
# AUDIT
# =========================================================

if __name__ == "__main__":

    start = pd.Timestamp(
        "2026-10-01"
    )

    end = pd.Timestamp(
        "2026-10-05"
    )

    clear_dashboard_cache()

    for company in VALID_COMPANIES:

        print(
            "\n"
            + "=" * 80
        )

        print(
            f"COMPANY: {company}"
        )

        print(
            "=" * 80
        )

        # =================================================
        # RANGE
        # =================================================

        print(
            "\n--- RANGE ---"
        )

        range_result = build_range_performance(
            start_date=start,
            end_date=end,
            company=company,
        )

        print(
            range_result
        )

        # =================================================
        # DAILY
        # =================================================

        print(
            "\n--- DAILY ---"
        )

        daily_result = build_daily_performance(
            start_date=start,
            end_date=end,
            company=company,
        )

        if not daily_result.empty:

            print(
                daily_result[
                    [
                        "date",
                        "target",
                        "paid",
                        "unpaid",
                        "Qty Invoice Paid",
                        "Qty Invoice Unpaid",
                        "paid_invoice_revenue",
                        "unpaid_invoice_revenue",
                        "achievement_pct",
                        "projection_pct",
                        "achievement_cvr",
                    ]
                ].to_string(
                    index=False
                )
            )

        else:

            print(
                "Tidak ada data daily."
            )

        # =================================================
        # AGENT RANKING
        # =================================================

        print(
            "\n--- AGENT RANKING ---"
        )

        ranking_result = build_agent_ranking(
            start_date=start,
            end_date=end,
            company=company,
        )

        if not ranking_result.empty:

            print(
                ranking_result[
                    [
                        "agent",
                        "role",
                        "team_leader",
                        "tier",
                        "target",
                        "Qty Invoice Paid",
                        "Qty Invoice Unpaid",
                        "paid_invoice_revenue",
                        "unpaid_invoice_revenue",
                        "achievement_pct",
                        "projection_pct",
                        "achievement_cvr",
                    ]
                ].to_string(
                    index=False
                )
            )

        else:

            print(
                "Tidak ada data agent."
            )

        # =================================================
        # MTD TEAM
        # =================================================

        print(
            "\n--- MTD TEAM ---"
        )

        mtd_team_result = build_mtd_team(
            period_end=end,
            company=company,
        )

        print(
            mtd_team_result.to_string(
                index=False
            )
        )

        # =================================================
        # MTD AGENT
        # =================================================

        print(
            "\n--- MTD AGENT ---"
        )

        mtd_agent_result = build_mtd_agent(
            period_end=end,
            company=company,
        )

        print(
            mtd_agent_result.to_string(
                index=False
            )
        )
