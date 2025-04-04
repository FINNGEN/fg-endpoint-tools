import polars as pl

from fg_endpoint_tools import definition_checker


def test_duplicate_endpoint_name():
    dataf_with_dups = pl.DataFrame(
        {"NAME": ["my_endpoint", "another_endpoint", "my_endpoint"]}
    )

    dataf_no_dups = pl.DataFrame({"NAME": ["first_endpoint", "second_endpoint"]})

    assert ["my_endpoint"] == definition_checker.find_duplicates_by_name(
        dataf_with_dups
    )
    assert [] == definition_checker.find_duplicates_by_name(dataf_no_dups)


def test_no_exallc():
    dataf_with_exallc = pl.DataFrame({"NAME": "my_EXALLC"})

    dataf_no_exallc = pl.DataFrame({"NAME": "my_endpoint"})

    assert ["my_EXALLC"] == definition_checker.find_any_exallc(dataf_with_exallc)
    assert [] == definition_checker.find_any_exallc(dataf_no_exallc)


def test_no_exmore():
    dataf_with_exmore = pl.DataFrame({"NAME": "my_EXMORE"})

    dataf_no_exmore = pl.DataFrame({"NAME": "my_endpoint"})

    assert ["my_EXMORE"] == definition_checker.find_any_exmore(dataf_with_exmore)
    assert [] == definition_checker.find_any_exmore(dataf_no_exmore)


def test_wide_cancer_endpoints__good_definitions():
    endpoint_basic = {
        "NAME": "my_endpoint",
        # Hilmo case definition
        "HD_ICD_10": None,
        "HD_ICD_9": None,
        "HD_ICD_8": None,
        "HD_ICD_10_EXCL": None,
        "HD_ICD_9_EXCL": None,
        "HD_ICD_8_EXCL": None,
        # Cancer case definition
        "CANC_TOPO": "some_canc_topo",
        "CANC_TOPO_EXCL": "some_canc_topo_excl",
        "CANC_MORPH": "some_canc_morph",
        "CANC_MORPH_EXCL": "some_canc_morph_excl",
        "CANC_BEHAV": "some_canc_behav",
        # Control definition
        "CONTROL_EXCLUDE": "some_control_exclude",
        "CONTROL_PRECONDITIONS": "some_control_preconditions",
        "CONTROL_CONDITIONS": "some_control_conditions",
    }

    endpoint_wide = {
        "NAME": "my_endpoint_WIDE",
        # Hilmo case definition
        "HD_ICD_10": "some_hd_icd_10",
        "HD_ICD_9": "some_hd_icd_9",
        "HD_ICD_8": "some_hd_icd_8",
        "HD_ICD_10_EXCL": "some_hd_icd_10_excl",
        "HD_ICD_9_EXCL": "some_hd_icd_9_excl",
        "HD_ICD_8_EXCL": "some_hd_icd_8_excl",
        # Cancer case definition
        "CANC_TOPO": "some_canc_topo",
        "CANC_TOPO_EXCL": "some_canc_topo_excl",
        "CANC_MORPH": "some_canc_morph",
        "CANC_MORPH_EXCL": "some_canc_morph_excl",
        "CANC_BEHAV": "some_canc_behav",
        # Control definition
        "CONTROL_EXCLUDE": "some_control_exclude",
        "CONTROL_PRECONDITIONS": "some_control_preconditions",
        "CONTROL_CONDITIONS": "some_control_conditions",
    }

    dataf = pl.from_dicts([endpoint_basic, endpoint_wide])

    expected = []
    actual = definition_checker.check_wide_cancer_endpoints(dataf)

    assert expected == actual


def test_wide_cancer_endpoints__bad_basic_definition():
    endpoint_basic = {
        "NAME": "my_endpoint",
        # Hilmo case definition
        "HD_ICD_10": "should be empty",  # <-- introduced bad value here
        "HD_ICD_9": None,
        "HD_ICD_8": None,
        "HD_ICD_10_EXCL": None,
        "HD_ICD_9_EXCL": None,
        "HD_ICD_8_EXCL": None,
        # Cancer case definition
        "CANC_TOPO": "ANOTHER_canc_topo",  # <-- introduced bad value here
        "CANC_TOPO_EXCL": "some_canc_topo_excl",
        "CANC_MORPH": "some_canc_morph",
        "CANC_MORPH_EXCL": "some_canc_morph_excl",
        "CANC_BEHAV": "some_canc_behav",
        # Control definition
        "CONTROL_EXCLUDE": "ANOTHER_control_exclude",  # <-- introduced bad value here
        "CONTROL_PRECONDITIONS": "some_control_preconditions",
        "CONTROL_CONDITIONS": "some_control_conditions",
    }

    endpoint_wide = {
        "NAME": "my_endpoint_WIDE",
        # Hilmo case definition
        "HD_ICD_10": "some_hd_icd_10",
        "HD_ICD_9": "some_hd_icd_9",
        "HD_ICD_8": "some_hd_icd_8",
        "HD_ICD_10_EXCL": "some_hd_icd_10_excl",
        "HD_ICD_9_EXCL": "some_hd_icd_9_excl",
        "HD_ICD_8_EXCL": "some_hd_icd_8_excl",
        # Cancer case definition
        "CANC_TOPO": "some_canc_topo",
        "CANC_TOPO_EXCL": "some_canc_topo_excl",
        "CANC_MORPH": "some_canc_morph",
        "CANC_MORPH_EXCL": "some_canc_morph_excl",
        "CANC_BEHAV": "some_canc_behav",
        # Control definition
        "CONTROL_EXCLUDE": "some_control_exclude",
        "CONTROL_PRECONDITIONS": "some_control_preconditions",
        "CONTROL_CONDITIONS": "some_control_conditions",
    }

    dataf = pl.from_dicts([endpoint_basic, endpoint_wide])

    expected = [
        {
            "basic": "my_endpoint",
            "wide": "my_endpoint_WIDE",
            "have_same_cancer_definition": False,
            "wide_has_hilmo_definition": True,
            "basic_has_hilmo_definition": True,
            "have_same_control_definition": False,
        }
    ]
    actual = definition_checker.check_wide_cancer_endpoints(dataf)

    assert expected == actual


