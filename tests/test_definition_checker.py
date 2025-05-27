import polars as pl

from fg_endpoint_tools import definition_checker


COLUMNS_CANCER = [
    "CANC_TOPO",
    "CANC_TOPO_EXCL",
    "CANC_MORPH",
    "CANC_MORPH_EXCL",
    "CANC_BEHAV",
]

COLUMNS_CONTROL = [
    "CONTROL_EXCLUDE",
    "CONTROL_PRECONDITIONS",
    "CONTROL_CONDITIONS",
]


def test_duplicate_endpoint_name():
    # 1.
    dataf_with_dups = pl.DataFrame(
        {"NAME": ["my_endpoint", "another_endpoint", "my_endpoint"]}
    )

    expected_data = ["my_endpoint"]
    expected_excel_b64 = definition_checker.write_excel_as_b64(
        dataf_with_dups, expected_data
    )
    expected_result = definition_checker.Expectation(
        idname="name_duplicates",
        status=definition_checker.Status.FAIL,
        n_errors=1,
        endpoints_in_error=["my_endpoint"],
        data=["my_endpoint"],
        excel_file_b64=expected_excel_b64,
    )

    assert expected_result == definition_checker.assess_duplicates_by_name(
        dataf_with_dups
    )

    # 2.
    dataf_no_dups = pl.DataFrame({"NAME": ["first_endpoint", "second_endpoint"]})

    expected_data = []
    expected_excel_b64 = definition_checker.write_excel_as_b64(
        dataf_no_dups, expected_data
    )
    expected_result = definition_checker.Expectation(
        idname="name_duplicates",
        status=definition_checker.Status.ALL_GOOD,
        n_errors=0,
        endpoints_in_error=[],
        data=expected_data,
        excel_file_b64=expected_excel_b64,
    )


def test_no_exallc():
    # 1.
    dataf_with_exallc = pl.DataFrame({"NAME": "my_EXALLC"})

    expected_data = ["my_EXALLC"]
    expected_excel_b64 = definition_checker.write_excel_as_b64(
        dataf_with_exallc, expected_data
    )
    expected_result = definition_checker.Expectation(
        idname="name_any_exallc",
        status=definition_checker.Status.WARNING,
        n_errors=1,
        endpoints_in_error=expected_data,
        data=expected_data,
        excel_file_b64=expected_excel_b64,
    )

    assert expected_result == definition_checker.assess_any_exallc(dataf_with_exallc)

    # 2.
    dataf_no_exallc = pl.DataFrame({"NAME": "my_endpoint"})

    expected_data = []
    expected_excel_b64 = definition_checker.write_excel_as_b64(
        dataf_no_exallc, expected_data
    )
    expected_result = definition_checker.Expectation(
        idname="name_any_exallc",
        status=definition_checker.Status.ALL_GOOD,
        n_errors=0,
        endpoints_in_error=expected_data,
        data=expected_data,
        excel_file_b64=expected_excel_b64,
    )

    assert expected_result == definition_checker.assess_any_exallc(dataf_no_exallc)


def test_no_exmore():
    # 1.
    dataf_with_exmore = pl.DataFrame({"NAME": "my_EXMORE"})

    expected_data = ["my_EXMORE"]
    expected_excel_b64 = definition_checker.write_excel_as_b64(
        dataf_with_exmore, expected_data
    )
    expected_result = definition_checker.Expectation(
        idname="name_any_exmore",
        status=definition_checker.Status.WARNING,
        n_errors=1,
        endpoints_in_error=expected_data,
        data=expected_data,
        excel_file_b64=expected_excel_b64,
    )

    assert expected_result == definition_checker.assess_any_exmore(dataf_with_exmore)

    # 2.
    dataf_no_exmore = pl.DataFrame({"NAME": "my_endpoint"})

    expected_data = []
    expected_excel_b64 = definition_checker.write_excel_as_b64(
        dataf_no_exmore, expected_data
    )
    expected_result = definition_checker.Expectation(
        idname="name_any_exmore",
        status=definition_checker.Status.ALL_GOOD,
        n_errors=0,
        endpoints_in_error=expected_data,
        data=expected_data,
        excel_file_b64=expected_excel_b64,
    )

    assert expected_result == definition_checker.assess_any_exmore(dataf_no_exmore)


