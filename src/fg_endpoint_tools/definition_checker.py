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
- must: NAME should contain only upper case A-Z, numbers 0-9, or _ (underscore)
- should: no OMIT=2 endpoints getting recursively included in non-OMIT=2 endpoints
- TODO must: all descendants endpoints (from `INCLUDE` recursively) must exist
- TODO should: no duplicate endpoints in the `INCLUDE` field
- TODO must: all _COMORB endpoint are OMIT=2

TODO(Vincent 2025-05-16)  Add proposed fixes for each expectation:
For example, for the include OMIT=2 expectation:
1. Add `OMIT=2` to this endpoint.
2. Remove `OMIT=2` for the included endpoint.
3. Remove the included endpoint from the `INCLUDE` list.
"""

import io
import itertools
import re
import typing
from base64 import b64encode
from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from enum import auto

import polars as pl
import xlsxwriter


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
    data: typing.Any
    html_view: dict = field(default_factory=dict)
    excel_file_b64: str = ""


def read_definitions_excel(file_like):
    dataf = pl.read_excel(file_like, read_options={"dtypes": "string"})
    return dataf


def collect_report(file_like):
    dataf = read_definitions_excel(file_like)

    expectations = [
        assess_duplicates_by_name(dataf),
        assess_simple_names(dataf),
        assess_any_exallc(dataf),
        assess_any_exmore(dataf),
        assess_hd_cod_same_icd(dataf),
    ]
    expectations += assess_wide_cancer_endpoints(dataf)
    expectations += assess_include_rules(dataf)

    expectations = {xx.idname: xx for xx in expectations}

    return {
        "summary": get_summary(dataf),
        "expectations": expectations,
    }


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

    omit1_endpoints = (
        dataf.filter(pl.col("OMIT") == "1").get_column("NAME").sort().to_list()
    )
    omit2_endpoints = (
        dataf.filter(pl.col("OMIT") == "2").get_column("NAME").sort().to_list()
    )

    return {
        "n_columns": len(dataf.columns),
        "n_rows": dataf.height,
        "has_control_definitions": has_control_definitions,
        "has_core_info": has_core_info,
        "omit1_endpoints": omit1_endpoints,
        "omit2_endpoints": omit2_endpoints,
    }


def assess_duplicates_by_name(dataf) -> Expectation:
    assert "NAME" in dataf.columns

    names = dataf.get_column("NAME")
    dups = names.filter(names.is_duplicated()).unique().to_list()

    dups = sorted(dups)

    status = Status.ALL_GOOD if len(dups) == 0 else Status.FAIL

    excel_b64 = write_excel_as_b64(dataf, dups)

    return Expectation(
        idname="name_duplicates",
        status=status,
        n_errors=len(dups),
        endpoints_in_error=dups,
        data=dups,
        excel_file_b64=excel_b64,
    )


def assess_simple_names(dataf) -> Expectation:
    names = dataf.get_column("NAME")

    # NOTE(Vincent 2025-05-12)  Must be a regex compatible in Rust and Python,
    # as it will be used in polars, which uses Rust regex crate, and also by the
    # python re modlue.
    # For the Rust regex syntax, see: https://docs.rs/regex/latest/regex/#syntax
    #
    # NOTE(Vincent 2025-05-12)  Using parentheses around the regex to make the
    # non-matching parts appear when using python `re.split`. The parentheses do not
    # affect the yes/no matching in both Rust and Python regex systems.
    regex_complex_names = "([^A-Z0-9_])"
    regex_python_compiled = re.compile(regex_complex_names)

    complex_names = (
        names.filter(names.str.contains(regex_complex_names)).unique().to_list()
    )

    complex_names = sorted(complex_names)

    data = []
    for name in complex_names:
        name_annotated = []

        parts = re.split(regex_python_compiled, name)
        for part in parts:
            is_complex = re.fullmatch(regex_python_compiled, part)
            name_annotated.append({"string": part, "is_complex": is_complex})

        data.append({"endpoint": name, "name_annotated": name_annotated})

    status = Status.ALL_GOOD if len(complex_names) == 0 else Status.FAIL

    excel_b64 = write_excel_as_b64(dataf, complex_names)

    return Expectation(
        idname="complex_names",
        status=status,
        n_errors=len(complex_names),
        endpoints_in_error=complex_names,
        data=data,
        excel_file_b64=excel_b64,
    )


def assess_any_exallc(dataf) -> Expectation:
    any_exallc = find_any_with_suffix(dataf, "_EXALLC")

    status = Status.ALL_GOOD if len(any_exallc) == 0 else Status.WARNING

    excel_b64 = write_excel_as_b64(dataf, any_exallc)

    return Expectation(
        idname="name_any_exallc",
        status=status,
        n_errors=len(any_exallc),
        endpoints_in_error=any_exallc,
        data=any_exallc,
        excel_file_b64=excel_b64,
    )


def assess_any_exmore(dataf) -> Expectation:
    any_exmore = find_any_with_suffix(dataf, "_EXMORE")

    status = Status.ALL_GOOD if len(any_exmore) == 0 else Status.WARNING

    excel_b64 = write_excel_as_b64(dataf, any_exmore)

    return Expectation(
        idname="name_any_exmore",
        status=status,
        n_errors=len(any_exmore),
        endpoints_in_error=any_exmore,
        data=any_exmore,
        excel_file_b64=excel_b64,
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


def assess_wide_cancer_endpoints(dataf):
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
    #
    different_cancer_definitions = []
    different_cancer_definitions_data = []
    #
    wide_without_hilmo_definition = []
    wide_without_hilmo_definition_data = []
    #
    basic_with_hilmo_definition = []
    basic_with_hilmo_definition_data = []
    #
    different_control_definition = []
    different_control_definition_data = []

    for basic, wide in pair_basic_wide_endpoints:
        if basic not in all_endpoints:
            without_basic_endpoints.append({"wide": wide, "basic": basic})
            continue

        has_same_cancer_definition, values_pair_cancer_definition = (
            check_pair_has_same_values(dataf, basic, wide, columns_cancer)
        )
        if not has_same_cancer_definition:
            different_cancer_definitions.append({"wide": wide, "basic": basic})
            different_cancer_definitions_data.append(values_pair_cancer_definition)

        wide_has_hilmo_definition, wide_hilmo_definition_values = (
            check_endpoint_has_hilmo_definition(dataf, wide)
        )
        if not wide_has_hilmo_definition:
            wide_without_hilmo_definition.append({"wide": wide, "basic": basic})
            wide_without_hilmo_definition_data.append(wide_hilmo_definition_values)

        basic_has_hilmo_definition, basic_hilmo_definition_values = (
            check_endpoint_has_hilmo_definition(dataf, basic)
        )
        if basic_has_hilmo_definition:
            basic_with_hilmo_definition.append({"wide": wide, "basic": basic})
            basic_with_hilmo_definition_data.append(basic_hilmo_definition_values)

        has_same_control_definition, values_pair_control_definition = (
            check_pair_has_same_values(dataf, basic, wide, columns_control)
        )
        if not has_same_control_definition:
            different_control_definition.append({"wide": wide, "basic": basic})
            different_control_definition_data.append(values_pair_control_definition)

    # Sort by endpoint _WIDE name
    without_basic_endpoints = sorted(without_basic_endpoints, key=lambda dd: dd["wide"])
    #
    different_cancer_definitions = sorted(
        different_cancer_definitions, key=lambda dd: dd["wide"]
    )
    different_cancer_definitions_data = sorted(
        different_cancer_definitions_data, key=lambda dd: dd["wide"]
    )
    #
    wide_without_hilmo_definition = sorted(
        wide_without_hilmo_definition, key=lambda dd: dd["wide"]
    )
    wide_without_hilmo_definition_data = sorted(
        wide_without_hilmo_definition_data, key=lambda dd: dd["endpoint"]
    )
    #
    basic_with_hilmo_definition = sorted(
        basic_with_hilmo_definition, key=lambda dd: dd["basic"]
    )
    basic_with_hilmo_definition_data = sorted(
        basic_with_hilmo_definition_data, key=lambda dd: dd["endpoint"]
    )
    #
    different_control_definition = sorted(
        different_control_definition, key=lambda dd: dd["wide"]
    )
    different_control_definition_data = sorted(
        different_control_definition_data, key=lambda dd: dd["wide"]
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
            excel_file_b64=write_excel_as_b64(
                dataf, [dd["wide"] for dd in without_basic_endpoints]
            ),
        ),
        Expectation(
            idname="cancer_wide_same_cancer_definition",
            status=Status.ALL_GOOD
            if len(different_cancer_definitions) == 0
            else Status.FAIL,
            n_errors=len(different_cancer_definitions),
            endpoints_in_error=[dd["wide"] for dd in different_cancer_definitions],
            data=different_cancer_definitions_data,
            excel_file_b64=write_excel_as_b64(
                dataf,
                list(
                    itertools.chain.from_iterable(
                        [
                            [dd["wide"], dd["basic"]]
                            for dd in different_cancer_definitions
                        ]
                    )
                ),
            ),
        ),
        Expectation(
            idname="cancer_wide_have_hilmo_definition",
            status=Status.ALL_GOOD
            if len(wide_without_hilmo_definition) == 0
            else Status.FAIL,
            n_errors=len(wide_without_hilmo_definition),
            endpoints_in_error=[dd["wide"] for dd in wide_without_hilmo_definition],
            data=wide_without_hilmo_definition_data,
            excel_file_b64=write_excel_as_b64(
                dataf, [dd["wide"] for dd in wide_without_hilmo_definition]
            ),
        ),
        Expectation(
            idname="cancer_wide_basic_have_no_hilmo_definition",
            status=Status.ALL_GOOD
            if len(basic_with_hilmo_definition) == 0
            else Status.FAIL,
            n_errors=len(basic_with_hilmo_definition),
            endpoints_in_error=[dd["basic"] for dd in basic_with_hilmo_definition],
            data=basic_with_hilmo_definition_data,
            excel_file_b64=write_excel_as_b64(
                dataf, [dd["basic"] for dd in basic_with_hilmo_definition]
            ),
        ),
        Expectation(
            idname="cancer_wide_same_control_definition",
            status=Status.ALL_GOOD
            if len(different_control_definition) == 0
            else Status.FAIL,
            n_errors=len(different_control_definition),
            endpoints_in_error=[dd["wide"] for dd in different_control_definition],
            data=different_control_definition_data,
            excel_file_b64=write_excel_as_b64(
                dataf,
                list(
                    itertools.chain.from_iterable(
                        [
                            [dd["wide"], dd["basic"]]
                            for dd in different_control_definition
                        ]
                    )
                ),
            ),
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
        "diff_cols_basic": {},
        "diffs": {},
    }

    for col in values["cols_wide"].keys():
        if values["cols_wide"][col] != values["cols_basic"][col]:
            values["diff_cols_wide"][col] = values["cols_wide"][col]
            values["diff_cols_basic"][col] = values["cols_basic"][col]

            values["diffs"][col] = simple_diff(
                values["diff_cols_wide"][col], values["diff_cols_basic"][col]
            )

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

    values = (
        dataf.filter(pl.col("NAME") == endpoint)
        .select(pl.col(columns_hilmo))
        .to_dicts()
    )
    values = values[0]  # only 1 endpoint => only 1 row

    data = {"endpoint": endpoint, "values": values}

    has_hilmo_definition = (
        dataf.filter(pl.col("NAME") == endpoint)
        .select(pl.col(columns_hilmo).is_not_null())
        .select(pl.any_horizontal(pl.all()))
        .item()
    )

    return has_hilmo_definition, data


def assess_hd_cod_same_icd(dataf):
    """An endpoint HD_ICD_* definitions should be the same as its COD_ICD_* ones"""
    with_diff = (
        dataf.select(
            pl.col("NAME"),
            pl.col("HD_ICD_10"),
            pl.col("HD_ICD_9"),
            pl.col("HD_ICD_8"),
            pl.col("HD_ICD_10_EXCL"),
            pl.col("HD_ICD_9_EXCL"),
            pl.col("HD_ICD_8_EXCL"),
            pl.col("COD_ICD_10"),
            pl.col("COD_ICD_9"),
            pl.col("COD_ICD_8"),
            pl.col("COD_ICD_10_EXCL"),
            pl.col("COD_ICD_9_EXCL"),
            pl.col("COD_ICD_8_EXCL"),
            (
                (pl.col("HD_ICD_10").ne_missing(pl.col("COD_ICD_10")))
                | (pl.col("HD_ICD_9").ne_missing(pl.col("COD_ICD_9")))
                | (pl.col("HD_ICD_8").ne_missing(pl.col("COD_ICD_8")))
                | (pl.col("HD_ICD_10_EXCL").ne_missing(pl.col("COD_ICD_10_EXCL")))
                | (pl.col("HD_ICD_9_EXCL").ne_missing(pl.col("COD_ICD_9_EXCL")))
                | (pl.col("HD_ICD_8_EXCL").ne_missing(pl.col("COD_ICD_8_EXCL")))
            ).alias("AnyDiffICD"),
        )
        #
        .filter(pl.col("AnyDiffICD"))
        #
        .sort(by=pl.col("NAME"))
    )

    endpoints_in_error = (
        with_diff.get_column("NAME").unique(maintain_order=True).to_list()
    )

    status = Status.ALL_GOOD if len(endpoints_in_error) == 0 else Status.WARNING

    # Building the data
    data = []
    check_pair_cols = [
        ["HD_ICD_10", "COD_ICD_10"],
        ["HD_ICD_9", "COD_ICD_9"],
        ["HD_ICD_8", "COD_ICD_8"],
        ["HD_ICD_10_EXCL", "COD_ICD_10_EXCL"],
        ["HD_ICD_9_EXCL", "COD_ICD_9_EXCL"],
        ["HD_ICD_8_EXCL", "COD_ICD_8_EXCL"],
    ]
    for endpoint_data in with_diff.to_dicts():
        endpoint = endpoint_data.pop("NAME")
        endpoint_data.pop("AnyDiffICD")

        endpoint_data["endpoint"] = endpoint
        endpoint_data["diffs"] = []

        for hd_col, cod_col in check_pair_cols:
            if endpoint_data[hd_col] != endpoint_data[cod_col]:
                diff = simple_diff(endpoint_data[hd_col], endpoint_data[cod_col])
                diff["hd_col"] = hd_col
                diff["cod_col"] = cod_col

                endpoint_data["diffs"].append(diff)

        data.append(endpoint_data)

    return Expectation(
        idname="code_hd_cod_same_icd",
        status=status,
        n_errors=len(endpoints_in_error),
        endpoints_in_error=endpoints_in_error,
        data=data,
        excel_file_b64=write_excel_as_b64(dataf, endpoints_in_error),
    )


def assess_include_rules(dataf):
    map_parent_children = get_map_parent_children(dataf)
    map_child_ancestors = get_map_child_ancestors(map_parent_children)

    omit2_endpoints = set(
        dataf.filter(pl.col("OMIT") == "2").get_column("NAME").to_list()
    )

    expectations = [
        assess_include_omit2(
            map_parent_children, map_child_ancestors, omit2_endpoints, dataf
        )
    ]

    return expectations


def assess_include_omit2(
    map_parent_children, map_child_ancestors, omit2_endpoints, dataf
):
    endpoints_in_error = []
    data = {}

    for parent, children in map_parent_children.items():
        normal_endpoint = parent not in omit2_endpoints
        has_omit2_children = not children.isdisjoint(omit2_endpoints)

        if normal_endpoint and has_omit2_children:
            endpoints_in_error.append(parent)

            include_definition = (
                dataf.filter(pl.col("NAME") == parent).select("INCLUDE").item()
            )
            omit2_children = sorted(children.intersection(omit2_endpoints))

            data[parent] = {
                "omit2_children": omit2_children,
                "highlight": highlight(include_definition, omit2_children),
            }

    endpoints_in_error = sorted(endpoints_in_error)

    status = status.ALL_GOOD if len(endpoints_in_error) == 0 else Status.FAIL

    return Expectation(
        idname="include_omit2",
        status=status,
        n_errors=len(endpoints_in_error),
        endpoints_in_error=endpoints_in_error,
        data=data,
        excel_file_b64=write_excel_as_b64(dataf, endpoints_in_error),
    )


def highlight(text, words):
    # Assumes all words are found in text.
    # Assumes non-overlapping words.
    # Assumes at least 1 word in words.
    text_breakdown = []

    positions = []
    for ww in words:
        start = text.find(ww)
        positions.append({"start": start, "end": start + len(ww)})

    positions = sorted(positions, key=lambda pp: pp["start"])
    current_position = 0
    for pp in positions:
        good_text = text[current_position : pp["start"]]

        if good_text != "":
            text_breakdown.append({"text": good_text, "bad": False})

        bad_text = text[pp["start"] : pp["end"]]
        text_breakdown.append({"text": bad_text, "bad": True})

        current_position = pp["end"]

    last_end = positions[-1]["end"]
    if last_end < len(text):
        good_text = text[last_end:]
        text_breakdown.append({"text": good_text, "bad": False})

    return text_breakdown


def simple_diff(string_a, string_b):
    # Transform None to empty string.
    string_a = string_a or ""
    string_b = string_b or ""

    min_length = min(len(string_a), len(string_b))

    same_prefix_until = 0
    while same_prefix_until < min_length:
        if string_a[same_prefix_until] == string_b[same_prefix_until]:
            same_prefix_until += 1
        else:
            break

    same_suffix_after = -1
    while same_suffix_after > -min_length:
        if string_a[same_suffix_after] == string_b[same_suffix_after]:
            same_suffix_after -= 1
        else:
            break

    diff = {
        "string_a": {
            "original": string_a,
            "prefix_common": string_a[:same_prefix_until],
            "middle_diff": string_a[
                same_prefix_until : len(string_a) + same_suffix_after + 1
            ],
            "suffix_common": string_a[len(string_a) + same_suffix_after + 1 :],
        },
        "string_b": {
            "original": string_b,
            "prefix_common": string_b[:same_prefix_until],
            "middle_diff": string_b[
                same_prefix_until : len(string_b) + same_suffix_after + 1
            ],
            "suffix_common": string_b[len(string_b) + same_suffix_after + 1 :],
        },
    }

    return diff


def write_excel_as_b64(dataf, endpoint_names):
    in_memory_file = io.BytesIO()

    workbook = xlsxwriter.Workbook(in_memory_file)
    dataf.filter(pl.col("NAME").is_in(endpoint_names)).write_excel(workbook)
    workbook.close()

    as_b64 = b64encode(in_memory_file.getvalue()).decode("utf-8")

    return as_b64


def get_map_parent_children(dataf):
    rows = dataf.select("NAME", "INCLUDE").to_dicts()

    map_parent_children = {}
    for rr in rows:
        parent = rr["NAME"]

        if rr["INCLUDE"]:
            children = set(rr["INCLUDE"].split("|"))
        else:
            children = set()

        map_parent_children[parent] = children

    return map_parent_children


def get_map_child_ancestors(map_parent_children):
    # 1. Start by reversing the graph from  parent->children  to  child->parents
    map_child_parents = {}

    for parent, children in map_parent_children.items():
        for child in children:
            existing_parents = map_child_parents.get(child, set())
            existing_parents.add(parent)
            map_child_parents[child] = existing_parents

    # 2. Traverse the graph to build the set of all ancestors for each node
    map_child_ancestors = {}
    for child, parents in map_child_parents.items():
        if parents:
            ancestors = rec_ancestors_of(child, set(), map_child_parents)
            map_child_ancestors[child] = ancestors

    return map_child_ancestors


def rec_ancestors_of(node, acc, map_child_parents):
    if node not in map_child_parents:
        return acc

    else:
        for parent in map_child_parents[node]:
            acc.add(parent)
            acc = rec_ancestors_of(parent, acc, map_child_parents)
            return acc
