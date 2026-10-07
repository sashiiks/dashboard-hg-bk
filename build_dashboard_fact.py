import pandas as pd

from build_achievement_fact import build_achievement_fact
from build_performance_fact import build_performance_fact
from build_transaction_fact import (
    load_sheet,
    prepare_target_agent,
    prepare_sales,
    build_transaction_fact,
)


BRAND_TO_COMPANY = {
    "Healthy Go": "HG",
    "Bekelin": "BK",
}


# =========================================================
# BUILD TRANSACTION + PERFORMANCE
# =========================================================

def build_performance():

    target = load_sheet("TARGET AGENT")
    hg = load_sheet("SALES HG OCT")
    bk = load_sheet("SALES BK OCT")

    target = prepare_target_agent(target)

    target = target[
        target["Company"].isin(["HG", "BK"])
        & target["Nama Agent"].ne("")
    ].copy()

    hg = prepare_sales(
        hg,
        "Healthy Go",
    )

    bk = prepare_sales(
        bk,
        "Bekelin",
    )

    hg_fact = build_transaction_fact(
        hg,
        target,
    )

    bk_fact = build_transaction_fact(
        bk,
        target,
    )

    transaction_fact = pd.concat(
        [
            hg_fact,
            bk_fact,
        ],
        ignore_index=True,
    )

    performance_fact = build_performance_fact(
        transaction_fact
    )

    return performance_fact


# =========================================================
# BUILD DASHBOARD KPI
# =========================================================

def build_dashboard_kpi():

    achievement = build_achievement_fact()

    performance = build_performance()

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    achievement["achievement_date"] = pd.to_datetime(
        achievement["achievement_date"],
        errors="coerce",
    )

    performance["performance_date"] = pd.to_datetime(
        performance["performance_date"],
        errors="coerce",
    )

    # -----------------------------------------------------
    # LAST PERFORMANCE DATE
    # -----------------------------------------------------

    last_date = achievement[
        "achievement_date"
    ].max()

    # Hanya tanggal yang sudah punya actual
    actual_dates = achievement.loc[
        achievement["actual"] > 0,
        "achievement_date",
    ]

    if not actual_dates.empty:
        last_actual_date = actual_dates.max()
    else:
        last_actual_date = last_date

    # -----------------------------------------------------
    # MTD
    # -----------------------------------------------------

    current_month = last_actual_date.month
    current_year = last_actual_date.year

    mtd = achievement[
        (
            achievement["achievement_date"].dt.year
            == current_year
        )
        & (
            achievement["achievement_date"].dt.month
            == current_month
        )
        & (
            achievement["achievement_date"]
            <= last_actual_date
        )
    ].copy()

    # -----------------------------------------------------
    # COMPANY KPI
    # -----------------------------------------------------

    company_kpi = (
        mtd
        .groupby(
            "company",
            as_index=False,
        )
        .agg(
            target=(
                "target",
                "sum",
            ),
            actual=(
                "actual",
                "sum",
            ),
        )
    )

    company_kpi["achievement_pct"] = (
        company_kpi["actual"]
        .div(company_kpi["target"])
        .mul(100)
    )

    company_kpi["achievement_status"] = (
        company_kpi["achievement_pct"]
        .apply(
            lambda x: (
                "achieved"
                if pd.notna(x) and x >= 80
                else "below_target"
            )
        )
    )

    # -----------------------------------------------------
    # TOTAL KPI
    # -----------------------------------------------------

    total_target = mtd["target"].sum()
    total_actual = mtd["actual"].sum()

    if total_target > 0:
        total_achievement = (
            total_actual
            / total_target
            * 100
        )
    else:
        total_achievement = 0

    # -----------------------------------------------------
    # LIVE STATUS
    # -----------------------------------------------------

    performance["company"] = (
        performance["brand"]
        .map(BRAND_TO_COMPANY)
    )

    paid = performance[
        performance["status_live"]
        .eq("Paid")
    ]

    unpaid = performance[
        performance["status_live"]
        .eq("Unpaid")
    ]

    # -----------------------------------------------------
    # LIVE NOMINAL
    # -----------------------------------------------------

    paid_amount = pd.to_numeric(
        paid["performance_amount"],
        errors="coerce",
    ).fillna(0).sum()

    unpaid_amount = pd.to_numeric(
        unpaid["performance_amount"],
        errors="coerce",
    ).fillna(0).sum()

    # -----------------------------------------------------
    # LAST SOURCE UPDATE
    # -----------------------------------------------------

    source_updated = pd.to_datetime(
        performance["source_updated_at"],
        errors="coerce",
    )

    last_source_update = source_updated.max()

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    return {
        "last_actual_date": last_actual_date,
        "total_target": total_target,
        "total_actual": total_actual,
        "total_achievement_pct": total_achievement,
        "paid_count": len(paid),
        "unpaid_count": len(unpaid),
        "paid_amount": paid_amount,
        "unpaid_amount": unpaid_amount,
        "last_source_update": last_source_update,
        "company_kpi": company_kpi,
    }


# =========================================================
# AUDIT
# =========================================================

if __name__ == "__main__":

    dashboard = build_dashboard_kpi()

    print("\n========================================")
    print("DASHBOARD KPI AUDIT")
    print("========================================")

    print(
        f"\nLast actual date : "
        f"{dashboard['last_actual_date']}"
    )

    print(
        f"MTD Target       : "
        f"Rp {dashboard['total_target']:,.0f}"
    )

    print(
        f"MTD Actual       : "
        f"Rp {dashboard['total_actual']:,.0f}"
    )

    print(
        f"MTD Achievement  : "
        f"{dashboard['total_achievement_pct']:.2f}%"
    )

    print(
        f"\nPaid Count       : "
        f"{dashboard['paid_count']:,}"
    )

    print(
        f"Unpaid Count     : "
        f"{dashboard['unpaid_count']:,}"
    )

    print(
        f"Paid Amount      : "
        f"Rp {dashboard['paid_amount']:,.0f}"
    )

    print(
        f"Unpaid Amount    : "
        f"Rp {dashboard['unpaid_amount']:,.0f}"
    )

    print(
        f"\nLast Source Update : "
        f"{dashboard['last_source_update']}"
    )

    print("\n===== COMPANY KPI =====")

    print(
        dashboard["company_kpi"].to_string(
            index=False
        )
    )