def test_cancer_wide__wide_have_basic_endpoints():
    # 1. Bad
    dataf_bad = pl.DataFrame({"NAME": ["my_endpoint_bad_WIDE"]})

    excel_bad = definition_checker.write_excel_as_b64(
        dataf_bad, ["my_endpoint_bad_WIDE"]
    )

    expected_bad = definition_checker.Expectation(
        idname="cancer_wide_has_basic_endpoint",
        status=definition_checker.Status.FAIL,
        n_errors=1,
        endpoints_in_error=["my_endpoint_bad_WIDE"],
        data=[{"wide": "my_endpoint_bad_WIDE", "basic": "my_endpoint_bad"}],
        excel_file_b64=excel_bad,
    )

    assert expected_bad == definition_checker.assess_cancer_wide_have_basic_endpoints(
        dataf_bad,
        set(dataf_bad.get_column("NAME")),
        [["my_endpoint_bad", "my_endpoint_bad_WIDE"]],
    )

    # 2. Good
    dataf_good = pl.DataFrame({"NAME": ["my_endpoint_good_WIDE", "my_endpoint_good"]})

    excel_good = definition_checker.write_excel_as_b64(dataf_good, [])

    expected_good = definition_checker.Expectation(
        idname="cancer_wide_has_basic_endpoint",
        status=definition_checker.Status.ALL_GOOD,
        n_errors=0,
        endpoints_in_error=[],
        data=[],
        excel_file_b64=excel_good,
    )

    assert expected_good == definition_checker.assess_cancer_wide_have_basic_endpoints(
        dataf_good,
        set(dataf_good.get_column("NAME")),
        [["my_endpoint_good_WIDE", "my_endpoint_good"]],
    )


def test_cancer_wide__same_cancer_definition():
    # 1. Bad
    dataf_bad = pl.DataFrame(
        {
            "NAME": ["my_endpoint_WIDE", "my_endpoint"],
            "CANC_TOPO": ["a code", "a DIFFERENT code"],
            "CANC_TOPO_EXCL": [None, None],
            "CANC_MORPH": [None, None],
            "CANC_MORPH_EXCL": [None, None],
            "CANC_BEHAV": [None, None],
        }
    )

    data_bad = [
        {
            "wide": "my_endpoint_WIDE",
            "basic": "my_endpoint",
            "cols_wide": {
                "CANC_TOPO": "a code",
                "CANC_TOPO_EXCL": None,
                "CANC_MORPH": None,
                "CANC_MORPH_EXCL": None,
                "CANC_BEHAV": None,
            },
            "cols_basic": {
                "CANC_TOPO": "a DIFFERENT code",
                "CANC_TOPO_EXCL": None,
                "CANC_MORPH": None,
                "CANC_MORPH_EXCL": None,
                "CANC_BEHAV": None,
            },
            "diff_cols_wide": {"CANC_TOPO": "a code"},
            "diff_cols_basic": {"CANC_TOPO": "a DIFFERENT code"},
            "diffs": {
                "CANC_TOPO": {
                    "string_a": {
                        "original": "a code",
                        "prefix_common": "a ",
                        "middle_diff": "",
                        "suffix_common": " code",
                    },
                    "string_b": {
                        "original": "a DIFFERENT code",
                        "prefix_common": "a ",
                        "middle_diff": "DIFFERENT",
                        "suffix_common": " code",
                    },
                }
            },
        }
    ]

    excel_bad = definition_checker.write_excel_as_b64(
        dataf_bad, ["my_endpoint_WIDE", "my_endpoint"]
    )

    expected_bad = definition_checker.Expectation(
        idname="cancer_wide_same_cancer_definition",
        status=definition_checker.Status.FAIL,
        n_errors=1,
        endpoints_in_error=["my_endpoint_WIDE"],
        data=data_bad,
        excel_file_b64=excel_bad,
    )

    assert expected_bad == definition_checker.assess_cancer_wide_same_cancer_definition(
        dataf_bad, [["my_endpoint", "my_endpoint_WIDE"]], COLUMNS_CANCER
    )

    # 2. Good
    dataf_good = pl.DataFrame(
        {
            "NAME": ["my_endpoint_WIDE", "my_endpoint"],
            "CANC_TOPO": ["same code", "same code"],
            "CANC_TOPO_EXCL": [None, None],
            "CANC_MORPH": [None, None],
            "CANC_MORPH_EXCL": [None, None],
            "CANC_BEHAV": [None, None],
        }
    )

    excel_good = definition_checker.write_excel_as_b64(dataf_good, [])

    expected_good = definition_checker.Expectation(
        idname="cancer_wide_same_cancer_definition",
        status=definition_checker.Status.ALL_GOOD,
        n_errors=0,
        endpoints_in_error=[],
        data=[],
        excel_file_b64=excel_good,
    )

    assert (
        expected_good
        == definition_checker.assess_cancer_wide_same_cancer_definition(
            dataf_good, [["my_endpoint", "my_endpoint_WIDE"]], COLUMNS_CANCER
        )
    )


