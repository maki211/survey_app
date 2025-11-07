from flask import Flask, render_template, request, redirect, url_for, session
import os, random
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import os


app = Flask(__name__)
app.secret_key = "secret_key_for_session"

REAL_FOLDER = "static/chichi_img"
SYNTH_FOLDER = "static/images"
RESULT_XLSX = "results.xlsx"
NUM_QUESTIONS = 10


def make_pairs():
    real_files = os.listdir(REAL_FOLDER)
    synth_files = os.listdir(SYNTH_FOLDER)

    pairs = []
    for real in real_files:
        real_prefix = os.path.splitext(real)[0]
        match = next((s for s in synth_files if real_prefix in s), None)
        if match:
            pairs.append({
                "prefix": real_prefix,
                "real": real,
                "synth": match
            })
    return pairs

pairs = make_pairs()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session["grade"] = request.form.get("grade")
        session["pairs"] = random.sample(pairs, min(NUM_QUESTIONS, len(pairs)))
        session["current"] = 0
        session["responses"] = []
        return redirect(url_for("survey"))

    grades = ["本科1", "本科2", "本科3", "本科4", "本科5", "専攻科1", "専攻科2"]
    return render_template("survey.html", stage="grade", grades=grades)


@app.route("/survey", methods=["GET", "POST"])
def survey():
    current = session.get("current", 0)
    responses = session.get("responses", [])

    if request.method == "POST" and current > 0:
        sim = request.form.get("similarity")
        weather = request.form.get("weather")
        if sim is None or weather is None:
            return "全ての選択肢を選んでください", 400

        pair = session["pairs"][current - 1]
        responses.append({
            "grade": session["grade"],
            "prefix": pair["prefix"],
            "real": pair["real"],
            "synth": pair["synth"],
            "similarity": sim,
            "weather": weather
        })
        session["responses"] = responses


    if current >= len(session["pairs"]):
        df = pd.DataFrame(responses)

        # ===== Google Sheets に追記 =====
        SHEET_NAME = "アンケート結果"
        SPREADSHEET_ID = "150Qv1M4eRfaNJQnznln1SnUC4yVqFKTFhI0EOjcb2Ak"

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        # 🔽 Render 環境変数から credentials を取得
        creds_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        gc = gspread.authorize(creds)

        sh = gc.open_by_key(SPREADSHEET_ID)
        try:
            worksheet = sh.worksheet(SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=SHEET_NAME, rows="100", cols="10")

        df.insert(0, "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        values = [df.columns.values.tolist()] + df.values.tolist()
        worksheet.append_rows(values)

        return render_template("done.html")


    pair = session["pairs"][current]
    session["current"] = current + 1

    return render_template(
        "survey.html",
        stage="survey",
        real_img=pair["real"],
        synth_img=pair["synth"],
        prefix=pair["prefix"],
        question_num=current + 1,
        total=len(session["pairs"])
    )


if __name__ == "__main__":
    app.run(debug=True)
