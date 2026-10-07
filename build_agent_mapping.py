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


def build_agent_mapping():
    # =========================
    # LOAD RAW DATA
    # =========================
    target = load_sheet("TARGET AGENT")
    hg = load_sheet("SALES HG OCT")
    bk = load_sheet("SALES BK OCT")

    # =========================
    # PREPARE TARGET
    # =========================
    target = prepare_target_agent(target)

    # Hanya scope HG & BK
    target = target[
        target["Company"].isin(["HG", "BK"])
        & target["Nama Agent"].ne("")
    ].copy()

    # =========================
    # PREPARE TRANSACTION
    # =========================
    hg = prepare_sales(hg, "Healthy Go")
    bk = prepare_sales(bk, "Bekelin")

    hg_fact = build_transaction_fact(hg, target)
    bk_fact = build_transaction_fact(bk, target)

    transaction = pd.concat(
        [hg_fact, bk_fact],
        ignore_index=True,
    )

    # =========================
    # NORMALIZE COMPANY
    # =========================
    transaction["company"] = transaction["brand"].map(
        BRAND_TO_COMPANY
    )

    transaction["agent"] = (
        transaction["sales"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    transaction["agent_key"] = (
        transaction["agent"]
        .str.casefold()
    )

    # =========================
    # TARGET MASTER
    # =========================
    target_master = target[
        [
            "Company",
            "Nama Agent",
            "agent_key",
            "Role",
            "Nama Team Leader",
            "Tier",
        ]
    ].drop_duplicates(
        subset=["Company", "agent_key"]
    )

    target_master = target_master.rename(
        columns={
            "Company": "target_company",
            "Nama Agent": "target_agent",
            "Role": "target_role",
            "Nama Team Leader": "target_team_leader",
            "Tier": "target_tier",
        }
    )

    # =========================
    # MERGE COMPANY + AGENT
    # =========================
    mapping = transaction[
        [
            "brand",
            "company",
            "agent",
        ]
    ].drop_duplicates()

    mapping = mapping.merge(
        target_master,
        left_on=["company", "agent"],
        right_on=["target_company", "target_agent"],
        how="left",
    )

    # =========================
    # MAPPING STATUS
    # =========================
    mapping["target_exists"] = (
        mapping["target_agent"]
        .notna()
        & mapping["target_agent"].ne("")
    )

    mapping["mapping_status"] = mapping[
        "target_exists"
    ].map(
        {
            True: "mapped",
            False: "agent_without_target",
        }
    )

    # =========================
    # OUTPUT
    # =========================
    result = mapping[
        [
            "company",
            "brand",
            "agent",
            "target_agent",
            "target_role",
            "target_team_leader",
            "target_tier",
            "target_exists",
            "mapping_status",
        ]
    ].sort_values(
        ["company", "mapping_status", "agent"]
    )

    return result


if __name__ == "__main__":
    mapping = build_agent_mapping()

    print("\n===== AGENT MAPPING =====")
    print(f"Total unique agent : {len(mapping):,}")
    print(
        f"Mapped             : "
        f"{(mapping['mapping_status'] == 'mapped').sum():,}"
    )
    print(
        f"Without target     : "
        f"{(mapping['mapping_status'] == 'agent_without_target').sum():,}"
    )

    print("\n===== MAPPING BY COMPANY =====")
    print(
        mapping.groupby(
            ["company", "mapping_status"]
        )
        .size()
        .unstack(fill_value=0)
    )

    print("\n===== AGENT WITHOUT TARGET =====")
    print(
        mapping[
            mapping["mapping_status"]
            == "agent_without_target"
        ][
            [
                "company",
                "brand",
                "agent",
            ]
        ].to_string(index=False)
    )

    print("\n===== MAPPED AGENTS =====")
    print(
        mapping[
            mapping["mapping_status"] == "mapped"
        ][
            [
                "company",
                "agent",
                "target_team_leader",
                "target_tier",
            ]
        ].to_string(index=False)
    )
