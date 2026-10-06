import pandas as pd

from google_sheet import connect_google_sheet


START_DATE = pd.Timestamp("2026-10-01")


def load_sheet(sheet_name: str) -> pd.DataFrame:
    """Load seluruh data dari satu worksheet."""
    sheet = connect_google_sheet().worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())


def normalize_text(series: pd.Series) -> pd.Series:
    """Normalisasi text untuk kebutuhan matching."""
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
    )


def prepare_target_agent(target: pd.DataFrame) -> pd.DataFrame:
    """Prepare master agent dari TARGET AGENT."""

    target = target.copy()

    text_columns = [
        "Company",
        "Nama Agent",
        "Role",
        "Nama Team Leader",
        "Tier",
    ]

    for column in text_columns:
        target[column] = normalize_text(target[column])

    # Case-insensitive matching key.
    target["agent_key"] = (
        target["Nama Agent"]
        .str.casefold()
    )

    return target


def prepare_sales(
    df: pd.DataFrame,
    brand: str,
) -> pd.DataFrame:
    """
    Prepare raw sales data tanpa menghilangkan kolom.
    """

    df = df.copy()

    # ---------------------------------------------------------
    # 1. BRAND
    # ---------------------------------------------------------

    df["brand"] = brand

    # ---------------------------------------------------------
    # 2. NORMALISASI TEXT
    # ---------------------------------------------------------

    for column in [
        "invoice_no",
        "sales",
        "status",
        "trx_type",
        "sub_trx_type",
    ]:
        df[column] = normalize_text(df[column])

    # ---------------------------------------------------------
    # 3. PARSE DATE
    # ---------------------------------------------------------

    df["tanggal"] = pd.to_datetime(
        df["tanggal"],
        errors="coerce",
    )

    df["payment_date"] = pd.to_datetime(
        df["payment_date"],
        errors="coerce",
    )

    return df


