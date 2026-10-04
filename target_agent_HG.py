import pandas as pd


def normalize_name(value):
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().lower().split())


def build_target_actual_HG(target_df, transaction_df):
    target = target_df.copy()
    transactions = transaction_df.copy()

    # Rapikan nama kolom
    target.columns = target.columns.astype(str).str.strip()
    transactions.columns = transactions.columns.str.strip()

    # Hanya target Company HG
    target = target[
        target["Company"].astype(str).str.strip().str.upper() == "HG"
    ].copy()

    # Normalisasi nama agent untuk matching
    target["_agent_key"] = target["Nama Agent"].map(normalize_name)
    transactions["_agent_key"] = transactions["sales"].map(normalize_name)

    # Pastikan tanggal transaksi benar
    transactions["tanggal"] = pd.to_datetime(
        transactions["tanggal"],
        errors="coerce"
    )

    # September 2026 + transaksi success
    transactions = transactions[
        (transactions["tanggal"].dt.year == 2026)
        & (transactions["tanggal"].dt.month == 9)
        & (transactions["final_status"] == "success")
    ].copy()

    # Pastikan total berupa angka
    transactions["total"] = pd.to_numeric(
        transactions["total"],
        errors="coerce"
    ).fillna(0)

    # Actual per agent per tanggal
    actual_daily = (
        transactions
        .groupby(
            ["_agent_key", transactions["tanggal"].dt.day],
            as_index=False
        )["total"]
        .sum()
        .rename(columns={"tanggal": "day", "total": "actual"})
    )

    # Target harian dari kolom 1-30
    target_rows = []

    for _, row in target.iterrows():
        for day in range(1, 31):
            target_rows.append({
                "_agent_key": row["_agent_key"],
                "day": day,
                "target": pd.to_numeric(
                    row[str(day)],
                    errors="coerce"
                ) if str(day) in target.columns else 0
            })

    target_daily = pd.DataFrame(target_rows)

    # Gabungkan target + actual
    daily = target_daily.merge(
        actual_daily,
        on=["_agent_key", "day"],
        how="left"
    )

    daily["actual"] = daily["actual"].fillna(0)

    # Ambil informasi agent
    agent_info = target[
        [
            "_agent_key",
            "Nama Agent",
            "Role",
            "Nama Team Leader",
            "Tier"
        ]
    ].drop_duplicates("_agent_key")

    daily = daily.merge(
        agent_info,
        on="_agent_key",
        how="left"
    )

    # Rekap per agent
    result = (
        daily
        .groupby(
            [
                "_agent_key",
                "Nama Agent",
                "Role",
                "Nama Team Leader",
                "Tier"
            ],
            as_index=False
        )
        .agg(
            target=("target", "sum"),
            actual=("actual", "sum")
        )
    )

    # Achievement
    result["achievement"] = (
        result["actual"]
        .div(result["target"].replace(0, pd.NA))
        .mul(100)
    )

    return result