def test_cancer_wide__same_control_definition():
    # 1. Bad
    dataf_bad = pl.DataFrame(
        {
            "NAME": ["my_endpoint_WIDE", "my_endpoint"],
            "CONTROL_EXCLUDE": ["a code", "a DIFFERENT code"],
            "CONTROL_PRECONDITIONS": [None, None],
            "CONTROL_CONDITIONS": [None, None],
        }
    )

    data_bad = [
        {
            "wide": "my_endpoint_WIDE",
            "basic": "my_endpoint",
            "cols_wide": {
                "CONTROL_EXCLUDE": "a code",
                "CONTROL_PRECONDITIONS": None,
                "CONTROL_CONDITIONS": None,
            },
            "cols_basic": {
                "CONTROL_EXCLUDE": "a DIFFERENT code",
                "CONTROL_PRECONDITIONS": None,
                "CONTROL_CONDITIONS": None,
            },
            "diff_cols_wide": {"CONTROL_EXCLUDE": "a code"},
            "diff_cols_basic": {"CONTROL_EXCLUDE": "a DIFFERENT code"},
            "diffs": {
                "CONTROL_EXCLUDE": {
                    "string_a": {
                        "original": "a code",
                        "prefix_common": "a ",
                        "middle_diff": "",
                        "suffix_common": " code",
                    },
                    "string_b": {
                        "original": "a DIFFERENT code",
                        "prefix_common": "a ",
                        "middle_diff": "DIFFERENT",
                        "suffix_common": " code",
                    },
                }
            },
        }
    ]

    excel_bad = definition_checker.write_excel_as_b64(
        dataf_bad, ["my_endpoint_WIDE", "my_endpoint"]
    )

    expected_bad = definition_checker.Expectation(
        idname="cancer_wide_same_control_definition",
        status=definition_checker.Status.FAIL,
        n_errors=1,
        endpoints_in_error=["my_endpoint_WIDE"],
        data=data_bad,
        excel_file_b64=excel_bad,
    )

    assert (
        expected_bad
        == definition_checker.assess_cancer_wide_same_control_definition(
            dataf_bad, [["my_endpoint", "my_endpoint_WIDE"]], COLUMNS_CONTROL
        )
    )

    # 2. Good
    dataf_good = pl.DataFrame(
        {
            "NAME": ["my_endpoint_WIDE", "my_endpoint"],
            "CONTROL_EXCLUDE": ["same code", "same code"],
            "CONTROL_PRECONDITIONS": [None, None],
            "CONTROL_CONDITIONS": [None, None],
        }
    )

    excel_good = definition_checker.write_excel_as_b64(dataf_good, [])

    expected_good = definition_checker.Expectation(
        idname="cancer_wide_same_control_definition",
        status=definition_checker.Status.ALL_GOOD,
        n_errors=0,
        endpoints_in_error=[],
        data=[],
        excel_file_b64=excel_good,
    )

    assert (
        expected_good
        == definition_checker.assess_cancer_wide_same_control_definition(
            dataf_good, [["my_endpoint", "my_endpoint_WIDE"]], COLUMNS_CONTROL
        )
    )


