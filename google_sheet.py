import os
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


CREDENTIALS_FILE = "moonlit-casing-510516-n8-3fc64142db30.json"

SPREADSHEET_ID = "1E9o8a2v5vH7ij1s4vHfok3PADgo0Ep29YVSqRfdWOOc"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]


def connect_google_sheet():

    # =========================================================
    # LOCAL
    # =========================================================

    if os.path.exists(CREDENTIALS_FILE):

        credentials = Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=SCOPES
        )

    # =========================================================
    # STREAMLIT CLOUD
    # =========================================================

    else:

        credentials_info = dict(
            st.secrets["gcp_service_account"]
        )

        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    return spreadsheet


def get_sales_hg():
    spreadsheet = connect_google_sheet()

    worksheet = spreadsheet.worksheet("SALES HG")

    data = worksheet.get_all_records()

    return data


def inspect_sales_hg():
    import pandas as pd

    data = get_sales_hg()

    df = pd.DataFrame(data)

    print("\n=== 5 BARIS PERTAMA ===")
    print(df.head().to_string())

    print("\n=== TIPE DATA ===")
    print(df.dtypes)

    print("\n=== JUMLAH DATA KOSONG ===")
    print(df.isna().sum())


def inspect_sales_hg_categories():
    import pandas as pd

    data = get_sales_hg()
    df = pd.DataFrame(data)

    columns = [
        "status",
        "trx_type",
        "sub_trx_type",
        "is_waive",
        "cs_status"
    ]

    for column in columns:
        print(f"\n=== {column.upper()} ===")

        values = df[column].value_counts(dropna=False)

        print(values.to_string())


def get_sales_bk():
    spreadsheet = connect_google_sheet()

    worksheet = spreadsheet.worksheet("SALES BK")

    data = worksheet.get_all_records()

    return data


def inspect_sales_bk():
    import pandas as pd

    data = get_sales_bk()

    df = pd.DataFrame(data)

    print("\n=== SALES BK ===")
    print("JUMLAH BARIS:", len(df))
    print("JUMLAH KOLOM:", len(df.columns))

    print("\n=== KOLOM ===")
    print(list(df.columns))

    print("\n=== 5 BARIS PERTAMA ===")
    print(df.head().to_string())


def compare_sales_columns():
    hg = get_sales_hg()
    bk = get_sales_bk()

    hg_columns = set(hg[0].keys())
    bk_columns = set(bk[0].keys())

    print("\n=== HANYA ADA DI HG ===")
    print(hg_columns - bk_columns)

    print("\n=== HANYA ADA DI BK ===")
    print(bk_columns - hg_columns)


def inspect_id_row_distribution():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:
        id_counts = df.groupby("id").size()

        print(f"\n=== {name} ===")
        print("Jumlah baris:", len(df))
        print("Jumlah ID unik:", id_counts.size)

        print("\nDistribusi jumlah baris per ID:")
        print(id_counts.value_counts().sort_index().to_string())

        print("\nID dengan jumlah baris terbanyak:")
        print(id_counts.sort_values(ascending=False).head(10).to_string())


def inspect_id_invoice_relationship():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:
        invoice_per_id = (
            df.groupby("id")["invoice_no"]
            .nunique()
        )

        multiple_invoices = invoice_per_id[invoice_per_id > 1]

        print(f"\n=== {name} ===")
        print("Total ID unik:", invoice_per_id.size)
        print("ID dengan lebih dari 1 invoice:", len(multiple_invoices))

        if len(multiple_invoices) > 0:
            print("\nContoh:")
            print(multiple_invoices.head(10).to_string())


def inspect_one_id_rows():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:
        id_counts = df.groupby("id").size()
        sample_id = id_counts[id_counts == 4].index[0]

        print(f"\n=== {name} ===")
        print("Contoh ID:", sample_id)
        print("\nData lengkap:")
        print(
            df[df["id"] == sample_id]
            .to_string(index=False)
        )


def inspect_transaction_header_distribution():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    columns = [
        "total",
        "amount",
        "payment_total",
        "payment_date",
        "TGL BAYAR"
    ]

    for name, df in [("HG", hg), ("BK", bk)]:
        print(f"\n=== {name} ===")

        for column in columns:
            non_empty = (
                df[column]
                .astype(str)
                .str.strip()
                .ne("")
            )

            per_id = (
                df.assign(_filled=non_empty)
                .groupby("id")["_filled"]
                .sum()
            )

            print(f"\n{column}")
            print(per_id.value_counts().sort_index().to_string())


