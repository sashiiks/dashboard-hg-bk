import pandas as pd

from build_transaction_fact import (
    load_sheet,
    prepare_target_agent,
    prepare_sales,
    build_transaction_fact,
)


def print_mapping_audit(
    fact: pd.DataFrame,
    target: pd.DataFrame,
):

    print("\n===== AGENT MAPPING AUDIT =====")

    # =========================================================
    # TARGET AGENT
    # =========================================================

    target_agents = (
        target[
            ["Company", "Nama Agent"]
        ]
        .drop_duplicates()
        .copy()
    )

    target_agents["Company"] = (
        target_agents["Company"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    target_agents["Nama Agent"] = (
        target_agents["Nama Agent"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # =========================================================
    # PERFORMANCE / TRANSACTION AGENT
    # =========================================================

    fact_agents = (
        fact[
            [
                "brand",
                "sales",
                "mapping_status",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    fact_agents["brand"] = (
        fact_agents["brand"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    fact_agents["sales"] = (
        fact_agents["sales"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # =========================================================
    # SUMMARY PER BRAND
    # =========================================================

    print("\n===== TARGET AGENT =====")

    target_summary = (
        target_agents
        .groupby("Company")
        .agg(
            target_agents=(
                "Nama Agent",
                "nunique",
            )
        )
    )

    print(
        target_summary.to_string()
    )

    print("\n===== TRANSACTION AGENT =====")

    fact_summary = (
        fact_agents
        .groupby("brand")
        .agg(
            transaction_agents=(
                "sales",
                "nunique",
            ),
            mapped_agents=(
                "mapping_status",
                lambda x: (
                    fact_agents.loc[
                        x.index,
                        "mapping_status"
                    ] == "mapped"
                ).sum(),
            ),
        )
    )

    print(
        fact_summary.to_string()
    )

    # =========================================================
    # UNMAPPED
    # =========================================================

    print("\n===== UNMAPPED AGENT =====")

    unmapped = fact_agents[
        fact_agents["mapping_status"]
        == "unmapped"
    ]

    if len(unmapped) == 0:

        print(
            "✓ Tidak ada agent transaction "
            "yang unmapped."
        )

    else:

        print(
            unmapped[
                [
                    "brand",
                    "sales",
                ]
            ]
            .sort_values(
                [
                    "brand",
                    "sales",
                ]
            )
            .to_string(
                index=False
            )
        )

    # =========================================================
    # MAPPED DISTRIBUTION
    # =========================================================

    print("\n===== MAPPING STATUS BY BRAND =====")

    mapping_summary = (
        fact
        .groupby(
            [
                "brand",
                "mapping_status",
            ]
        )
        .size()
        .unstack(
            fill_value=0
        )
    )

    print(
        mapping_summary.to_string()
    )


def main():

    print("Loading Google Sheets...")

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
        f"TARGET AGENT : "
        f"{len(target):,} rows"
    )

    print(
        f"HG RAW       : "
        f"{len(hg):,} rows"
    )

    print(
        f"BK RAW       : "
        f"{len(bk):,} rows"
    )

    # =========================================================
    # PREPARE
    # =========================================================

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

    # =========================================================
    # BUILD TRANSACTION FACT
    # =========================================================

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

    print(
        f"Transaction Fact : "
        f"{len(fact):,} rows"
    )

    # =========================================================
    # AUDIT
    # =========================================================

    print_mapping_audit(
        fact,
        target,
    )


if __name__ == "__main__":
    main()
