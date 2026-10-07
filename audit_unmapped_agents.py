import pandas as pd

from build_transaction_fact import (
    load_sheet,
    prepare_target_agent,
    prepare_sales,
    build_transaction_fact,
)


BRAND_TO_COMPANY = {
    "Healthy Go": "HG",
    "Bekelin": "BK",
}


def build_data():

    # =========================
    # LOAD DATA
    # =========================
    target = load_sheet("TARGET AGENT")
    hg = load_sheet("SALES HG OCT")
    bk = load_sheet("SALES BK OCT")

    target = prepare_target_agent(target)

    # =========================
    # HANYA SCOPE HG & BK
    # =========================
    target = target[
        target["Company"].isin(["HG", "BK"])
        & target["Nama Agent"].ne("")
    ].copy()

    # =========================
    # PREPARE SALES
    # =========================
    hg = prepare_sales(hg, "Healthy Go")
    bk = prepare_sales(bk, "Bekelin")

    # =========================
    # BUILD TRANSACTION FACT
    # =========================
    hg_fact = build_transaction_fact(hg, target)
    bk_fact = build_transaction_fact(bk, target)

    fact = pd.concat(
        [hg_fact, bk_fact],
        ignore_index=True,
    )

    # =========================
    # COMPANY MAPPING
    # =========================
    fact["company"] = fact["brand"].map(
        BRAND_TO_COMPANY
    )

    # =========================
    # NORMALIZE AGENT
    # =========================
    fact["agent"] = (
        fact["sales"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    fact["agent_key"] = (
        fact["agent"]
        .str.casefold()
    )

    # =========================
    # TARGET AGENT KEY
    # =========================
    target["target_agent_key"] = (
        target["Nama Agent"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    # =========================
    # TARGET LOOKUP
    # =========================
    target_lookup = target[
        [
            "Company",
            "target_agent_key",
        ]
    ].drop_duplicates(
        subset=[
            "Company",
            "target_agent_key",
        ]
    )

    target_lookup["target_exists"] = True

    # =========================
    # CHECK TARGET
    # =========================
    fact = fact.merge(
        target_lookup,
        left_on=[
            "company",
            "agent_key",
        ],
        right_on=[
            "Company",
            "target_agent_key",
        ],
        how="left",
    )

    # Pastikan benar-benar boolean
    fact["target_exists"] = (
        fact["target_exists"]
        .fillna(False)
        .astype(bool)
    )

    return fact


if __name__ == "__main__":

    fact = build_data()

    # =========================
    # ONLY UNMAPPED
    # =========================
    unmapped = fact[
        fact["target_exists"].eq(False)
    ].copy()

    # =========================
    # CLEAN STATUS
    # =========================
    unmapped["status_clean"] = (
        unmapped["status"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    # =========================
    # SUMMARY
    # =========================
    summary = (
        unmapped
        .groupby(
            [
                "company",
                "agent",
            ]
        )
        .agg(
            transactions=(
                "invoice_no",
                "count",
            ),
            paid=(
                "status_clean",
                lambda x: (
                    x == "success"
                ).sum(),
            ),
            unpaid=(
                "status_clean",
                lambda x: x.isin(
                    [
                        "pending",
                        "challenge",
                    ]
                ).sum(),
            ),
            cancel=(
                "status_clean",
                lambda x: (
                    x == "cancel"
                ).sum(),
            ),
        )
        .reset_index()
        .sort_values(
            [
                "company",
                "transactions",
            ],
            ascending=[
                True,
                False,
            ],
        )
    )

    # =========================
    # OUTPUT
    # =========================
    print(
        "\n===== UNMAPPED AGENT AUDIT ====="
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print("\n===== TOTAL =====")

    print(
        f"Unmapped transactions : "
        f"{len(unmapped):,}"
    )

    print(
        f"Paid                  : "
        f"{(unmapped['status_clean'] == 'success').sum():,}"
    )

    print(
        f"Unpaid                : "
        f"{unmapped['status_clean'].isin(['pending', 'challenge']).sum():,}"
    )

    print(
        f"Cancel                : "
        f"{(unmapped['status_clean'] == 'cancel').sum():,}"
    )
