import pandas as pd

from build_transaction_fact import (
    load_sheet,
    prepare_target_agent,
    prepare_sales,
    build_transaction_fact,
)

from build_performance_fact import (
    build_performance_fact,
)

from build_target_fact import (
    build_target_fact,
)


BRAND_TO_COMPANY = {
    "Healthy Go": "HG",
    "Bekelin": "BK",
}


# =========================================================
# LOAD TRANSACTION + PERFORMANCE
# =========================================================

def build_performance():
    target = load_sheet("TARGET AGENT")

    hg = load_sheet("SALES HG OCT")
    bk = load_sheet("SALES BK OCT")

    # Prepare TARGET AGENT
    target = prepare_target_agent(target)

    # Hanya HG & BK
    target = target[
        target["Company"].isin(["HG", "BK"])
        & target["Nama Agent"].ne("")
    ].copy()

    # Prepare sales
    hg = prepare_sales(
        hg,
        "Healthy Go",
    )

    bk = prepare_sales(
        bk,
        "Bekelin",
    )

    # Build transaction fact per brand
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

    # Build performance fact
    performance_fact = build_performance_fact(
        transaction_fact
    )

    return performance_fact


# =========================================================
# LOAD TARGET FACT
# =========================================================

def build_targets():
    target = load_sheet("TARGET AGENT")

    target = prepare_target_agent(target)

    # Hanya HG & BK
    target = target[
        target["Company"].isin(["HG", "BK"])
        & target["Nama Agent"].ne("")
    ].copy()

    target_fact = build_target_fact(
        target
    )

    return target_fact


# =========================================================
# BUILD ACHIEVEMENT FACT
# =========================================================

