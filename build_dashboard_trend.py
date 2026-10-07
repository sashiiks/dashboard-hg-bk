import pandas as pd

from build_achievement_fact import build_achievement_fact


# =========================================================
# BUILD DAILY MTD TREND
# =========================================================

def build_mtd_trend():

    achievement = build_achievement_fact()

    achievement["achievement_date"] = pd.to_datetime(
        achievement["achievement_date"],
        errors="coerce",
    )

    achievement["target"] = pd.to_numeric(
        achievement["target"],
        errors="coerce",
    ).fillna(0)

    achievement["actual"] = pd.to_numeric(
        achievement["actual"],
        errors="coerce",
    ).fillna(0)

    # -----------------------------------------------------
    # LAST ACTUAL DATE
    # -----------------------------------------------------

    actual_dates = achievement.loc[
        achievement["actual"] > 0,
        "achievement_date",
    ]

    if actual_dates.empty:
        raise ValueError(
            "Tidak ditemukan actual transaction."
        )

    last_actual_date = actual_dates.max()

    # -----------------------------------------------------
    # CURRENT MONTH
    # -----------------------------------------------------

    trend = achievement[
        (
            achievement["achievement_date"].dt.year
            == last_actual_date.year
        )
        & (
            achievement["achievement_date"].dt.month
            == last_actual_date.month
        )
        & (
            achievement["achievement_date"]
            <= last_actual_date
        )
    ].copy()

    # -----------------------------------------------------
    # DAILY
    # -----------------------------------------------------

    trend = (
        trend
        .groupby(
            "achievement_date",
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
        .sort_values(
            "achievement_date"
        )
    )

    # -----------------------------------------------------
    # CUMULATIVE
    # -----------------------------------------------------

    trend["target_cumulative"] = (
        trend["target"]
        .cumsum()
    )

    trend["actual_cumulative"] = (
        trend["actual"]
        .cumsum()
    )

    # -----------------------------------------------------
    # CUMULATIVE ACHIEVEMENT
    # -----------------------------------------------------

    trend["achievement_pct"] = (
        trend["actual_cumulative"]
        .div(
            trend["target_cumulative"]
        )
        .mul(100)
    )

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    trend["achievement_status"] = (
        trend["achievement_pct"]
        .apply(
            lambda x: (
                "achieved"
                if pd.notna(x) and x >= 80
                else "below_target"
            )
        )
    )

    return trend


# =========================================================
# AUDIT
# =========================================================

if __name__ == "__main__":

    trend = build_mtd_trend()

    print("\n========================================")
    print("MTD TREND AUDIT")
    print("========================================")

    print(
        trend.to_string(
            index=False
        )
    )

    print("\n===== LAST MTD =====")

    print(
        trend.tail(1).to_string(
            index=False
        )
    )