def inspect_id_value_variation():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    columns = [
        "total",
        "amount",
        "payment_total",
        "payment_date",
        "TGL BAYAR"
    ]

    for name, df in [("HG", hg), ("BK", bk)]:
        print(f"\n=== {name} ===")

        for column in columns:
            temp = df.copy()

            temp[column] = (
                temp[column]
                .astype(str)
                .str.strip()
            )

            temp = temp[temp[column] != ""]

            unique_values = (
                temp.groupby("id")[column]
                .nunique()
            )

            multiple_values = unique_values[unique_values > 1]

            print(
                f"{column}: "
                f"{len(multiple_values)} ID memiliki >1 nilai berbeda"
            )

            if len(multiple_values) > 0:
                print(
                    multiple_values
                    .sort_values(ascending=False)
                    .head(5)
                    .to_string()
                )


def inspect_amount_variation():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:

        temp = df.copy()
        temp["amount_clean"] = (
            temp["amount"]
            .astype(str)
            .str.strip()
        )

        variation = (
            temp[temp["amount_clean"] != ""]
            .groupby("id")["amount_clean"]
            .nunique()
        )

        ids = variation[variation > 1].index

        print(f"\n=== {name} ===")

        if len(ids) == 0:
            print("Tidak ada variasi amount.")
            continue

        sample_id = ids[0]

        print("Contoh ID:", sample_id)
        print()

        columns = [
            "id",
            "invoice_no",
            "tanggal",
            "total",
            "kodeunik",
            "amount",
            "payment_total",
            "payment_date",
            "is_waive",
            "trx_type",
            "sub_trx_type",
            "package",
            "program",
            "qty_meal",
            "qty_juice",
            "qty_cutlery",
            "started_at",
            "sales",
            "purpose",
            "TGL BAYAR"
        ]

        print(
            df[df["id"] == sample_id][columns]
            .to_string(index=False)
        )


