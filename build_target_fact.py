from build_transaction_fact import load_sheet
import pandas as pd


def build_target_fact(target: pd.DataFrame) -> pd.DataFrame:
    """
    Mengubah TARGET AGENT dari format wide:

        Agent | ... | 1 | 2 | 3 | ... | 30

    menjadi format long:

        company
        agent
        role
        team_leader
        tier
        target_date
        daily_target
    """

    target = target.copy()

    # ============================================================
    # 1. NORMALISASI NAMA KOLOM
    # ============================================================

    target.columns = [
        str(col).strip()
        for col in target.columns
    ]

    target = target.rename(
        columns={
            "Company": "company",
            "Nama Agent": "agent",
            "Role": "role",
            "Nama Team Leader": "team_leader",
            "Tier": "tier",
        }
    )

    # ============================================================
    # 2. IDENTIFIKASI KOLOM TARGET HARIAN
    # ============================================================

    base_columns = [
        "company",
        "agent",
        "role",
        "team_leader",
        "tier",
    ]

    date_columns = [
        str(day)
        for day in range(1, 31)
        if str(day) in target.columns
    ]

    if len(date_columns) == 0:
        raise ValueError(
            "Tidak ditemukan kolom target harian 1-30."
        )

    print(
        f"Target columns ditemukan : "
        f"{len(date_columns)} hari"
    )

    # ============================================================
    # 3. WIDE -> LONG
    # ============================================================

    target_fact = target.melt(
        id_vars=base_columns,
        value_vars=date_columns,
        var_name="day",
        value_name="daily_target",
    )

    # ============================================================
    # 4. NORMALISASI DATA
    # ============================================================

    target_fact["company"] = (
        target_fact["company"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    target_fact["agent"] = (
        target_fact["agent"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    target_fact["role"] = (
        target_fact["role"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    target_fact["team_leader"] = (
        target_fact["team_leader"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    target_fact["tier"] = (
        target_fact["tier"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # ============================================================
    # 5. TARGET NUMERIC
    # ============================================================

    target_fact["daily_target"] = pd.to_numeric(
        target_fact["daily_target"],
        errors="coerce",
    ).fillna(0)

    target_fact["day"] = pd.to_numeric(
        target_fact["day"],
        errors="coerce",
    )

    # ============================================================
    # 6. TARGET DATE
    # ============================================================

    target_fact["target_date"] = pd.to_datetime(
        {
            "year": 2026,
            "month": 10,
            "day": target_fact["day"],
        },
        errors="coerce",
    )

    # ============================================================
    # 7. FILTER ROW TANPA AGENT
    # ============================================================

    empty_agent_mask = target_fact["agent"].eq("")

    empty_agent_rows = target_fact.loc[
        empty_agent_mask
    ].copy()

    if len(empty_agent_rows) > 0:
        print(
            "\nWARNING:"
        )

        print(
            f"Ditemukan {len(empty_agent_rows):,} "
            "target rows tanpa nama agent."
        )

        print(
            "Row tersebut akan dikeluarkan dari "
            "Target Fact."
        )

        print(
            f"Raw target rows yang dikeluarkan : "
            f"{empty_agent_rows['agent'].shape[0]:,}"
        )

        print(
            f"Target rows setelah filter : "
            f"{(~empty_agent_mask).sum():,}"
        )

        target_fact = target_fact.loc[
            ~empty_agent_mask
        ].copy()

    # ============================================================
    # 8. VALIDASI TANGGAL
    # ============================================================

    invalid_date = target_fact[
        target_fact["target_date"].isna()
    ]

    if len(invalid_date) > 0:
        raise ValueError(
            f"Ditemukan {len(invalid_date)} target "
            "dengan tanggal tidak valid."
        )

    # ============================================================
    # 9. SORT
    # ============================================================

    target_fact = target_fact.sort_values(
        by=[
            "target_date",
            "company",
            "agent",
        ]
    ).reset_index(drop=True)

    # ============================================================
    # 10. TARGET ID
    # ============================================================

    target_fact["target_id"] = (
        target_fact["company"]
        + "|"
        + target_fact["agent"]
        + "|"
        + target_fact["target_date"]
        .dt.strftime("%Y-%m-%d")
    )

    # ============================================================
    # 11. COLUMN ORDER
    # ============================================================

    target_fact = target_fact[
        [
            "target_id",
            "company",
            "agent",
            "role",
            "team_leader",
            "tier",
            "target_date",
            "day",
            "daily_target",
        ]
    ]

    return target_fact


def print_target_audit(
    target_fact: pd.DataFrame,
):

    print("\n===== TARGET FACT =====")

    print(
        f"Total rows : "
        f"{len(target_fact):,}"
    )

    print(
        f"Unique agent : "
        f"{target_fact['agent'].nunique():,}"
    )

    print(
        f"Unique company : "
        f"{target_fact['company'].nunique():,}"
    )

    print(
        f"Date range : "
        f"{target_fact['target_date'].min().date()} "
        f"→ "
        f"{target_fact['target_date'].max().date()}"
    )

    print("\n===== TARGET BY COMPANY =====")

    print(
        target_fact
        .groupby("company")
        .agg(
            agents=("agent", "nunique"),
            rows=("target_id", "count"),
            total_target=("daily_target", "sum"),
        )
        .to_string()
    )

    print("\n===== TARGET BY TIER =====")

    print(
        target_fact
        .groupby("tier")
        .agg(
            agents=("agent", "nunique"),
            total_target=("daily_target", "sum"),
        )
        .to_string()
    )

    print("\n===== SAMPLE =====")

    print(
        target_fact.head(15).to_string(
            index=False
        )
    )

    print("\n===== VALIDATION =====")

    duplicate_target = target_fact.duplicated(
        subset=[
            "company",
            "agent",
            "target_date",
        ],
        keep=False,
    )

    print(
        "Duplicate company + agent + date : "
        f"{duplicate_target.sum()}"
    )

    missing_target = (
        target_fact["daily_target"]
        .isna()
        .sum()
    )

    print(
        "Missing target : "
        f"{missing_target}"
    )


def main():

    print("Loading TARGET AGENT...")

    target = load_sheet(
        "TARGET AGENT"
    )

    print(
        f"TARGET AGENT : "
        f"{len(target):,} rows"
    )

    print("\nBuilding target fact...")

    target_fact = build_target_fact(
        target
    )

    print_target_audit(
        target_fact
    )


if __name__ == "__main__":
    main()
