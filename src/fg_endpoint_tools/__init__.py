from argparse import ArgumentParser
from pathlib import Path

from . import definition_checker


def main() -> None:
    args = init_cli()

    dataf = definition_checker.read_definitions_excel(args.definitions_excel_file)

    report = definition_checker.collect_report(dataf)
    for key, val in report.items():
        print(f"~~~ {key} ~~~")
        print(val)
        print()

    definition_checker.write_html_report(args.output_html, context=report)


def init_cli():
    parser = ArgumentParser()

    parser.add_argument(
        "--definitions-excel-file",
        help="Path to the definitions file in Excel format",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output-html", help="Path to write the HTML report", required=True, type=Path
    )

    args = parser.parse_args()
    return args
