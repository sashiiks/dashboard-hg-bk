import re
import pandas as pd


def clean_empty(value):
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value == "" or value.lower() in ["nan", "none"]:
        return pd.NA

    return value


def clean_amount(value):
    value = clean_empty(value)

    if pd.isna(value):
        return pd.NA

    digits = re.sub(r"\D", "", str(value))

    if digits == "":
        return pd.NA

    return int(digits)


def first_non_empty(series):
    series = series.map(clean_empty)
    series = series.dropna()

    if len(series) == 0:
        return pd.NA

    return series.iloc[0]


def last_non_empty(series):
    series = series.map(clean_empty)
    series = series.dropna()

    if len(series) == 0:
        return pd.NA

    return series.iloc[-1]


def last_clean_amount(series):
    series = series.map(clean_amount)
    series = series.dropna()

    if len(series) == 0:
        return pd.NA

    return series.iloc[-1]


def build_transaction_BK(df):
    data = df.copy()

    # =========================
    # Rapikan nama kolom
    # =========================

    data.columns = data.columns.str.strip()

    # =========================
    # Pastikan invoice valid
    # =========================

    data["invoice_no"] = data["invoice_no"].map(clean_empty)

    data = data[
        data["invoice_no"].notna()
    ].copy()

    # =========================
    # Pertahankan urutan source
    # =========================

    data["_row_order"] = range(len(data))

    data = data.sort_values(
        "_row_order"
    )

    # =========================
    # Build transaction layer
    # =========================

    transactions = (
        data
        .groupby(
            "invoice_no",
            sort=False
        )
        .agg(
            source_id=("id", first_non_empty),
            customer_phone=("phone_number", first_non_empty),
            customer_name=("cust_name", first_non_empty),
            tanggal=("tanggal", first_non_empty),
            waktu=("waktu", first_non_empty),
            branch=("branch", first_non_empty),
            sales=("sales", first_non_empty),
            trx_type=("trx_type", first_non_empty),
            sub_trx_type=("sub_trx_type", first_non_empty),
            package=("package", first_non_empty),
            program=("program", first_non_empty),
            total=("total", last_clean_amount),
            amount=("amount", last_clean_amount),
            payment_total=("payment_total", last_clean_amount),
            payment_date=("payment_date", first_non_empty),
            final_status=("status", last_non_empty),
            raw_row_count=("invoice_no", "size"),
        )
        .reset_index()
    )

    return transactions
