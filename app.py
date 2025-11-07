from flask import Flask, render_template, request, redirect, url_for, session
import os, random
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret_key_for_session"

REAL_FOLDER = "static/chichi_img"
SYNTH_FOLDER = "static/images"
RESULT_XLSX = "results.xlsx"
NUM_QUESTIONS = 10

# ---------- ファイルペア作成 ----------
# ---------- ファイルペア作成（同じプレフィックスを含むものを対応） ----------
def make_pairs():
    real_files = os.listdir(REAL_FOLDER)
    synth_files = os.listdir(SYNTH_FOLDER)

    pairs = []
    for real in real_files:
        real_prefix = os.path.splitext(real)[0]
        # synth 側に同じプレフィックスを含むものがあればペアにする
        match = next((s for s in synth_files if real_prefix in s), None)
        if match:
            pairs.append({
                "prefix": real_prefix,
                "real": real,
                "synth": match
            })
    return pairs

# 🔽 この行を忘れずに！
pairs = make_pairs()
print(f"共通ペア数: {len(pairs)}")

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

    # ✅ すべての質問が終わった場合の処理
    if current >= len(session["pairs"]):
        from datetime import datetime
        import openpyxl

        df = pd.DataFrame(responses)
        sheet_name = datetime.now().strftime("%Y-%m-%d")

        if os.path.exists(RESULT_XLSX):
            with pd.ExcelWriter(RESULT_XLSX, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
                existing_sheets = writer.book.sheetnames
                if sheet_name in existing_sheets:
                    i = 1
                    while f"{sheet_name}_{i}" in existing_sheets:
                        i += 1
                    sheet_name = f"{sheet_name}_{i}"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            df.to_excel(RESULT_XLSX, sheet_name=sheet_name, index=False)

        return render_template("done.html")

    # ✅ まだ質問が残っている場合の処理
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
