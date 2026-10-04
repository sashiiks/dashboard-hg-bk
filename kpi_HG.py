import pandas as pd


def build_kpi_HG(target_actual_df):
    data = target_actual_df.copy()

    # Pastikan numeric
    data["target"] = pd.to_numeric(
        data["target"], errors="coerce"
    ).fillna(0)

    data["actual"] = pd.to_numeric(
        data["actual"], errors="coerce"
    ).fillna(0)

    # Achievement per agent
    data["achievement"] = (
        data["actual"]
        .div(data["target"].replace(0, pd.NA))
        .mul(100)
    )

    # Gap
    data["gap"] = data["actual"] - data["target"]

    # Status performance
    data["performance_status"] = pd.cut(
        data["achievement"],
        bins=[-float("inf"), 80, 100, float("inf")],
        labels=[
            "Below Target",
            "Near Target",
            "Achieved"
        ],
        right=False
    )

    # KPI utama
    total_target = data["target"].sum()
    total_actual = data["actual"].sum()

    overall_achievement = (
        total_actual / total_target * 100
        if total_target != 0
        else 0
    )

    total_gap = total_actual - total_target

    # Agent yang mencapai target
    agents_achieved = (
        data["achievement"] >= 100
    ).sum()

    total_agents = len(data)

    agent_achievement_rate = (
        agents_achieved / total_agents * 100
        if total_agents != 0
        else 0
    )

    kpi = {
        "total_agents": total_agents,
        "total_target": total_target,
        "total_actual": total_actual,
        "overall_achievement": overall_achievement,
        "total_gap": total_gap,
        "agents_achieved": agents_achieved,
        "agent_achievement_rate": agent_achievement_rate,
    }

    # Performance berdasarkan role
    role_performance = (
        data
        .groupby("Role", as_index=False)
        .agg(
            target=("target", "sum"),
            actual=("actual", "sum"),
            agents=("Nama Agent", "count")
        )
    )

    role_performance["achievement"] = (
        role_performance["actual"]
        / role_performance["target"]
        * 100
    )

    role_performance["gap"] = (
        role_performance["actual"]
        - role_performance["target"]
    )

    # Performance berdasarkan tier
    tier_performance = (
        data
        .groupby("Tier", as_index=False)
        .agg(
            target=("target", "sum"),
            actual=("actual", "sum"),
            agents=("Nama Agent", "count")
        )
    )

    tier_performance["achievement"] = (
        tier_performance["actual"]
        / tier_performance["target"]
        * 100
    )

    tier_performance["gap"] = (
        tier_performance["actual"]
        - tier_performance["target"]
    )

    # Top performer
    top_agents = (
        data
        .sort_values("achievement", ascending=False)
        .head(10)
        .copy()
    )

    # Bottom performer
    bottom_agents = (
        data
        .sort_values("achievement", ascending=True)
        .head(10)
        .copy()
    )

    return {
        "kpi": kpi,
        "agent_performance": data,
        "role_performance": role_performance,
        "tier_performance": tier_performance,
        "top_agents": top_agents,
        "bottom_agents": bottom_agents,
    }


def build_daily_performance_HG(target_df, transaction_df):
    target = target_df.copy()
    transactions = transaction_df.copy()

    # Rapikan kolom
    target.columns = target.columns.astype(str).str.strip()
    transactions.columns = transactions.columns.str.strip()

    # Hanya target Company HG
    target = target[
        target["Company"].astype(str).str.strip().str.upper() == "HG"
    ].copy()

    # Normalisasi nama agent
    def normalize_name(value):
        if pd.isna(value):
            return ""
        return " ".join(str(value).strip().lower().split())

    target["_agent_key"] = target["Nama Agent"].map(normalize_name)
    transactions["_agent_key"] = transactions["sales"].map(normalize_name)

    # Hanya transaksi dari agent yang terdapat di TARGET AGENT HG
    valid_agents = set(target["_agent_key"])

    transactions = transactions[
        transactions["_agent_key"].isin(valid_agents)
    ].copy()

    # Pastikan tanggal benar
    transactions["tanggal"] = pd.to_datetime(
        transactions["tanggal"],
        errors="coerce"
    )

    # September 2026 + success
    transactions = transactions[
        (transactions["tanggal"].dt.year == 2026)
        & (transactions["tanggal"].dt.month == 9)
        & (transactions["final_status"] == "success")
    ].copy()

    # Pastikan total numeric
    transactions["total"] = pd.to_numeric(
        transactions["total"],
        errors="coerce"
    ).fillna(0)

    # =========================
    # ACTUAL HARIAN
    # =========================

    actual_daily = (
        transactions
        .groupby(transactions["tanggal"].dt.day)["total"]
        .sum()
        .reset_index()
    )

    actual_daily.columns = ["day", "actual"]

    # =========================
    # TARGET HARIAN
    # =========================

    target_rows = []

    for _, row in target.iterrows():
        for day in range(1, 31):
            target_rows.append({
                "day": day,
                "target": pd.to_numeric(
                    row[str(day)],
                    errors="coerce"
                )
            })

    target_daily = pd.DataFrame(target_rows)

    target_daily["target"] = (
        target_daily["target"]
        .fillna(0)
    )

    target_daily = (
        target_daily
        .groupby("day", as_index=False)["target"]
        .sum()
    )

    # =========================
    # GABUNGKAN
    # =========================

    daily = target_daily.merge(
        actual_daily,
        on="day",
        how="left"
    )

    daily["actual"] = daily["actual"].fillna(0)

    # Achievement
    daily["achievement"] = (
        daily["actual"]
        .div(daily["target"].replace(0, pd.NA))
        .mul(100)
    )

    # Gap
    daily["gap"] = (
        daily["actual"]
        - daily["target"]
    )

    return daily


def build_agent_performance_HG(target_actual_df):
    data = target_actual_df.copy()

    # Pastikan numeric
    data["target"] = pd.to_numeric(
        data["target"],
        errors="coerce"
    ).fillna(0)

    data["actual"] = pd.to_numeric(
        data["actual"],
        errors="coerce"
    ).fillna(0)

    # Achievement
    data["achievement"] = (
        data["actual"]
        .div(data["target"].replace(0, pd.NA))
        .mul(100)
    )

    # Gap
    data["gap"] = (
        data["actual"]
        - data["target"]
    )

    # Status performance
    data["performance_status"] = pd.cut(
        data["achievement"],
        bins=[-float("inf"), 80, 100, float("inf")],
        labels=[
            "Below Target",
            "Near Target",
            "Achieved"
        ],
        right=False
    )

    # Ranking berdasarkan achievement
    data["rank"] = (
        data["achievement"]
        .rank(
            ascending=False,
            method="min"
        )
        .astype(int)
    )

    # Rapikan urutan
    data = data.sort_values(
        "rank"
    ).reset_index(drop=True)

    return data
