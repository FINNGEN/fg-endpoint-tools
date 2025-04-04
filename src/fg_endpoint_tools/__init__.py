import json
from argparse import ArgumentParser
from pathlib import Path

from . import definition_checker


def main() -> None:
    args = init_cli()

    dataf = definition_checker.read_definitions_excel(args.definitions_excel_file)
    print("Summary")
    print(json.dumps(definition_checker.get_summary(dataf), indent=2))
    print()
    print("Dups?")
    print(json.dumps(definition_checker.find_duplicates_by_name(dataf), indent=2))
    print()
    print("Any _EXALLC?")
    print(json.dumps(definition_checker.find_any_exallc(dataf), indent=2))
    print()
    print("Any _EXMORE?")
    print(json.dumps(definition_checker.find_any_exmore(dataf), indent=2))
    print()
    print("Breaking assumptions of _WIDE endpoints")
    print(json.dumps(definition_checker.check_wide_cancer_endpoints(dataf), indent=2))


def init_cli():
    parser = ArgumentParser()

    parser.add_argument(
        "--definitions-excel-file",
        help="Path to the definitions file in Excel format",
        required=True,
        type=Path,
    )

    args = parser.parse_args()
    return args
