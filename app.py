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
#  prefix 抽出関数（★ここがめちゃ重要★）
# ======================================================

def extract_prefix_real(filename):
    """実写: 20241114_0250.jpg → 20241114_0250"""
    return os.path.splitext(filename)[0]


def extract_prefix_synth(filename):
    """
    生成画像:
      20241114_0250_r14_FLDK_06_04_05_synthesized_image.jpg
    → 20241114_0250 を返す
    """
    base = os.path.splitext(filename)[0]
    parts = base.split("_")

    # ["20241114", "0250", "r14", ...] の構造なので先頭2つを使う
    if len(parts) >= 2:
        return parts[0] + "_" + parts[1]
    return None


# ======================================================
#  高速版：アプリ起動時に一度だけペア生成
# ======================================================
def build_pairs():
    real_files = os.listdir(REAL_FOLDER)
    synth_files = os.listdir(SYNTH_FOLDER)

    # 生成画像 prefix → ファイル名 の辞書
    synth_dict = {}
    for s in synth_files:
        p = extract_prefix_synth(s)
        if p:
            synth_dict[p] = s

    pairs = []
    for real in real_files:
        real_prefix = extract_prefix_real(real)
        if real_prefix in synth_dict:
            pairs.append({
                "prefix": real_prefix,
                "real": real,
                "synth": synth_dict[real_prefix]
            })

    return pairs


# アプリ起動時に1度だけ実行（高速）
ALL_PAIRS = build_pairs()
print("PAIR COUNT:", len(ALL_PAIRS))


# ======================================================
#  ルーティング
# ======================================================
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/survey/<int:grade>", methods=["GET", "POST"])
def survey(grade):

    # --- 初回アクセス（GET または current 未定義） ---
    if request.method == "GET" or session.get("current") is None:
        session["grade"] = grade
        session["current"] = 0
        session["responses"] = []

        session["pairs"] = random.sample(
            ALL_PAIRS,
            min(NUM_QUESTIONS, len(ALL_PAIRS))
        )

    current = session.get("current", 0)
    responses = session.get("responses", [])

    # --- POSTでの回答処理 ---
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

    # --- 全回答終了 ---
    if current >= len(session["pairs"]):
        df = pd.DataFrame(responses)

        # --------------------------
        #  Google Sheet へ保存処理
        # --------------------------
        SHEET_NAME = "アンケート結果"
        SPREADSHEET_ID = "150Qv1M4eRfaNJQnznln1SnUC4yVqFKTFhI0EOjcb2Ak"
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        creds_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        gc = gspread.authorize(creds)

        sh = gc.open_by_key(SPREADSHEET_ID)
        try:
            worksheet = sh.worksheet(SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=SHEET_NAME, rows="100", cols="10")

        import pytz
        jst = datetime.now(pytz.timezone("Asia/Tokyo"))
        df.insert(0, "timestamp", jst.strftime("%Y-%m-%d %H:%M:%S"))

        values = [df.columns.values.tolist()] + df.values.tolist()
        worksheet.append_rows(values)

        return render_template("done.html")

    # --- 次の質問表示 ---
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
