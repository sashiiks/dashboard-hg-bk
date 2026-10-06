import pandas as pd

from build_transaction_fact import (
    load_sheet,
    prepare_target_agent,
    prepare_sales,
    build_transaction_fact,
)


START_DATE = pd.Timestamp("2026-10-01")


def build_performance_fact(fact: pd.DataFrame) -> pd.DataFrame:
    """
    Mengubah Transaction Fact menjadi Performance Fact.

    Business rule:
    - success             -> Paid
    - pending/challenge   -> Unpaid
    - cancel              -> Excluded

    Revenue:
    - Paid   -> paid_invoice_revenue
    - Unpaid -> unpaid_invoice_revenue
    - Cancel -> 0

    Catatan:
    invoice_revenue berasal dari Transaction Fact:
    payment_total -> fallback amount.
    """

    fact = fact.copy()

    # ============================================================
    # 1. VALIDASI REQUIRED COLUMNS
    # ============================================================

    required_columns = [
        "invoice_no",
        "brand",
        "status_final",
        "tanggal",
        "payment_date",
        "payment_total",
        "amount",
        "invoice_revenue",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in fact.columns
    ]

    if missing_columns:
        raise KeyError(
            "Kolom Transaction Fact tidak ditemukan: "
            f"{missing_columns}"
        )

    # ============================================================
    # 2. NORMALISASI STATUS
    # ============================================================

    fact["status_final"] = (
        fact["status_final"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    # ============================================================
    # 3. BUSINESS STATUS
    # ============================================================

    status_map = {
        "success": "Paid",
        "pending": "Unpaid",
        "challenge": "Unpaid",
        "cancel": "Excluded",
    }

    fact["status_live"] = fact["status_final"].map(status_map)

    # ============================================================
    # 4. VALIDASI STATUS
    # ============================================================

    unexpected = fact.loc[
        fact["status_live"].isna(),
        [
            "invoice_no",
            "status_final",
        ],
    ]

    if len(unexpected) > 0:
        print("\n===== UNEXPECTED STATUS =====")
        print(
            unexpected.to_string(index=False)
        )

        raise ValueError(
            f"Ditemukan {len(unexpected)} transaction "
            "dengan status yang belum memiliki business rule."
        )

    # ============================================================
    # 5. PERFORMANCE DATE
    # ============================================================

    fact["tanggal"] = pd.to_datetime(
        fact["tanggal"],
        errors="coerce",
    )

    fact["payment_date"] = pd.to_datetime(
        fact["payment_date"],
        errors="coerce",
    )

    # Default:
    # success -> payment_date

    fact["performance_datetime"] = fact["payment_date"]

    # Unpaid:
    # pending/challenge -> tanggal

    unpaid_mask = fact["status_live"].eq("Unpaid")

    fact.loc[
        unpaid_mask,
        "performance_datetime",
    ] = fact.loc[
        unpaid_mask,
        "tanggal",
    ]

    # Excluded:
    # cancel tidak masuk performance

    excluded_mask = fact["status_live"].eq("Excluded")

    fact.loc[
        excluded_mask,
        "performance_datetime",
    ] = pd.NaT

    fact["performance_date"] = (
        fact["performance_datetime"]
        .dt.normalize()
    )

    # ============================================================
    # 6. LIVE UPDATE TIMESTAMP
    # ============================================================

    source_updated_at = pd.Timestamp.now()

    fact["source_updated_at"] = source_updated_at

    fact["source_updated_at_display"] = (
        source_updated_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    # ============================================================
    # 7. KPI FLAGS
    # ============================================================

    fact["is_paid"] = (
        fact["status_live"] == "Paid"
    )

    fact["is_unpaid"] = (
        fact["status_live"] == "Unpaid"
    )

    fact["is_excluded"] = (
        fact["status_live"] == "Excluded"
    )

    # ============================================================
    # 8. NORMALIZE PAYMENT / AMOUNT
    # ============================================================

    fact["payment_total"] = pd.to_numeric(
        fact["payment_total"],
        errors="coerce",
    )

    fact["amount"] = pd.to_numeric(
        fact["amount"],
        errors="coerce",
    )

    # ============================================================
    # 9. PERFORMANCE AMOUNT
    # ============================================================

    # Business rule:
    #
    # payment_total
    #       ↓ jika kosong
    # amount
    #
    # Dipertahankan agar KPI lama tidak berubah.

    fact["performance_amount"] = (
        fact["payment_total"]
        .fillna(fact["amount"])
        .fillna(0)
    )

    # Cancel tidak masuk KPI.

    fact.loc[
        fact["is_excluded"],
        "performance_amount",
    ] = 0

    # ============================================================
    # 10. INVOICE REVENUE
    # ============================================================

    fact["invoice_revenue"] = pd.to_numeric(
        fact["invoice_revenue"],
        errors="coerce",
    ).fillna(0)

    # ============================================================
    # 11. PAID INVOICE REVENUE
    # ============================================================

    fact["paid_invoice_revenue"] = (
        fact["invoice_revenue"].where(
            fact["is_paid"],
            0,
        )
    )

    # ============================================================
    # 12. UNPAID INVOICE REVENUE
    # ============================================================

    fact["unpaid_invoice_revenue"] = (
        fact["invoice_revenue"].where(
            fact["is_unpaid"],
            0,
        )
    )

    # ============================================================
    # 13. PERFORMANCE SCOPE
    # ============================================================

    fact["is_dashboard"] = (
        ~fact["is_excluded"]
        & fact["performance_date"].notna()
        & fact["invoice_no"].ne("")
    )

    # ============================================================
    # 14. SORT
    # ============================================================

    fact = fact.sort_values(
        by=[
            "performance_date",
            "brand",
            "invoice_no",
        ],
        na_position="last",
    ).reset_index(
        drop=True
    )

    return fact


# ============================================================
# AUDIT
# ============================================================

def print_performance_audit(
    performance: pd.DataFrame,
):
    print("\n===== PERFORMANCE FACT =====")

    print(
        f"Total transaction : "
        f"{len(performance):,}"
    )

    # ========================================================
    # LIVE STATUS
    # ========================================================

    print("\n===== LIVE STATUS =====")

    print(
        performance["status_live"]
        .value_counts(dropna=False)
    )

    # ========================================================
    # KPI SCOPE
    # ========================================================

    print("\n===== KPI SCOPE =====")

    print(
        performance["is_dashboard"]
        .value_counts(dropna=False)
    )

    # ========================================================
    # PAID
    # ========================================================

    print("\n===== PAID =====")

    print(
        f"Transactions : "
        f"{performance['is_paid'].sum():,}"
    )

    print(
        f"Performance  : Rp "
        f"{performance.loc[performance['is_paid'], 'performance_amount'].sum():,.0f}"
    )

    print(
        f"Invoice Rev  : Rp "
        f"{performance.loc[performance['is_dashboard'] & performance['is_paid'], 'paid_invoice_revenue'].sum():,.0f}"
    )

    # ========================================================
    # UNPAID
    # ========================================================

    print("\n===== UNPAID =====")

    print(
        f"Transactions : "
        f"{performance['is_unpaid'].sum():,}"
    )

    print(
        f"Performance  : Rp "
        f"{performance.loc[performance['is_unpaid'], 'performance_amount'].sum():,.0f}"
    )

    print(
        f"Invoice Rev  : Rp "
        f"{performance.loc[performance['is_dashboard'] & performance['is_unpaid'], 'unpaid_invoice_revenue'].sum():,.0f}"
    )

    # ========================================================
    # EXCLUDED
    # ========================================================

    print("\n===== EXCLUDED =====")

    print(
        f"Transactions : "
        f"{performance['is_excluded'].sum():,}"
    )

    # ========================================================
    # PERFORMANCE DATE
    # ========================================================

    print("\n===== PERFORMANCE DATE =====")

    date_audit = (
        performance.loc[
            performance["is_dashboard"],
            "performance_date",
        ]
        .value_counts()
        .sort_index()
    )

    print(
        date_audit.to_string()
    )

    # ========================================================
    # LIVE TIMESTAMP
    # ========================================================

    print("\n===== LIVE TIMESTAMP =====")

    print(
        performance[
            [
                "invoice_no",
                "status_live",
                "performance_datetime",
                "source_updated_at_display",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    # ========================================================
    # REVENUE VALIDATION
    # ========================================================

    print("\n===== REVENUE VALIDATION =====")

    dashboard_mask = performance["is_dashboard"]

    paid_revenue = (
        performance.loc[
            dashboard_mask & performance["is_paid"],
            "paid_invoice_revenue",
        ]
        .sum()
    )

    unpaid_revenue = (
        performance.loc[
            dashboard_mask & performance["is_unpaid"],
            "unpaid_invoice_revenue",
        ]
        .sum()
    )

    total_revenue = (
        performance.loc[
            dashboard_mask,
            "invoice_revenue",
        ]
        .sum()
    )

    print(
        f"Paid Invoice Revenue   : "
        f"Rp{paid_revenue:,.0f}"
    )

    print(
        f"Unpaid Invoice Revenue : "
        f"Rp{unpaid_revenue:,.0f}"
    )

    print(
        f"Total Invoice Revenue  : "
        f"Rp{total_revenue:,.0f}"
    )

    print(
        f"Paid + Unpaid          : "
        f"Rp{paid_revenue + unpaid_revenue:,.0f}"
    )

    print(
        "Revenue reconciliation : "
        f"{'OK' if total_revenue == paid_revenue + unpaid_revenue else 'CHECK'}"
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    print("\n===== FINAL VALIDATION =====")

    valid_status = performance[
        "status_live"
    ].isin(
        [
            "Paid",
            "Unpaid",
            "Excluded",
        ]
    )

    print(
        f"Unexpected status : "
        f"{(~valid_status).sum()}"
    )

    duplicate_invoice = (
        performance.duplicated(
            subset=[
                "brand",
                "invoice_no",
            ],
            keep=False,
        )
    )

    print(
        f"Duplicate brand + invoice : "
        f"{duplicate_invoice.sum()}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("Loading Google Sheets...")

    # ========================================================
    # LOAD RAW
    # ========================================================

    target = load_sheet(
        "TARGET AGENT"
    )

    hg = load_sheet(
        "SALES HG OCT"
    )

    bk = load_sheet(
        "SALES BK OCT"
    )

    print(
        f"TARGET AGENT : {len(target):,} rows"
    )

    print(
        f"HG RAW       : {len(hg):,} rows"
    )

    print(
        f"BK RAW       : {len(bk):,} rows"
    )

    # ========================================================
    # PREPARE
    # ========================================================

    target = prepare_target_agent(
        target
    )

    hg = prepare_sales(
        hg,
        "Healthy Go",
    )

    bk = prepare_sales(
        bk,
        "Bekelin",
    )

    # ========================================================
    # TRANSACTION FACT
    # ========================================================

    print(
        "\nBuilding transaction fact..."
    )

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

    # ========================================================
    # PERFORMANCE FACT
    # ========================================================

    print(
        "\nBuilding performance fact..."
    )

    performance = build_performance_fact(
        fact
    )

    # ========================================================
    # AUDIT
    # ========================================================

    print_performance_audit(
        performance
    )


if __name__ == "__main__":
    main()
