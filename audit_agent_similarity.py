import pandas as pd
from difflib import SequenceMatcher

from build_transaction_fact import (
    load_sheet,
    prepare_target_agent,
    prepare_sales,
    build_transaction_fact,
)


def similarity(a, b):
    return SequenceMatcher(
        None,
        str(a).casefold(),
        str(b).casefold(),
    ).ratio()


def main():

    print("Loading Google Sheets...")

    target = load_sheet("TARGET AGENT")
    hg = load_sheet("SALES HG OCT")
    bk = load_sheet("SALES BK OCT")

    target = prepare_target_agent(target)

    hg = prepare_sales(
        hg,
        "Healthy Go",
    )

    bk = prepare_sales(
        bk,
        "Bekelin",
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
        [hg_fact, bk_fact],
        ignore_index=True,
    )

    # =========================================================
    # UNMAPPED UNIQUE NAMES
    # =========================================================

    unmapped = (
        fact.loc[
            fact["mapping_status"] == "unmapped",
            ["brand", "sales"],
        ]
        .drop_duplicates()
    )

    target_agents = (
        target[
            [
                "Company",
                "Nama Agent",
            ]
        ]
        .drop_duplicates()
    )

    print("\n===== AGENT SIMILARITY AUDIT =====")

    results = []

    for _, row in unmapped.iterrows():

        brand = row["brand"]
        sales = row["sales"]

        best_match = None
        best_score = 0
        best_company = None

        for _, target_row in target_agents.iterrows():

            score = similarity(
                sales,
                target_row["Nama Agent"],
            )

            if score > best_score:

                best_score = score
                best_match = (
                    target_row["Nama Agent"]
                )
                best_company = (
                    target_row["Company"]
                )

        results.append(
            {
                "brand": brand,
                "transaction_agent": sales,
                "closest_target_agent": best_match,
                "target_company": best_company,
                "similarity": round(
                    best_score * 100,
                    2,
                ),
            }
        )

    result = (
        pd.DataFrame(results)
        .sort_values(
            [
                "brand",
                "similarity",
            ],
            ascending=[
                True,
                False,
            ],
        )
    )

    print(
        result.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