def test_wide_cancer_endpoints__bad_wide_definition():
    endpoint_basic = {
        "NAME": "my_endpoint",
        # Hilmo case definition
        "HD_ICD_10": None,
        "HD_ICD_9": None,
        "HD_ICD_8": None,
        "HD_ICD_10_EXCL": None,
        "HD_ICD_9_EXCL": None,
        "HD_ICD_8_EXCL": None,
        # Cancer case definition
        "CANC_TOPO": "some_canc_topo",
        "CANC_TOPO_EXCL": "some_canc_topo_excl",
        "CANC_MORPH": "some_canc_morph",
        "CANC_MORPH_EXCL": "some_canc_morph_excl",
        "CANC_BEHAV": "some_canc_behav",
        # Control definition
        "CONTROL_EXCLUDE": "some_control_exclude",
        "CONTROL_PRECONDITIONS": "some_control_preconditions",
        "CONTROL_CONDITIONS": "some_control_conditions",
    }

    endpoint_wide = {
        "NAME": "my_endpoint_WIDE",
        # Hilmo case definition
        "HD_ICD_10": None,
        "HD_ICD_9": None,
        "HD_ICD_8": None,
        "HD_ICD_10_EXCL": None,
        "HD_ICD_9_EXCL": None,
        "HD_ICD_8_EXCL": None,
        # Cancer case definition
        "CANC_TOPO": "ANOTHER_canc_topo",
        "CANC_TOPO_EXCL": "some_canc_topo_excl",
        "CANC_MORPH": "some_canc_morph",
        "CANC_MORPH_EXCL": "some_canc_morph_excl",
        "CANC_BEHAV": "some_canc_behav",
        # Control definition
        "CONTROL_EXCLUDE": "ANOTHER_control_exclude",
        "CONTROL_PRECONDITIONS": "some_control_preconditions",
        "CONTROL_CONDITIONS": "some_control_conditions",
    }

    dataf = pl.from_dicts([endpoint_basic, endpoint_wide])

    expected = [
        {
            "basic": "my_endpoint",
            "wide": "my_endpoint_WIDE",
            "have_same_cancer_definition": False,
            "wide_has_hilmo_definition": False,
            "basic_has_hilmo_definition": False,
            "have_same_control_definition": False,
        }
    ]
    actual = definition_checker.check_wide_cancer_endpoints(dataf)

    assert expected == actual


def test_wide_cancer_endpoints__missing_basic():
    endpoint_wide = {
        "NAME": "my_endpoint_WIDE",
        # Hilmo case definition
        "HD_ICD_10": "some_hd_icd_10",
        "HD_ICD_9": "some_hd_icd_9",
        "HD_ICD_8": "some_hd_icd_8",
        "HD_ICD_10_EXCL": "some_hd_icd_10_excl",
        "HD_ICD_9_EXCL": "some_hd_icd_9_excl",
        "HD_ICD_8_EXCL": "some_hd_icd_8_excl",
        # Cancer case definition
        "CANC_TOPO": "some_canc_topo",
        "CANC_TOPO_EXCL": "some_canc_topo_excl",
        "CANC_MORPH": "some_canc_morph",
        "CANC_MORPH_EXCL": "some_canc_morph_excl",
        "CANC_BEHAV": "some_canc_behav",
        # Control definition
        "CONTROL_EXCLUDE": "some_control_exclude",
        "CONTROL_PRECONDITIONS": "some_control_preconditions",
        "CONTROL_CONDITIONS": "some_control_conditions",
    }

    dataf = pl.from_dicts([endpoint_wide])

    expected = [
        {
            "basic": None,
            "wide": "my_endpoint_WIDE",
            "have_same_cancer_definition": None,
            "wide_has_hilmo_definition": None,
            "basic_has_hilmo_definition": None,
            "have_same_control_definition": None,
        }
    ]
    actual = definition_checker.check_wide_cancer_endpoints(dataf)

    assert expected == actual