def test_cancer_wide__wide_have_hilmo():
    # 1.
    dataf_bad = pl.DataFrame(
        {
            "NAME": "my_endpoint_bad",
            "HD_ICD_10": None,
            "HD_ICD_9": None,
            "HD_ICD_8": None,
            "HD_ICD_10_EXCL": None,
            "HD_ICD_9_EXCL": None,
            "HD_ICD_8_EXCL": None,
            "INCLUDE": None,
        }
    )

    excel_bad = definition_checker.write_excel_as_b64(dataf_bad, ["my_endpoint_bad"])

    expected_bad = definition_checker.Expectation(
        idname="cancer_wide_have_hilmo_definition",
        status=definition_checker.Status.FAIL,
        n_errors=1,
        endpoints_in_error=["my_endpoint_bad"],
        data=[
            {
                "endpoint": "my_endpoint_bad",
                "descendants": set(),
                "table": {
                    "my_endpoint_bad": {
                        "HD_ICD_10": None,
                        "HD_ICD_9": None,
                        "HD_ICD_8": None,
                        "HD_ICD_10_EXCL": None,
                        "HD_ICD_9_EXCL": None,
                        "HD_ICD_8_EXCL": None,
                    }
                },
            }
        ],
        excel_file_b64=excel_bad,
    )

    assert expected_bad == definition_checker.assess_cancer_wide_have_hilmo(
        dataf_bad, ["my_endpoint_bad"]
    )

    # 2.
    dataf_good = pl.DataFrame(
        {
            "NAME": "my_endpoint_good",
            "HD_ICD_10": "some Hilmo code",
            "HD_ICD_9": None,
            "HD_ICD_8": None,
            "HD_ICD_10_EXCL": None,
            "HD_ICD_9_EXCL": None,
            "HD_ICD_8_EXCL": None,
            "INCLUDE": None,
        }
    )

    excel_good = definition_checker.write_excel_as_b64(dataf_good, [])

    expected_good = definition_checker.Expectation(
        idname="cancer_wide_have_hilmo_definition",
        status=definition_checker.Status.ALL_GOOD,
        n_errors=0,
        endpoints_in_error=[],
        data=[],
        excel_file_b64=excel_good,
    )

    assert expected_good == definition_checker.assess_cancer_wide_have_hilmo(
        dataf_good, ["my_endpoint_good"]
    )


def test_wide_cancer__basic_have_no_hilmo():
    # 1. Bad
    dataf_bad = pl.DataFrame(
        {
            "NAME": "my_endpoint_bad",
            "HD_ICD_10": "some unexpected code",
            "HD_ICD_9": None,
            "HD_ICD_8": None,
            "HD_ICD_10_EXCL": None,
            "HD_ICD_9_EXCL": None,
            "HD_ICD_8_EXCL": None,
            "INCLUDE": None,
        }
    )

    excel_bad = definition_checker.write_excel_as_b64(dataf_bad, ["my_endpoint_bad"])

    expected_bad = definition_checker.Expectation(
        idname="cancer_wide_basic_have_no_hilmo_definition",
        status=definition_checker.Status.FAIL,
        n_errors=1,
        endpoints_in_error=["my_endpoint_bad"],
        data=[
            {
                "endpoint": "my_endpoint_bad",
                "descendants": set(),
                "table": {
                    "my_endpoint_bad": {
                        "HD_ICD_10": "some unexpected code",
                        "HD_ICD_9": None,
                        "HD_ICD_8": None,
                        "HD_ICD_10_EXCL": None,
                        "HD_ICD_9_EXCL": None,
                        "HD_ICD_8_EXCL": None,
                    }
                },
            }
        ],
        excel_file_b64=excel_bad,
    )

    assert expected_bad == definition_checker.assess_cancer_wide_basic_have_no_hilmo(
        dataf_bad, ["my_endpoint_bad"]
    )

    # 2. Good
    dataf_good = pl.DataFrame(
        {
            "NAME": "my_endpoint_good",
            "HD_ICD_10": None,
            "HD_ICD_9": None,
            "HD_ICD_8": None,
            "HD_ICD_10_EXCL": None,
            "HD_ICD_9_EXCL": None,
            "HD_ICD_8_EXCL": None,
            "INCLUDE": None,
        }
    )

    excel_good = definition_checker.write_excel_as_b64(dataf_good, [])

    expected_good = definition_checker.Expectation(
        idname="cancer_wide_basic_have_no_hilmo_definition",
        status=definition_checker.Status.ALL_GOOD,
        n_errors=0,
        endpoints_in_error=[],
        data=[],
        excel_file_b64=excel_good,
    )

    assert expected_good == definition_checker.assess_cancer_wide_basic_have_no_hilmo(
        dataf_good, ["my_endpoint_good"]
    )