def build_transaction_fact(
    df: pd.DataFrame,
    target: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build 1 transaction fact per brand + invoice_no.

    Business rule:
    - 1 transaction = 1 brand + 1 invoice_no.
    - Status terakhir/current digunakan sebagai status_final.
    - Raw fields tetap dipertahankan.
    - Agent dimapping berdasarkan TARGET AGENT.
    """

    df = df.copy()

    # =========================================================
    # 1. TRANSACTION KEY
    # =========================================================

    df["transaction_key"] = (
        df["brand"].astype(str).str.strip()
        + "|"
        + df["invoice_no"].astype(str).str.strip()
    )

    # =========================================================
    # 2. ORIGINAL ROW ORDER
    # =========================================================

    df["_row_order"] = range(len(df))

    # =========================================================
    # 3. SORT TRANSACTION LIFECYCLE
    # =========================================================

    df = df.sort_values(
        by=[
            "transaction_key",
            "tanggal",
            "payment_date",
            "_row_order",
        ],
        na_position="first",
    )

    # =========================================================
    # 4. LATEST ROW = CURRENT TRANSACTION STATE
    # =========================================================

    fact = (
        df.groupby(
            "transaction_key",
            as_index=False,
        )
        .last()
    )

    fact["status_final"] = fact["status"]

    # =========================================================
    # 5. AGENT MAPPING
    # =========================================================

    target_mapping = (
        target[
            [
                "agent_key",
                "Nama Agent",
                "Company",
                "Role",
                "Nama Team Leader",
                "Tier",
            ]
        ]
        .drop_duplicates("agent_key")
    )

    fact["agent_key"] = (
        fact["sales"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    fact = fact.merge(
        target_mapping,
        on="agent_key",
        how="left",
        suffixes=("", "_target"),
    )

    # =========================================================
    # 6. MAPPING STATUS
    # =========================================================

    fact["mapping_status"] = fact["Nama Agent"].apply(
        lambda x: (
            "mapped"
            if pd.notna(x) and str(x).strip()
            else "unmapped"
        )
    )

    # =========================================================
    # 7. PERFORMANCE DATE
    # =========================================================

    fact["performance_date"] = pd.NaT

    success_mask = (
        fact["status_final"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .eq("success")
    )

    unpaid_mask = (
        fact["status_final"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .isin(
            [
                "pending",
                "challenge",
            ]
        )
    )

    # Paid → payment_date.
    fact.loc[
        success_mask,
        "performance_date",
    ] = fact.loc[
        success_mask,
        "payment_date",
    ]

    # Unpaid → tanggal invoice.
    fact.loc[
        unpaid_mask,
        "performance_date",
    ] = fact.loc[
        unpaid_mask,
        "tanggal",
    ]

    # Cancel → tidak masuk performance.
    fact.loc[
        fact["status_final"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .eq("cancel"),
        "performance_date",
    ] = pd.NaT

    # Normalize ke tanggal saja.
    fact["performance_date"] = pd.to_datetime(
        fact["performance_date"],
        errors="coerce",
    ).dt.normalize()

    # =========================================================
    # 8. DASHBOARD STATUS
    # =========================================================

    fact["dashboard_status"] = (
        fact["status_final"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .map(
            {
                "success": "paid",
                "pending": "unpaid",
                "challenge": "unpaid",
                "cancel": "cancel",
            }
        )
    )

    # =========================================================
    # 9. AGENT DISPLAY
    # =========================================================

    def clean_value(value):
        if pd.isna(value):
            return ""

        return str(value).strip()

    fact["agent_display"] = (
        fact["Nama Agent"].apply(clean_value)
        + " · Tier "
        + fact["Tier"].apply(clean_value)
        + " · "
        + fact["Role"].apply(clean_value)
        + " · TL: "
        + fact["Nama Team Leader"].apply(clean_value)
    )

    # Untuk agent yang belum termapping,
    # jangan menghasilkan string informasi kosong yang panjang.
    fact.loc[
        fact["mapping_status"] == "unmapped",
        "agent_display",
    ] = fact.loc[
        fact["mapping_status"] == "unmapped",
        "sales",
    ].apply(clean_value)

    # =========================================================
    # 10. NUMERIC REVENUE FIELDS
    # =========================================================

    fact["payment_total"] = pd.to_numeric(
        fact["payment_total"],
        errors="coerce",
    )

    fact["amount"] = pd.to_numeric(
        fact["amount"],
        errors="coerce",
    )

    # Revenue dasar:
    # payment_total → fallback amount.
    fact["invoice_revenue"] = (
        fact["payment_total"]
        .fillna(fact["amount"])
        .fillna(0)
    )

    # =========================================================
    # 11. CLEAN HELPER
    # =========================================================

    fact = fact.drop(
        columns=["_row_order"],
        errors="ignore",
    )

    return fact


def main():

    print("Loading Google Sheets...")

    # =========================================================
    # LOAD RAW
    # =========================================================

    target = load_sheet("TARGET AGENT")
    hg = load_sheet("SALES HG OCT")
    bk = load_sheet("SALES BK OCT")

    print(
        f"TARGET AGENT : {len(target):,} rows"
    )

    print(
        f"HG RAW       : {len(hg):,} rows"
    )

    print(
        f"BK RAW       : {len(bk):,} rows"
    )

    # =========================================================
    # DATE AUDIT
    # =========================================================

    print("\n===== DATE AUDIT =====")

    for name, data in [
        ("HG", hg),
        ("BK", bk),
    ]:

        temp = data.copy()

        temp["tanggal_check"] = pd.to_datetime(
            temp["tanggal"],
            errors="coerce",
        )

        temp["payment_date_check"] = pd.to_datetime(
            temp["payment_date"],
            errors="coerce",
        )

        before_oct = temp[
            temp["tanggal_check"] < START_DATE
        ]

        payment_oct = before_oct[
            before_oct["payment_date_check"] >= START_DATE
        ]

        print(f"\n{name}")

        print(
            f"Rows tanggal < 1 Okt : "
            f"{len(before_oct):,}"
        )

        print(
            f"Invoice tanggal < Okt + payment Okt : "
            f"{payment_oct['invoice_no'].nunique():,}"
        )

    # =========================================================
    # PREPARE DATA
    # =========================================================

    target = prepare_target_agent(target)

    hg = prepare_sales(
        hg,
        "Healthy Go",
    )

    bk = prepare_sales(
        bk,
        "Bekelin",
    )

    # =========================================================
    # BUILD TRANSACTION FACT
    # =========================================================

    print("\n===== BUILD TRANSACTION FACT =====")

    hg_fact = build_transaction_fact(
        hg,
        target,
    )

    bk_fact = build_transaction_fact(
        bk,
        target,
    )

    fact = pd.concat(
        [
            hg_fact,
            bk_fact,
        ],
        ignore_index=True,
    )

    # =========================================================
    # RESULT
    # =========================================================

    print("\n===== TRANSACTION FACT =====")

    print(
        f"Total transaction : "
        f"{len(fact):,}"
    )

    # =========================================================
    # BRAND
    # =========================================================

    print("\n===== BRAND =====")

    print(
        fact["brand"]
        .value_counts()
        .to_string()
    )

    # =========================================================
    # FINAL STATUS
    # =========================================================

    print("\n===== FINAL STATUS =====")

    print(
        fact["status_final"]
        .value_counts(dropna=False)
        .to_string()
    )

    # =========================================================
    # DASHBOARD STATUS
    # =========================================================

    print("\n===== DASHBOARD STATUS =====")

    print(
        fact["dashboard_status"]
        .value_counts(dropna=False)
        .to_string()
    )

    # =========================================================
    # MAPPING
    # =========================================================

    print("\n===== MAPPING =====")

    print(
        fact["mapping_status"]
        .value_counts(dropna=False)
        .to_string()
    )

    # =========================================================
    # UNMAPPED SALES
    # =========================================================

    print("\n===== UNMAPPED SALES =====")

    unmapped = (
        fact.loc[
            fact["mapping_status"] == "unmapped",
            "sales",
        ]
        .value_counts()
    )

    print(
        unmapped.to_string()
    )

    # =========================================================
    # TEAM LEADER
    # =========================================================

    print("\n===== TEAM LEADER =====")

    print(
        fact["Nama Team Leader"]
        .value_counts(dropna=False)
        .to_string()
    )

    # =========================================================
    # AGENT DISPLAY
    # =========================================================

    print("\n===== AGENT DISPLAY SAMPLE =====")

    print(
        fact[
            [
                "Nama Agent",
                "Tier",
                "Role",
                "Nama Team Leader",
                "agent_display",
            ]
        ]
        .drop_duplicates()
        .head(20)
        .to_string(index=False)
    )

    # =========================================================
    # REVENUE
    # =========================================================

    print("\n===== INVOICE REVENUE =====")

    paid = fact[
        fact["dashboard_status"] == "paid"
    ]

    unpaid = fact[
        fact["dashboard_status"] == "unpaid"
    ]

    excluded = fact[
        fact["dashboard_status"] == "cancel"
    ]

    print(
        f"Paid Invoice Revenue   : Rp "
        f"{paid['invoice_revenue'].sum():,.0f}"
    )

    print(
        f"Unpaid Invoice Revenue : Rp "
        f"{unpaid['invoice_revenue'].sum():,.0f}"
    )

    print(
        f"Excluded Revenue       : Rp "
        f"{excluded['invoice_revenue'].sum():,.0f}"
    )

    # =========================================================
    # PERFORMANCE DATE
    # =========================================================

    print("\n===== PERFORMANCE DATE =====")

    date_audit = (
        fact.loc[
            fact["dashboard_status"].isin(
                [
                    "paid",
                    "unpaid",
                ]
            ),
            "performance_date",
        ]
        .value_counts()
        .sort_index()
    )

    print(
        date_audit.to_string()
    )

    # =========================================================
    # VALIDATION
    # =========================================================

    print("\n===== VALIDATION =====")

    print(
        f"HG transaction : "
        f"{len(hg_fact):,}"
    )

    print(
        f"BK transaction : "
        f"{len(bk_fact):,}"
    )

    print(
        f"TOTAL          : "
        f"{len(fact):,}"
    )

    # =========================================================
    # DUPLICATE TRANSACTION KEY
    # =========================================================

    print("\n===== DUPLICATE TRANSACTION KEY =====")

    duplicate_keys = fact[
        fact["transaction_key"].duplicated(
            keep=False
        )
    ]

    print(
        f"Duplicate rows : "
        f"{len(duplicate_keys):,}"
    )

    if len(duplicate_keys) > 0:
        print(
            duplicate_keys[
                [
                    "transaction_key",
                    "brand",
                    "invoice_no",
                ]
            ].to_string(index=False)
        )

    # =========================================================
    # STATUS LIFECYCLE AUDIT
    # =========================================================

    print("\n===== STATUS LIFECYCLE AUDIT =====")

    lifecycle = (
        fact.groupby(
            [
                "invoice_no",
                "brand",
            ]
        )["status_final"]
        .agg(list)
    )

    print(
        f"Total invoice : "
        f"{len(lifecycle):,}"
    )

    print("\nFINAL STATUS DISTRIBUTION:")

    print(
        fact["status_final"]
        .value_counts(dropna=False)
        .to_string()
    )

    # =========================================================
    # SUCCESS / UNPAID / CANCEL AUDIT
    # =========================================================

    print("\n===== SUCCESS / UNPAID AUDIT =====")

    success_count = (
        fact["status_final"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .eq("success")
        .sum()
    )

    unpaid_count = (
        fact["status_final"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .isin(
            [
                "pending",
                "challenge",
            ]
        )
        .sum()
    )

    cancel_count = (
        fact["status_final"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .eq("cancel")
        .sum()
    )

    print(
        f"PAID / SUCCESS      : "
        f"{success_count:,}"
    )

    print(
        f"UNPAID              : "
        f"{unpaid_count:,}"
    )

    print(
        f"CANCEL / EXCLUDED   : "
        f"{cancel_count:,}"
    )

    # =========================================================
    # FINAL STATUS CHECK
    # =========================================================

    print("\n===== FINAL STATUS CHECK =====")

    allowed_status = [
        "success",
        "pending",
        "challenge",
        "cancel",
    ]

    unexpected = fact[
        ~fact["status_final"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .isin(allowed_status)
    ]

    print(
        f"Unexpected status : "
        f"{len(unexpected):,}"
    )

    if len(unexpected) > 0:

        print(
            unexpected[
                [
                    "invoice_no",
                    "brand",
                    "status_final",
                    "sales",
                ]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
