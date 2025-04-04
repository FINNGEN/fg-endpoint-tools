"""
Checks assumptions for a endpoint definition file.

Assumptions:
- must: no duplicate endpoints by NAME
- should: no endpoints with suffix _EXALLC
- should: no endpoints with suffix _EXMORE
- must: <endpoint>_WIDE and basic <endpoint> have the same case definition in cancer registry
- must: <endpoint>_WIDE and basic <endpoint> have different case definitions for Hilmo
  . _WIDE has a definition in Hilmo
  . basic has no definition in Hilmo
- must: <endpoint>_WIDE and basic <endpoint> have the same control definition
- should: endpoint HD_ICD_<x> be the same has COD_ICD_<x>
- should: no OMIT=2 endpoints getting recursively included in non-OMIT=2 endpoints
"""

from pathlib import Path

import polars as pl


def read_definitions_excel(path: Path):
    dataf = pl.read_excel(path, read_options={"dtypes": "string"})
    return dataf


def get_summary(dataf):
    """Summary statistics on the endpoint definition table."""
    columns = set(dataf.columns)

    has_control_definitions = (
        "CONTROL_EXCLUDE" in columns
        and "CONTROL_PRECONDITIONS" in columns
        and "CONTROL_CONDITIONS" in columns
        and "CONTROLS_Modification_date" in columns
        and "CONTROLS_Modified_by" in columns
        and "CONTROLS_Modification_reason" in columns
    )

    has_core_info = "CORE_ENDPOINTS" in columns and "REASON_FOR_NONCORE" in columns

    return {
        "n_columns": len(dataf.columns),
        "n_rows": dataf.height,
        "has_control_definitions": has_control_definitions,
        "has_core_info": has_core_info,
    }


def find_duplicates_by_name(dataf):
    assert "NAME" in dataf.columns

    names = dataf.get_column("NAME")
    dups = names.filter(names.is_duplicated()).unique().to_list()

    dups = sorted(dups)
    return dups


def find_any_exallc(dataf):
    return find_any_with_suffix(dataf, "_EXALLC")


def find_any_exmore(dataf):
    return find_any_with_suffix(dataf, "_EXMORE")


def find_any_with_suffix(dataf, suffix):
    assert "NAME" in dataf.columns

    with_suffix = (
        dataf.filter(pl.col("NAME").str.ends_with(suffix))
        .get_column("NAME")
        .unique()
        .to_list()
    )

    with_suffix = sorted(with_suffix)
    return with_suffix


def check_wide_cancer_endpoints(dataf):
    columns_cancer = [
        "CANC_TOPO",
        "CANC_TOPO_EXCL",
        "CANC_MORPH",
        "CANC_MORPH_EXCL",
        "CANC_BEHAV",
    ]

    columns_control = [
        "CONTROL_EXCLUDE",
        "CONTROL_PRECONDITIONS",
        "CONTROL_CONDITIONS",
    ]

    good_state = {
        "have_same_cancer_definition": True,
        "wide_has_hilmo_definition": True,
        "basic_has_hilmo_definition": False,
        "have_same_control_definition": True,
    }

    all_endpoints = set(dataf.get_column("NAME"))

    pair_basic_wide_endpoints = []
    for ee in all_endpoints:
        if ee.endswith("_WIDE"):
            basic = ee.removesuffix("_WIDE")
            pair_basic_wide_endpoints.append([basic, ee])

    checks = []
    for basic, wide in pair_basic_wide_endpoints:
        if basic not in all_endpoints:
            checks.append(
                {
                    "basic": None,
                    "wide": wide,
                    "have_same_cancer_definition": None,
                    "wide_has_hilmo_definition": None,
                    "basic_has_hilmo_definition": None,
                    "have_same_control_definition": None,
                }
            )
            continue

        # Cancer case definition
        have_same_cancer_definition = check_pair_has_same_values(
            dataf, [basic, wide], columns_cancer
        )

        # Hilmo case definition
        wide_has_hilmo_definition = check_endpoint_has_hilmo_definition(dataf, wide)
        basic_has_hilmo_definition = check_endpoint_has_hilmo_definition(dataf, basic)

        # Control definition
        have_same_control_definition = check_pair_has_same_values(
            dataf, [basic, wide], columns_control
        )

        checks.append(
            {
                "basic": basic,
                "wide": wide,
                "have_same_cancer_definition": have_same_cancer_definition,
                "wide_has_hilmo_definition": wide_has_hilmo_definition,
                "basic_has_hilmo_definition": basic_has_hilmo_definition,
                "have_same_control_definition": have_same_control_definition,
            }
        )

    broken_assumptions = []
    for check in checks:
        is_good = True

        for key, good_value in good_state.items():
            if check[key] != good_value:
                is_good = False
                break

        if not is_good:
            broken_assumptions.append(check)

    broken_assumptions = sorted(broken_assumptions, key=lambda dd: dd["wide"])
    return broken_assumptions


def check_pair_has_same_values(dataf, endpoint_pair, columns):
    return (
        dataf.filter(pl.col("NAME").is_in(endpoint_pair))
        .select(columns)
        .is_duplicated()
        .all()
    )


def check_endpoint_has_hilmo_definition(dataf, endpoint):
    columns_hilmo = [
        "HD_ICD_10",
        "HD_ICD_9",
        "HD_ICD_8",
        "HD_ICD_10_EXCL",
        "HD_ICD_9_EXCL",
        "HD_ICD_8_EXCL",
    ]

    return (
        dataf.filter(pl.col("NAME") == endpoint)
        .select(pl.col(columns_hilmo).is_not_null())
        .select(pl.any_horizontal(pl.all()))
        .item()
    )


def check_cases_suffix(dataf, suffix):
    results = []

    columns_can_differ = [
        "NAME",
        "LONGNAME",
        "CONTROL_EXCLUDE",
        "CONTROL_CONDITIONS",
        "CONTROLS_Modification_date",
        "CONTROLS_Modified_by",
        "CONTROLS_Modification_reason",
        "OMIT",
        "LEVEL",
        "version",
        "Modification_date",
        "Modified_by",
        "Modification_reason",
    ]

    all_endpoints = set(dataf.get_column("NAME"))

    with_suffix = [ee for ee in all_endpoints if ee.endswith(suffix)]
    for ee in with_suffix:
        base = ee.removesuffix(suffix)
        pair = dataf.filter(pl.col("NAME").is_in([ee, base])).select(
            pl.exclude(columns_can_differ)
        )

        if base not in all_endpoints:
            results.append(
                {
                    "endpoint": ee,
                    "error": f"The endpoint {ee} is missing its base endpoint {base}.",
                }
            )

        elif not pair.is_duplicated().all():
            differ_by = (
                pair
                # Compare values within each column
                .select(pl.all().is_duplicated())
                # Reduce to 1 row, with True/False indicating duplicate value for each column
                .select(pl.col("*").all())
                # Transpose to find columns that differ
                .unpivot()
                .filter(~pl.col("value"))
            )

            diffs = []
            for column in differ_by.get_column("variable"):
                base_value = (
                    dataf.filter(pl.col("NAME") == base).get_column(column).item()
                )
                ee_value = dataf.filter(pl.col("NAME") == ee).get_column(column).item()
                diffs.append({"column": column, "base": base_value, "other": ee_value})

            results.append(
                {
                    "endpoint": ee,
                    "error": f"The endpoints {ee} and {base} don't have the same case definition.",
                    "diffs": diffs,
                }
            )

    return results