def inspect_total_variation_hg():
    import pandas as pd

    df = pd.DataFrame(get_sales_hg())

    df["total_clean"] = (
        df["total"]
        .astype(str)
        .str.replace("Rp", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )

    variation = (
        df[df["total_clean"] != ""]
        .groupby("id")["total_clean"]
        .nunique()
    )

    ids = variation[variation > 1].index

    print("ID dengan total berbeda:", list(ids))

    columns = [
        "id",
        "invoice_no",
        "tanggal",
        "total",
        "kodeunik",
        "amount",
        "payment_total",
        "payment_date",
        "is_waive",
        "trx_type",
        "sub_trx_type",
        "package",
        "program",
        "qty_meal",
        "qty_juice",
        "qty_cutlery",
        "started_at",
        "sales",
        "purpose",
        "TGL BAYAR"
    ]

    for transaction_id in ids:
        print(f"\n=== ID {transaction_id} ===")
        print(
            df[df["id"] == transaction_id][columns]
            .to_string(index=False)
        )


def inspect_payment_status_by_id():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:

        temp = df.copy()

        temp["payment_total_clean"] = (
            temp["payment_total"]
            .astype(str)
            .str.replace("Rp", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip()
        )

        per_id = (
            temp.groupby("id")["payment_total_clean"]
            .apply(
                lambda x: any(
                    value != "" and value.lower() != "nan"
                    for value in x
                )
            )
        )

        print(f"\n=== {name} ===")
        print("ID unik:", len(per_id))
        print("ID dengan payment_total:", int(per_id.sum()))
        print("ID tanpa payment_total:", int((~per_id).sum()))


def inspect_status_by_id():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:

        status_per_id = (
            df.groupby("id")["status"]
            .apply(lambda x: sorted(set(
                str(value).strip()
                for value in x
                if str(value).strip()
            )))
        )

        multiple_status = status_per_id[
            status_per_id.apply(len) > 1
        ]

        print(f"\n=== {name} ===")
        print("ID unik:", len(status_per_id))
        print("ID dengan >1 status:", len(multiple_status))

        print("\nJumlah ID berdasarkan kombinasi status:")

        combinations = (
            status_per_id
            .apply(lambda x: " + ".join(x))
            .value_counts()
        )

        print(combinations.to_string())


def inspect_status_transition_examples():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:

        status_per_id = (
            df.groupby("id")["status"]
            .apply(lambda x: set(
                str(value).strip()
                for value in x
                if str(value).strip()
            ))
        )

        interesting = status_per_id[
            status_per_id.apply(
                lambda x: (
                    "success" in x
                    and (
                        "pending" in x
                        or "challenge" in x
                        or "cancel" in x
                    )
                )
            )
        ]

        print(f"\n=== {name} ===")

        for transaction_id in interesting.head(3).index:

            print(f"\n--- ID {transaction_id} ---")

            columns = [
                "id",
                "invoice_no",
                "tanggal",
                "status",
                "total",
                "amount",
                "payment_total",
                "payment_date",
                "is_waive",
                "trx_type",
                "sales",
                "TGL BAYAR"
            ]

            print(
                df[df["id"] == transaction_id][columns]
                .to_string(index=False)
            )


def inspect_status_row_order():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:

        status_per_id = (
            df.groupby("id")["status"]
            .apply(lambda x: set(
                str(value).strip()
                for value in x
                if str(value).strip()
            ))
        )

        interesting = status_per_id[
            status_per_id.apply(
                lambda x: len(x) > 1
                and "success" in x
            )
        ]

        print(f"\n=== {name} ===")

        for transaction_id in interesting.head(5).index:

            print(f"\n--- ID {transaction_id} ---")

            temp = df[df["id"] == transaction_id].copy()

            temp["row_order"] = range(1, len(temp) + 1)

            columns = [
                "row_order",
                "status",
                "payment_total",
                "payment_date",
                "TGL BAYAR"
            ]

            print(
                temp[columns]
                .to_string(index=False)
            )


def inspect_success_completeness():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:

        success = df[
            df["status"].astype(str).str.strip().str.lower() == "success"
        ].copy()

        success_per_id = success.groupby("id").agg(
            jumlah_success=("id", "size"),
            payment_total_terisi=(
                "payment_total",
                lambda x: sum(str(v).strip() != "" for v in x)
            ),
            payment_date_terisi=(
                "payment_date",
                lambda x: sum(str(v).strip() != "" for v in x)
            ),
            amount_terisi=(
                "amount",
                lambda x: sum(str(v).strip() != "" for v in x)
            )
        )

        print(f"\n=== {name} ===")
        print("Jumlah ID dengan success:", len(success_per_id))

        print(
            "\nID success yang TIDAK punya payment_total:"
        )
        print(
            (success_per_id["payment_total_terisi"] == 0).sum()
        )

        print(
            "\nID success yang TIDAK punya payment_date:"
        )
        print(
            (success_per_id["payment_date_terisi"] == 0).sum()
        )

        print(
            "\nID success yang TIDAK punya amount:"
        )
        print(
            (success_per_id["amount_terisi"] == 0).sum()
        )

        print("\nContoh ID yang payment_total-nya tidak terisi:")
        print(
            success_per_id[
                success_per_id["payment_total_terisi"] == 0
            ].head(10).to_string()
        )


def inspect_success_without_payment():
    import pandas as pd

    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:

        success = df[
            df["status"].astype(str).str.strip().str.lower() == "success"
        ].copy()

        success_without_payment = success[
            success["payment_total"].astype(str).str.strip() == ""
        ]

        # Ambil satu row per ID untuk melihat karakter transaksinya
        sample = (
            success_without_payment
            .groupby("id", as_index=False)
            .first()
        )

        print(f"\n=== {name} ===")
        print("Jumlah ID success tanpa payment:", sample["id"].nunique())

        columns = [
            "id",
            "invoice_no",
            "trx_type",
            "sub_trx_type",
            "is_waive",
            "package",
            "program",
            "total",
            "amount",
            "payment_total",
            "payment_date",
            "status"
        ]

        print("\nDistribusi trx_type:")
        print(
            sample["trx_type"]
            .astype(str)
            .str.strip()
            .value_counts(dropna=False)
            .to_string()
        )

        print("\nDistribusi is_waive:")
        print(
            sample["is_waive"]
            .astype(str)
            .str.strip()
            .value_counts(dropna=False)
            .to_string()
        )

        print("\nContoh data:")
        print(
            sample[columns]
            .head(20)
            .to_string(index=False)
        )


def inspect_success_without_payment_by_trx_type():
    import pandas as pd
    hg = get_sales_hg()
    bk = get_sales_bk()

    for name, data in [("HG", hg), ("BK", bk)]:
        df = pd.DataFrame(data)

        # Ambil transaksi yang punya status success
        # tetapi payment_total kosong
        success_df = df[
            (df["status"].astype(str).str.lower() == "success")
            & (
                df["payment_total"].isna()
                | (df["payment_total"].astype(str).str.strip() == "")
            )
        ].copy()

        print(f"\n=== {name} ===")
        print("Jumlah ROW:", len(success_df))
        print("Jumlah ID unik:", success_df["id"].nunique())

        print("\n=== DISTRIBUSI TRX_TYPE ===")
        print(success_df["trx_type"].value_counts(dropna=False))

        print("\n=== DISTRIBUSI IS_WAIVE ===")
        print(success_df["is_waive"].value_counts(dropna=False))

        print("\n=== KOMBINASI TRX_TYPE + IS_WAIVE ===")
        print(
            success_df.groupby(
                ["trx_type", "is_waive"],
                dropna=False
            )["id"]
            .nunique()
            .sort_values(ascending=False)
        )

        print("\n=== TOTAL ===")
        print(
            success_df.groupby("trx_type", dropna=False)["total"]
            .agg(["count", "nunique"])
        )

        print("\n=== CONTOH DATA ===")
        columns = [
            "id",
            "invoice_no",
            "trx_type",
            "sub_trx_type",
            "status",
            "is_waive",
            "total",
            "amount",
            "payment_total",
            "payment_date",
            "package",
            "program",
            "sales",
        ]

        print(success_df[columns].head(20).to_string(index=False))


def inspect_success_without_payment_detail():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:

        print(f"\n{'=' * 60}")
        print(f"=== {name} ===")
        print(f"{'=' * 60}")

        # ID yang memiliki minimal satu row success
        success_ids = df[
            df["status"].astype(str).str.lower().eq("success")
        ]["id"].unique()

        success_df = df[df["id"].isin(success_ids)].copy()

        # Ambil ID yang TIDAK memiliki payment_total sama sekali
        payment_filled = (
            success_df["payment_total"]
            .astype(str)
            .str.strip()
            .ne("")
        )

        ids_with_payment = success_df.loc[
            payment_filled, "id"
        ].unique()

        target = success_df[
            ~success_df["id"].isin(ids_with_payment)
        ].copy()

        # Satu baris per ID
        result = (
            target.groupby("id")
            .agg(
                invoice_no=("invoice_no", "first"),
                trx_type=("trx_type", "first"),
                sub_trx_type=("sub_trx_type", "first"),
                status=("status", "last"),
                total=("total", "last"),
                amount=("amount", "last"),
                payment_total=("payment_total", "last"),
                payment_date=("payment_date", "last"),
                is_waive=("is_waive", "first"),
                tgl_bayar=("TGL BAYAR", "last"),
                package=("package", "first"),
                program=("program", "first"),
                sales=("sales", "first"),
            )
            .reset_index()
        )

        print("\nJumlah ID:", len(result))

        print("\n=== TRX TYPE ===")
        print(
            result["trx_type"]
            .value_counts(dropna=False)
        )

        print("\n=== IS_WAIVE ===")
        print(
            result["is_waive"]
            .value_counts(dropna=False)
        )

        print("\n=== TGL BAYAR TERISI ===")
        print(
            result["tgl_bayar"]
            .astype(str)
            .str.strip()
            .ne("")
            .value_counts()
        )

        print("\n=== PAYMENT DATE TERISI ===")
        print(
            result["payment_date"]
            .astype(str)
            .str.strip()
            .ne("")
            .value_counts()
        )

        print("\n=== CONTOH REGULER ===")
        print(
            result[
                result["trx_type"].astype(str).str.lower() == "reguler"
            ]
            .head(20)
            .to_string(index=False)
        )

        print("\n=== CONTOH COMPANY ===")
        print(
            result[
                result["trx_type"].astype(str).str.lower() == "company"
            ]
            .head(20)
            .to_string(index=False)
        )


def inspect_duplicate_id():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:
        print("\n" + "=" * 60)
        print(f"=== {name} ===")
        print("=" * 60)

        counts = (
            df.groupby("id")
            .size()
            .sort_values(ascending=False)
        )

        print("\n=== JUMLAH ROW PER ID ===")
        print(counts.head(20))

        print("\nJumlah ID unik:", df["id"].nunique())
        print("Jumlah ID dengan >1 row:", (counts > 1).sum())


def inspect_one_id():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())

    sample_id = 101250

    result = hg[hg["id"] == sample_id].copy()

    print("\n" + "=" * 60)
    print(f"=== DETAIL ID {sample_id} ===")
    print("=" * 60)

    print("Jumlah row:", len(result))

    columns = [
        "id",
        "invoice_no",
        "trx_type",
        "sub_trx_type",
        "status",
        "total",
        "amount",
        "payment_total",
        "payment_date",
        "is_waive",
        "tgl_bayar",
        "package",
        "program",
        "sales",
    ]

    available_columns = [
        col for col in columns
        if col in result.columns
    ]

    print(
        result[available_columns]
        .to_string(index=False)
    )


def inspect_invoice_id_relationship():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())
    bk = pd.DataFrame(get_sales_bk())

    for name, df in [("HG", hg), ("BK", bk)]:
        print("\n" + "=" * 60)
        print(f"=== {name} ===")
        print("=" * 60)

        relationship = (
            df.groupby("invoice_no")["id"]
            .nunique()
            .sort_values(ascending=False)
        )

        print("\n=== JUMLAH ID PER INVOICE ===")
        print(relationship.head(20))

        print("\nJumlah invoice unik:", df["invoice_no"].nunique())

        print(
            "Invoice dengan >1 ID:",
            (relationship > 1).sum()
        )


