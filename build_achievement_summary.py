import pandas as pd

from build_achievement_fact import build_achievement_fact


# =========================================================
# LOAD ACHIEVEMENT FACT
# =========================================================

def load_achievement():
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

    return achievement


# =========================================================
# HELPER
# =========================================================

def calculate_achievement(df):
    df["achievement_pct"] = (
        df["actual"]
        .div(df["target"])
        .mul(100)
    )

    df.loc[
        df["target"] <= 0,
        "achievement_pct",
    ] = pd.NA

    df["achievement_status"] = (
        df["achievement_pct"]
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

    return df


# =========================================================
# DAILY SUMMARY
# =========================================================

def build_daily_summary(achievement):

    daily = (
        achievement
        .groupby(
            [
                "achievement_date",
                "company",
            ],
            as_index=False,
        )
        .agg(
            target=("target", "sum"),
            actual=("actual", "sum"),
            agents=("agent", "nunique"),
        )
    )

    daily = calculate_achievement(daily)

    return daily


# =========================================================
# WEEKLY SUMMARY
# =========================================================

def build_weekly_summary(achievement):

    achievement = achievement.copy()

    achievement["week_start"] = (
        achievement["achievement_date"]
        - pd.to_timedelta(
            achievement["achievement_date"].dt.weekday,
            unit="D",
        )
    )

    weekly = (
        achievement
        .groupby(
            [
                "week_start",
                "company",
            ],
            as_index=False,
        )
        .agg(
            target=("target", "sum"),
            actual=("actual", "sum"),
            agents=("agent", "nunique"),
        )
    )

    weekly = calculate_achievement(weekly)

    return weekly


# =========================================================
# MONTHLY SUMMARY
# =========================================================

def build_monthly_summary(achievement):

    achievement = achievement.copy()

    achievement["month"] = (
        achievement["achievement_date"]
        .dt.to_period("M")
        .astype(str)
    )

    monthly = (
        achievement
        .groupby(
            [
                "month",
                "company",
            ],
            as_index=False,
        )
        .agg(
            target=("target", "sum"),
            actual=("actual", "sum"),
            agents=("agent", "nunique"),
        )
    )

    monthly = calculate_achievement(monthly)

    return monthly


# =========================================================
# TEAM SUMMARY
# =========================================================

def build_team_summary(achievement):

    team = (
        achievement
        .groupby(
            [
                "achievement_date",
                "company",
                "team_leader",
            ],
            as_index=False,
        )
        .agg(
            target=("target", "sum"),
            actual=("actual", "sum"),
            agents=("agent", "nunique"),
        )
    )

    team = calculate_achievement(team)

    return team


# =========================================================
# AGENT SUMMARY
# =========================================================

def build_agent_summary(achievement):

    agent = (
        achievement
        .groupby(
            [
                "achievement_date",
                "company",
                "agent",
                "role",
                "team_leader",
                "tier",
            ],
            as_index=False,
        )
        .agg(
            target=("target", "sum"),
            actual=("actual", "sum"),
        )
    )

    agent = calculate_achievement(agent)

    return agent


# =========================================================
# AUDIT
# =========================================================

if __name__ == "__main__":

    achievement = load_achievement()

    daily = build_daily_summary(
        achievement
    )

    weekly = build_weekly_summary(
        achievement
    )

    monthly = build_monthly_summary(
        achievement
    )

    team = build_team_summary(
        achievement
    )

    agent = build_agent_summary(
        achievement
    )

    print("\n========================================")
    print("ACHIEVEMENT SUMMARY AUDIT")
    print("========================================")

    print("\n===== DAILY =====")

    print(
        daily.to_string(
            index=False
        )
    )

    print("\n===== WEEKLY =====")

    print(
        weekly.to_string(
            index=False
        )
    )

    print("\n===== MONTHLY =====")

    print(
        monthly.to_string(
            index=False
        )
    )

    print("\n===== TEAM SAMPLE =====")

    print(
        team.head(20).to_string(
            index=False
        )
    )

    print("\n===== AGENT SAMPLE =====")

    print(
        agent.head(20).to_string(
            index=False
        )
    )
