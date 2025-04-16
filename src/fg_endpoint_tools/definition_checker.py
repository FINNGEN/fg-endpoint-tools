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

import json
from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from enum import auto
from pathlib import Path

import polars as pl


class Status(StrEnum):
    ALL_GOOD = auto()
    WARNING = auto()
    FAIL = auto()


@dataclass
class Expectation:
    idname: str
    status: Status
    n_errors: int
    endpoints_in_error: list[str]
    data: any
    html_view: dict = field(default_factory=dict)


def read_definitions_excel(file_like):
    dataf = pl.read_excel(file_like, read_options={"dtypes": "string"})
    return dataf


def collect_report(file_like):
    dataf = read_definitions_excel(file_like)

    expectations = [
        assess_duplicates_by_name(dataf),
        assess_any_exallc(dataf),
        assess_any_exmore(dataf),
    ]
    expectations += check_wide_cancer_endpoints(dataf)

    return {
        "summary": get_summary(dataf),
        "expectations": expectations,
    }


def as_json(object):
    return json.dumps(object, indent=2)


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


def assess_duplicates_by_name(dataf) -> Expectation:
    assert "NAME" in dataf.columns

    names = dataf.get_column("NAME")
    dups = names.filter(names.is_duplicated()).unique().to_list()

    dups = sorted(dups)

    status = Status.ALL_GOOD if len(dups) == 0 else Status.FAIL

    return Expectation(
        idname="duplicates",
        status=status,
        n_errors=len(dups),
        endpoints_in_error=dups,
        data=dups,
    )


def assess_any_exallc(dataf) -> Expectation:
    any_exallc = find_any_with_suffix(dataf, "_EXALLC")

    status = Status.ALL_GOOD if len(any_exallc) == 0 else Status.WARNING

    return Expectation(
        idname="any_exallc",
        status=status,
        n_errors=len(any_exallc),
        endpoints_in_error=any_exallc,
        data=any_exallc,
    )


def assess_any_exmore(dataf) -> Expectation:
    any_exmore = find_any_with_suffix(dataf, "_EXMORE")

    status = Status.ALL_GOOD if len(any_exmore) == 0 else Status.WARNING

    return Expectation(
        idname="any_exmore",
        status=status,
        n_errors=len(any_exmore),
        endpoints_in_error=any_exmore,
        data=any_exmore,
    )


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

    all_endpoints = set(dataf.get_column("NAME"))

    pair_basic_wide_endpoints = []
    for ee in all_endpoints:
        if ee.endswith("_WIDE"):
            basic = ee.removesuffix("_WIDE")
            pair_basic_wide_endpoints.append([basic, ee])

    without_basic_endpoints = []
    different_cancer_definitions = []
    values_cancer_definition = []
    wide_without_hilmo_definition = []
    basic_with_hilmo_definition = []
    different_control_definition = []
    values_control_definition = []

    for basic, wide in pair_basic_wide_endpoints:
        if basic not in all_endpoints:
            without_basic_endpoints.append({"wide": wide, "basic": basic})
            continue

        has_same_cancer_definition, values_pair_cancer_definition = (
            check_pair_has_same_values(dataf, basic, wide, columns_cancer)
        )
        if not has_same_cancer_definition:
            different_cancer_definitions.append({"wide": wide, "basic": basic})
            values_cancer_definition.append(values_pair_cancer_definition)

        if not check_endpoint_has_hilmo_definition(dataf, wide):
            wide_without_hilmo_definition.append({"wide": wide, "basic": basic})

        if check_endpoint_has_hilmo_definition(dataf, basic):
            basic_with_hilmo_definition.append({"wide": wide, "basic": basic})

        has_same_control_definition, values_pair_control_definition = (
            check_pair_has_same_values(dataf, basic, wide, columns_control)
        )
        if not has_same_control_definition:
            different_control_definition.append({"wide": wide, "basic": basic})
            values_control_definition.append(values_pair_control_definition)

    # Sort by endpoint _WIDE name
    without_basic_endpoints = sorted(without_basic_endpoints, key=lambda dd: dd["wide"])
    different_cancer_definitions = sorted(
        different_cancer_definitions, key=lambda dd: dd["wide"]
    )
    values_cancer_definition = sorted(
        values_cancer_definition, key=lambda dd: dd["wide"]
    )
    wide_without_hilmo_definition = sorted(
        wide_without_hilmo_definition, key=lambda dd: dd["wide"]
    )
    basic_with_hilmo_definition = sorted(
        basic_with_hilmo_definition, key=lambda dd: dd["basic"]
    )
    different_control_definition = sorted(
        different_control_definition, key=lambda dd: dd["wide"]
    )
    values_control_definition = sorted(
        values_control_definition, key=lambda dd: dd["wide"]
    )

    expectations = [
        Expectation(
            idname="cancer_wide_has_basic_endpoint",
            status=Status.ALL_GOOD
            if len(without_basic_endpoints) == 0
            else Status.FAIL,
            n_errors=len(without_basic_endpoints),
            endpoints_in_error=[dd["wide"] for dd in without_basic_endpoints],
            data=without_basic_endpoints,
        ),
        Expectation(
            idname="cancer_wide_same_cancer_definition",
            status=Status.ALL_GOOD
            if len(different_cancer_definitions) == 0
            else Status.FAIL,
            n_errors=len(different_cancer_definitions),
            endpoints_in_error=[dd["wide"] for dd in different_cancer_definitions],
            data=values_cancer_definition,
        ),
        Expectation(
            idname="cancer_wide_have_hilmo_definition",
            status=Status.ALL_GOOD
            if len(wide_without_hilmo_definition) == 0
            else Status.FAIL,
            n_errors=len(wide_without_hilmo_definition),
            endpoints_in_error=[dd["wide"] for dd in wide_without_hilmo_definition],
            data=wide_without_hilmo_definition,
        ),
        Expectation(
            idname="cancer_wide_basic_have_no_hilmo_definition",
            status=Status.ALL_GOOD
            if len(basic_with_hilmo_definition) == 0
            else Status.FAIL,
            n_errors=len(basic_with_hilmo_definition),
            endpoints_in_error=[dd["basic"] for dd in basic_with_hilmo_definition],
            data=basic_with_hilmo_definition,
        ),
        Expectation(
            idname="cancer_wide_same_control_definition",
            status=Status.ALL_GOOD
            if len(different_control_definition) == 0
            else Status.FAIL,
            n_errors=len(different_control_definition),
            endpoints_in_error=[dd["wide"] for dd in different_control_definition],
            data=values_control_definition,
        ),
    ]

    return expectations


def check_pair_has_same_values(dataf, basic, wide, columns):
    has_same_values = (
        dataf.filter(pl.col("NAME").is_in([basic, wide]))
        .select(columns)
        .is_duplicated()
        .all()
    )

    values = (
        dataf.filter(pl.col("NAME").is_in([basic, wide]))
        .select(["NAME"] + columns)
        .to_dicts()
    )
    values = {dd.pop("NAME"): dd for dd in values}

    values = {
        "wide": wide,
        "basic": basic,
        "cols_wide": values[wide],
        "cols_basic": values[basic],
        "diff_cols_wide": {},
        "diff_cols_basic": {}
    }

    for col in values['cols_wide'].keys():
        if values['cols_wide'][col] != values['cols_basic'][col]:
            values["diff_cols_wide"][col] = values['cols_wide'][col] 
            values["diff_cols_basic"][col] = values['cols_basic'][col] 
   
    return (has_same_values, values)


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
    # TODO(VIncent 2025-04-04) Rework to be just a value-differ, currently not used.
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
