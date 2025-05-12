from datetime import datetime
from io import BytesIO

from flask import Flask
from flask import redirect
from flask import render_template
from flask import request

from . import definition_checker


app = Flask(__name__)


@app.route("/")
def redir():
    return redirect("/definition-checker/")


@app.route("/definition-checker/", methods=["GET"])
def serve_definition_checker_home():
    return render_template("home.html")


@app.route("/definition-checker/", methods=["POST"])
def serve_definition_checker_report():
    file = request.files["file"]

    file_as_bytes = BytesIO()
    file.save(file_as_bytes)
    report = definition_checker.collect_report(file_as_bytes)

    for _expectation_id, expectation in report["expectations"].items():
        if expectation.status == definition_checker.Status.ALL_GOOD:
            expectation.html_view["class_check_open"] = "closed"
        else:
            expectation.html_view["class_check_open"] = "preview"

    context = {
        "file_name": file.filename,
        "run_datetime": get_current_time(),
    }

    context |= report

    context["status_counts"] = status_counts(report)

    return render_template("report.html", **context)


def get_current_time() -> str:
    now = datetime.now()
    now_as_str = now.strftime("%c")
    return now_as_str


def status_counts(report) -> dict[definition_checker.Status, int]:
    all_status = map(lambda xx: xx.status, report["expectations"].values())

    counts = {ss: 0 for ss in definition_checker.Status}
    for ss in all_status:
        counts[ss] += 1

    return counts
