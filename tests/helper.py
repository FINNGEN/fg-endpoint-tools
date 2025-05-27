def nullify_excel(expectation, *more_expectations):
    """Remove the Excel file attribute from Expectation(s).

    This is useful when we want to compare Expectations, for example in tests, since the
    Excel files created with `xlsxwriter` could differ only by their metadata (usually
    the `created` and `modified` properties) while still having the same content.
    Ideally we would just strip these metadata from the Excel documents so that we could
    still compare the Excel content, but it does not appear to be possible with
    `xlsxwriter`.
    """
    all_expectations = [expectation]

    if more_expectations:
        all_expectations += more_expectations

    for xx in all_expectations:
        xx.excel_file_b64 = ""
