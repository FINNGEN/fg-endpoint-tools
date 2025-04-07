from datetime import datetime
from io import BytesIO

from flask import Flask
from flask import render_template
from flask import request

from . import definition_checker


app = Flask(__name__)


@app.route("/")
def serve_home():
    return render_template('home.html')


@app.route("/definition-checker", methods=["POST"])
def serve_definition_checker():
    file = request.files['file']

    file_as_bytes = BytesIO()
    file.save(file_as_bytes)
    report = definition_checker.collect_report(file_as_bytes)
    
    context = {
        "file_name": file.filename,
        "run_datetime": get_current_time(),
        "myobj": {"keya": 54}
    }

    context |= report

    print(context["summary"])

    return render_template('report.html', **context)


def get_current_time() -> str:
    return datetime.now().isoformat()
