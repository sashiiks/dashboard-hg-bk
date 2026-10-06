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

    target = prepare_target_agent(target)

    # Hanya HG & BK
    target = target[
        target["Company"].isin(["HG", "BK"])
        & target["Nama Agent"].ne("")
    ].copy()

    hg = prepare_sales(hg, "Healthy Go")
    bk = prepare_sales(bk, "Bekelin")

    hg_fact = build_transaction_fact(
        hg,
        target,
    )

    bk_fact = build_transaction_fact(
        bk,
        target,
    )

    transaction_fact = pd.concat(
        [hg_fact, bk_fact],
        ignore_index=True,
    )

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
    # ACTUAL
    # =====================================================

    performance["actual"] = (
        pd.to_numeric(
            performance["performance_amount"],
            errors="coerce",
        )
        .fillna(0)
    )

    performance["actual"] = performance[
        "actual"
    ].where(
        performance["is_dashboard"],
        0,
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
            )
        )
        .rename(
            columns={
                "performance_date": "achievement_date"
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

    # Tidak ada transaksi = actual 0
    achievement["actual"] = (
        achievement["actual"]
        .fillna(0)
    )

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

    print("\n===== ACHIEVEMENT STATUS =====")

    print(
        achievement[
            "achievement_status"
        ]
        .value_counts()
        .to_string()
    )

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
        )
        .to_string()
    )

    print("\n===== SAMPLE =====")

    print(
        achievement.head(20).to_string(
            index=False
        )
    )
