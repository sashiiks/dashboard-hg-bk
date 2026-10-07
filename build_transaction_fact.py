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
    """Prepare master agent."""
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

    # Case-insensitive matching key
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
    Prepare raw sales data.

    Row tanpa invoice_no dianggap sebagai blank/template row
    dan tidak diproses sebagai transaction.
    """

    df = df.copy()

    df["brand"] = brand

    # ---------------------------------------------------------
    # NORMALISASI KOLOM TEXT UTAMA
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
    # FILTER BLANK TRANSACTION
    # ---------------------------------------------------------
    # Row yang tidak memiliki invoice_no bukan transaksi valid.
    # Biasanya berasal dari blank row/template di Google Sheet.

    df = df[
        df["invoice_no"].ne("")
    ].copy()

    # ---------------------------------------------------------
    # PARSE TANGGAL
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
    - 1 transaction = 1 brand + 1 invoice_no
    - Status terakhir/current digunakan sebagai status_final
    - Raw fields tetap dipertahankan
    """

    df = df.copy()

    # ---------------------------------------------------------
    # 1. BUAT TRANSACTION KEY
    # ---------------------------------------------------------

    df["transaction_key"] = (
        df["brand"].astype(str).str.strip()
        + "|"
        + df["invoice_no"].astype(str).str.strip()
    )

    # ---------------------------------------------------------
    # 2. SIMPAN URUTAN ASLI DATA
    # ---------------------------------------------------------
    # Digunakan sebagai tie-breaker kalau informasi waktunya
    # sama.

    df["_row_order"] = range(len(df))

    # ---------------------------------------------------------
    # 3. URUTKAN BERDASARKAN TRANSACTION + INFORMASI WAKTU
    # ---------------------------------------------------------

    df = df.sort_values(
        by=[
            "transaction_key",
            "tanggal",
            "payment_date",
            "_row_order",
        ],
        na_position="first",
    )

    # ---------------------------------------------------------
    # 4. AMBIL ROW TERAKHIR UNTUK SETIAP TRANSACTION
    # ---------------------------------------------------------

    fact = (
        df.groupby("transaction_key", as_index=False)
        .last()
    )

    # ---------------------------------------------------------
    # 5. STATUS FINAL / CURRENT STATUS
    # ---------------------------------------------------------

    fact["status_final"] = (
        fact["status"]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    # ---------------------------------------------------------
    # 6. INVOICE REVENUE
    # ---------------------------------------------------------
    #
    # Business rule:
    #
    # payment_total
    #       ↓ jika kosong
    # amount
    #       ↓ jika tetap kosong
    # 0
    #
    # Ini menjadi sumber revenue yang digunakan oleh
    # Performance Fact.

    fact["invoice_revenue"] = pd.to_numeric(
        fact["payment_total"],
        errors="coerce",
    )

    fact["invoice_revenue"] = fact[
        "invoice_revenue"
    ].fillna(
        pd.to_numeric(
            fact["amount"],
            errors="coerce",
        )
    ).fillna(0)

    # ---------------------------------------------------------
    # 7. MAPPING AGENT → TARGET AGENT
    # ---------------------------------------------------------

    target_mapping = target[
        [
            "agent_key",
            "Nama Agent",
            "Company",
            "Role",
            "Nama Team Leader",
            "Tier",
        ]
    ].drop_duplicates("agent_key")

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

    # ---------------------------------------------------------
    # 8. MAPPING STATUS
    # ---------------------------------------------------------

    fact["mapping_status"] = fact["Nama Agent"].apply(
        lambda x: (
            "mapped"
            if pd.notna(x) and str(x).strip()
            else "unmapped"
        )
    )

    # ---------------------------------------------------------
    # 9. PERFORMANCE DATE
    # ---------------------------------------------------------

    fact["performance_date"] = pd.NaT

    success_mask = (
        fact["status_final"]
        .eq("success")
    )

    unpaid_mask = (
        fact["status_final"]
        .isin(["pending", "challenge"])
    )

    fact.loc[
        success_mask,
        "performance_date",
    ] = fact.loc[
        success_mask,
        "payment_date",
    ]

    fact.loc[
        unpaid_mask,
        "performance_date",
    ] = fact.loc[
        unpaid_mask,
        "tanggal",
    ]

    # ---------------------------------------------------------
    # 10. STATUS DASHBOARD
    # ---------------------------------------------------------

    fact["dashboard_status"] = (
        fact["status_final"]
        .map(
            {
                "success": "paid",
                "pending": "unpaid",
                "challenge": "unpaid",
                "cancel": "cancel",
            }
        )
    )

    # ---------------------------------------------------------
    # 11. BERSIHKAN HELPER
    # ---------------------------------------------------------

    fact = fact.drop(
        columns=["_row_order"],
        errors="ignore",
    )

    return fact


def main():
    print("Loading Google Sheets...")

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
    # DATE AUDIT — SEBELUM FILTER 1 OKTOBER
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

    print("\n===== BRAND =====")

    print(
        fact["brand"]
        .value_counts()
        .to_string()
    )

    print("\n===== FINAL STATUS =====")

    print(
        fact["status_final"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\n===== MAPPING =====")

    print(
        fact["mapping_status"]
        .value_counts(dropna=False)
        .to_string()
    )

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

    print("\n===== TL =====")

    print(
        fact["Nama Team Leader"]
        .value_counts(dropna=False)
        .to_string()
    )

    # =========================================================
    # REVENUE AUDIT
    # =========================================================

    print("\n===== INVOICE REVENUE AUDIT =====")

    print(
        f"Invoice Revenue : "
        f"Rp{fact['invoice_revenue'].sum():,.0f}"
    )

    print(
        f"Paid Revenue    : "
        f"Rp{fact.loc[fact['status_final'].eq('success'), 'invoice_revenue'].sum():,.0f}"
    )

    print(
        f"Unpaid Revenue  : "
        f"Rp{fact.loc[fact['status_final'].isin(['pending', 'challenge']), 'invoice_revenue'].sum():,.0f}"
    )

    print(
        f"Cancel Revenue  : "
        f"Rp{fact.loc[fact['status_final'].eq('cancel'), 'invoice_revenue'].sum():,.0f}"
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
    # STATUS LIFECYCLE + BUSINESS RULE AUDIT
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
    # SUCCESS / UNPAID AUDIT
    # =========================================================

    print("\n===== SUCCESS / UNPAID AUDIT =====")

    success_count = (
        fact["status_final"] == "success"
    ).sum()

    unpaid_count = (
        fact["status_final"]
        .isin(
            [
                "pending",
                "challenge",
            ]
        )
    ).sum()

    cancel_count = (
        fact["status_final"] == "cancel"
    ).sum()

    print(
        f"PAID / SUCCESS       : "
        f"{success_count:,}"
    )

    print(
        f"UNPAID               : "
        f"{unpaid_count:,}"
    )

    print(
        f"CANCEL / EXCLUDED    : "
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
        ~fact["status_final"].isin(
            allowed_status
        )
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
