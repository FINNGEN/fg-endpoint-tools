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
        # check_wide_cancer_endpoints(dataf),  # TODO(Vincent 2025-04-11)
    ]

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
    # TODO(VIncent 2025-04-04) Rework to be separate for each assumptions
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


def write_html_report(output_path, context):
    env = jinja2.Environment(
        loader=jinja2.PackageLoader("fg_endpoint_tools"),
        autoescape=jinja2.select_autoescape(),
    )

    template = env.get_template("report.html")

    with open(output_path, "w") as ff:
        ff.write(template.render(context))