def build_achievement_fact():

    performance = build_performance()
    target = build_targets()

    # =====================================================
    # PERFORMANCE COMPANY
    # =====================================================

    performance["company"] = (
        performance["brand"]
        .map(BRAND_TO_COMPANY)
    )

    # =====================================================
    # NORMALIZE AGENT
    # =====================================================

    performance["agent_key"] = (
        performance["sales"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    target["agent_key"] = (
        target["agent"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    # =====================================================
    # TARGET MASTER
    # =====================================================

    agent_master = target[
        [
            "company",
            "agent",
            "role",
            "team_leader",
            "tier",
            "agent_key",
        ]
    ].drop_duplicates(
        subset=[
            "company",
            "agent_key",
        ]
    )

    # =====================================================
    # ONLY MATCHED AGENT
    # =====================================================

    performance = performance.merge(
        agent_master,
        on=[
            "company",
            "agent_key",
        ],
        how="inner",
        suffixes=(
            "_performance",
            "_target",
        ),
    )

    # =====================================================
    # ONLY DASHBOARD TRANSACTION
    # =====================================================
    #
    # Dashboard scope:
    # - Paid    -> is_dashboard = True
    # - Unpaid  -> is_dashboard = True
    # - Cancel  -> excluded
    #
    # Karena agent sudah di-inner join dengan TARGET AGENT,
    # transaksi unmapped otomatis tidak masuk achievement.
    # =====================================================

    performance = performance[
        performance["is_dashboard"]
    ].copy()

    # =====================================================
    # ACTUAL
    # =====================================================

    performance["actual"] = (
        pd.to_numeric(
            performance["performance_amount"],
            errors="coerce",
        )
        .fillna(0)
    )

    # =====================================================
    # INVOICE QUANTITY
    # =====================================================

    performance["qty_invoice"] = (
        performance["invoice_no"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .astype(int)
    )

    performance["qty_invoice_paid"] = (
        performance["qty_invoice"]
        .where(
            performance["is_paid"],
            0,
        )
    )

    performance["qty_invoice_unpaid"] = (
        performance["qty_invoice"]
        .where(
            performance["is_unpaid"],
            0,
        )
    )

    # =====================================================
    # DAILY ACTUAL
    # =====================================================

    daily_actual = (
        performance[
            performance["performance_date"].notna()
        ]
        .groupby(
            [
                "company",
                "agent",
                "role",
                "team_leader",
                "tier",
                "performance_date",
            ],
            as_index=False,
        )
        .agg(
            actual=(
                "actual",
                "sum",
            ),
            qty_invoice_paid=(
                "qty_invoice_paid",
                "sum",
            ),
            qty_invoice_unpaid=(
                "qty_invoice_unpaid",
                "sum",
            ),
        )
        .rename(
            columns={
                "performance_date": "achievement_date",
            }
        )
    )

    # =====================================================
    # DAILY TARGET
    # =====================================================

    daily_target = target[
        [
            "company",
            "agent",
            "role",
            "team_leader",
            "tier",
            "target_date",
            "daily_target",
        ]
    ].copy()

    daily_target = daily_target.rename(
        columns={
            "target_date": "achievement_date",
            "daily_target": "target",
        }
    )

    # =====================================================
    # TARGET + ACTUAL
    # =====================================================

    achievement = daily_target.merge(
        daily_actual,
        on=[
            "company",
            "agent",
            "role",
            "team_leader",
            "tier",
            "achievement_date",
        ],
        how="left",
    )

    # =====================================================
    # DEFAULT VALUE
    # =====================================================

    # Tidak ada transaksi = actual 0
    achievement["actual"] = (
        achievement["actual"]
        .fillna(0)
    )

    # Tidak ada Paid invoice = 0
    achievement["qty_invoice_paid"] = (
        achievement["qty_invoice_paid"]
        .fillna(0)
        .astype(int)
    )

    # Tidak ada Unpaid invoice = 0
    achievement["qty_invoice_unpaid"] = (
        achievement["qty_invoice_unpaid"]
        .fillna(0)
        .astype(int)
    )

    # Target numeric
    achievement["target"] = (
        pd.to_numeric(
            achievement["target"],
            errors="coerce",
        )
        .fillna(0)
    )

    # =====================================================
    # ACHIEVEMENT %
    # =====================================================

    achievement["achievement_pct"] = (
        achievement["actual"]
        .div(
            achievement["target"]
        )
        .mul(100)
    )

    achievement.loc[
        achievement["target"] <= 0,
        "achievement_pct",
    ] = pd.NA

    # =====================================================
    # ACHIEVEMENT STATUS
    # =====================================================

    achievement["achievement_status"] = (
        achievement["achievement_pct"]
        .apply(
            lambda x: (
                "achieved"
                if pd.notna(x) and x >= 80
                else (
                    "below_target"
                    if pd.notna(x)
                    else "no_target"
                )
            )
        )
    )

    # =====================================================
    # FINAL COLUMNS
    # =====================================================

    achievement = achievement[
        [
            "achievement_date",
            "company",
            "agent",
            "role",
            "team_leader",
            "tier",
            "target",
            "actual",
            "qty_invoice_paid",
            "qty_invoice_unpaid",
            "achievement_pct",
            "achievement_status",
        ]
    ].sort_values(
        [
            "achievement_date",
            "company",
            "team_leader",
            "agent",
        ]
    )

    return achievement


# =========================================================
# AUDIT
# =========================================================

if __name__ == "__main__":

    achievement = build_achievement_fact()

    print("\n===== ACHIEVEMENT FACT =====")

    print(
        f"Total rows : "
        f"{len(achievement):,}"
    )

    print(
        f"Unique agent : "
        f"{achievement['agent'].nunique():,}"
    )

    print(
        f"Unique company : "
        f"{achievement['company'].nunique():,}"
    )

    print(
        f"Date range : "
        f"{achievement['achievement_date'].min()} "
        f"→ "
        f"{achievement['achievement_date'].max()}"
    )

    # =====================================================
    # ACHIEVEMENT STATUS
    # =====================================================

    print("\n===== ACHIEVEMENT STATUS =====")

    print(
        achievement[
            "achievement_status"
        ]
        .value_counts()
        .to_string()
    )

    # =====================================================
    # BY COMPANY
    # =====================================================

    print("\n===== BY COMPANY =====")

    print(
        achievement
        .groupby("company")
        .agg(
            agents=(
                "agent",
                "nunique",
            ),
            rows=(
                "agent",
                "count",
            ),
            target=(
                "target",
                "sum",
            ),
            actual=(
                "actual",
                "sum",
            ),
            qty_invoice_paid=(
                "qty_invoice_paid",
                "sum",
            ),
            qty_invoice_unpaid=(
                "qty_invoice_unpaid",
                "sum",
            ),
        )
        .to_string()
    )

    # =====================================================
    # INVOICE QUANTITY VALIDATION
    # =====================================================

    print("\n===== INVOICE QUANTITY VALIDATION =====")

    total_paid = (
        achievement["qty_invoice_paid"]
        .sum()
    )

    total_unpaid = (
        achievement["qty_invoice_unpaid"]
        .sum()
    )

    print(
        f"Paid Invoice Qty   : "
        f"{total_paid:,}"
    )

    print(
        f"Unpaid Invoice Qty : "
        f"{total_unpaid:,}"
    )

    print(
        f"Dashboard Invoice  : "
        f"{total_paid + total_unpaid:,}"
    )

    # =====================================================
    # SAMPLE
    # =====================================================

    print("\n===== SAMPLE =====")

    print(
        achievement.head(20).to_string(
            index=False
        )
    )