def test_util_rec_targets_of():
    map_node_targets = {
        "GrandParent1": ["Parent1", "Parent2", "Parent3"],
        "GrandParent2": ["Parent3"],
        # Parent1 : intentionnaly missing
        "Parent2": ["Child1", "Child2"],
        "Parent3": ["Child3"],
    }

    gp1_expected = set(["Parent1", "Parent2", "Parent3", "Child1", "Child2", "Child3"])
    assert gp1_expected == definition_checker.rec_targets_of(
        "GrandParent1", map_node_targets
    )

    gp2_expected = set(["Parent3", "Child3"])
    assert gp2_expected == definition_checker.rec_targets_of(
        "GrandParent2", map_node_targets
    )

    p1_expected = set()
    assert p1_expected == definition_checker.rec_targets_of("Parent1", map_node_targets)

    p2_expected = set(["Child1", "Child2"])
    assert p2_expected == definition_checker.rec_targets_of("Parent2", map_node_targets)

    p3_expected = set(["Child3"])
    assert p3_expected == definition_checker.rec_targets_of("Parent3", map_node_targets)

    c1_expected = set()
    assert c1_expected == definition_checker.rec_targets_of("Child1", map_node_targets)

    c2_expected = set()
    assert c2_expected == definition_checker.rec_targets_of("Child2", map_node_targets)

    c3_expected = set()
    assert c3_expected == definition_checker.rec_targets_of("Child3", map_node_targets)


def test_regression__wide_have_hilmo_not_triggering():
    # NOTE(Vincent 2025-05-27)  Bug was that the "wide have hilmo" check was not triggering
    # when there was no basic endpoint for a wide endpoint.
    dataf = pl.DataFrame(
        {
            "NAME": ["my_endpoint_WIDE", "my_endpoint"],
            "INCLUDE": [None, None],
            "HD_ICD_10": [None, None],
            "HD_ICD_9": [None, None],
            "HD_ICD_8": [None, None],
            "HD_ICD_10_EXCL": [None, None],
            "HD_ICD_9_EXCL": [None, None],
            "HD_ICD_8_EXCL": [None, None],
            "CANC_TOPO": [None, None],
            "CANC_TOPO_EXCL": [None, None],
            "CANC_MORPH": [None, None],
            "CANC_MORPH_EXCL": [None, None],
            "CANC_BEHAV": [None, None],
            "CONTROL_EXCLUDE": [None, None],
            "CONTROL_PRECONDITIONS": [None, None],
            "CONTROL_CONDITIONS": [None, None],
        }
    )

    data_expected = [
        {
            "endpoint": "my_endpoint_WIDE",
            "descendants": set(),
            "table": {
                "my_endpoint_WIDE": {
                    "HD_ICD_10": None,
                    "HD_ICD_9": None,
                    "HD_ICD_8": None,
                    "HD_ICD_10_EXCL": None,
                    "HD_ICD_9_EXCL": None,
                    "HD_ICD_8_EXCL": None,
                }
            },
        }
    ]

    excel_b64_expected = definition_checker.write_excel_as_b64(
        dataf, ["my_endpoint_WIDE"]
    )

    expected = definition_checker.Expectation(
        idname="cancer_wide_have_hilmo_definition",
        status=definition_checker.Status.FAIL,
        n_errors=1,
        endpoints_in_error=["my_endpoint_WIDE"],
        data=data_expected,
        excel_file_b64=excel_b64_expected,
    )

    triggered_expectation = None
    for xx in definition_checker.assess_wide_cancer_endpoints(dataf):
        if xx.idname == "cancer_wide_have_hilmo_definition":
            triggered_expectation = xx

    assert expected == triggered_expectation