def inspect_one_invoice():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())

    sample_invoice = "INVE84F1948"

    result = hg[hg["invoice_no"] == sample_invoice].copy()

    print("\n" + "=" * 60)
    print(f"=== DETAIL INVOICE {sample_invoice} ===")
    print("=" * 60)

    print("Jumlah row:", len(result))

    for col in result.columns:
        unique_values = result[col].drop_duplicates()

        if len(unique_values) > 1:
            print(f"\n--- {col} ({len(unique_values)} nilai unik) ---")
            print(unique_values.to_string(index=False))


def inspect_customer_invoice_relationship():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())

    result = (
        hg.groupby("phone_number")["invoice_no"]
        .nunique()
        .sort_values(ascending=False)
    )

    print("\n" + "=" * 60)
    print("=== CUSTOMER → INVOICE RELATIONSHIP (HG) ===")
    print("=" * 60)

    print("\n=== TOP CUSTOMER DENGAN INVOICE TERBANYAK ===")
    print(result.head(20))

    print("\nJumlah customer/phone unik:", hg["phone_number"].nunique())

    print(
        "Customer dengan >1 invoice:",
        (result > 1).sum()
    )


def inspect_invoice_financial_consistency():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())

    sample_invoices = (
        hg["invoice_no"]
        .drop_duplicates()
        .head(20)
        .tolist()
    )

    columns = [
        "invoice_no",
        "id",
        "status",
        "total",
        "amount",
        "payment_total",
        "payment_date",
        "is_waive",
        "TGL BAYAR",
    ]

    print("\n" + "=" * 70)
    print("=== KONSISTENSI NILAI TRANSAKSI PER INVOICE ===")
    print("=" * 70)

    for invoice in sample_invoices:
        result = hg[hg["invoice_no"] == invoice][columns].drop_duplicates()

        print(f"\n--- INVOICE: {invoice} ---")
        print("Jumlah row:", len(hg[hg["invoice_no"] == invoice]))
        print(result.to_string(index=False))


def inspect_payment_total_variation():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())

    variation = (
        hg.groupby("invoice_no")["payment_total"]
        .nunique()
        .sort_values(ascending=False)
    )

    print("\n" + "=" * 60)
    print("=== VARIASI PAYMENT TOTAL PER INVOICE ===")
    print("=" * 60)

    print("Invoice dengan >1 payment_total berbeda:", (variation > 1).sum())

    print("\nInvoice yang punya variasi:")
    print(variation[variation > 1].head(20))


def inspect_payment_variation_detail():
    import pandas as pd
    hg = pd.DataFrame(get_sales_hg())

    invoice = "INV77996A71"

    result = hg[hg["invoice_no"] == invoice].copy()

    columns = [
        "invoice_no",
        "id",
        "status",
        "total",
        "amount",
        "payment_total",
        "payment_date",
        "is_waive",
        "TGL BAYAR",
    ]

    print("\n" + "=" * 60)
    print(f"=== PAYMENT VARIATION: {invoice} ===")
    print("=" * 60)

    print(result[columns].to_string(index=False))
