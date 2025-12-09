from flask import Flask, render_template, request, redirect, url_for, session
import os, random
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

app = Flask(__name__)
app.secret_key = "secret_key_for_session"

REAL_FOLDER = "static/chichi_img"
SYNTH_FOLDER = "static/images"
NUM_QUESTIONS = 10


# ======================================================
#  高速版：アプリ起動時に一度だけペアを作成（超重要）
# ======================================================
def build_pairs():
    real_files = os.listdir(REAL_FOLDER)
    synth_files = os.listdir(SYNTH_FOLDER)

    # prefix をキーにした辞書（高速検索）
    synth_dict = {os.path.splitext(s)[0]: s for s in synth_files}

    pairs = []
    for real in real_files:
        prefix = os.path.splitext(real)[0]
        if prefix in synth_dict:
            pairs.append({
                "prefix": prefix,
                "real": real,
                "synth": synth_dict[prefix]
            })

    return pairs


# アプリ起動時に一度だけ構築 → 毎回 0.00 秒でアクセス可能
ALL_PAIRS = build_pairs()
print("PAIR COUNT:", len(ALL_PAIRS))


# ======================================================
#  ルーティング
# ======================================================
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route("/survey/<int:grade>", methods=["GET", "POST"])
def survey(grade):

    print("---- ACCESS /survey ----")
    print("method:", request.method)
    print("session grade:", session.get("grade"))
    print("session current:", session.get("current"))
    print("session pairs exist:", "pairs" in session)
    print("-------------------------")

    # 最初のアクセス（GET または current が None または存在しない）
    if request.method == "GET" or session.get("current") is None:
        print(">>> INITIALIZE SESSION <<<")
        session["grade"] = grade
        session["current"] = 0
        session["responses"] = []
        session["pairs"] = random.sample(
            ALL_PAIRS,
            min(NUM_QUESTIONS, len(ALL_PAIRS))
        )

    # --- 最初のアクセス（POSTではなく current が 0 か responses が空） ---
    if request.method == "GET" or session.get("current") is None:
        session["grade"] = grade
        session["current"] = 0
        session["responses"] = []

        # ペアの再生成
        session["pairs"] = random.sample(
            ALL_PAIRS,
            min(NUM_QUESTIONS, len(ALL_PAIRS))
        )

    current = session.get("current", 0)
    responses = session.get("responses", [])

    # --- 回答処理 ---
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

    # --- 最後の質問終了 ---
    if current >= len(session["pairs"]):
        df = pd.DataFrame(responses)
        ...
        return render_template("done.html")

    # --- 次の問題 ---
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


@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")


if __name__ == "__main__":
    app.run(debug=True)
