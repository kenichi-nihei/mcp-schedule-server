from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
import urllib.parse
import openai
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

openai.api_key = os.getenv("OPENAI_API_KEY")  # 環境変数に登録しておくこと

# ✅ 日時候補をGPTから抽出
def extract_datetime_candidates(email_body: str) -> List[str]:
    prompt = f"""
以下のメール本文から、打ち合わせ候補日時を ISO8601形式（例: 2024-05-15T15:00:00）で最大3件抽出してください。
本文:
{email_body}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    lines = response["choices"][0]["message"]["content"].splitlines()
    return [line.strip() for line in lines if line.strip()]

# ✅ /contextエンドポイント：メール受信時に呼び出される
@app.post("/context")
async def receive_context(request: Request):
    body = await request.json()
    email = body["context"]["email"]
    subject = email["subject"]
    email_body = email["body"]

    print("✅ 受信データ:", email)

    # GPTで日時候補を抽出
    candidates = extract_datetime_candidates(email_body)

    # クエリパラメータ用にエンコード
    encoded_candidates = urllib.parse.urlencode([
        ("candidates", dt) for dt in candidates
    ])
    encoded_body = urllib.parse.quote(subject)

    return {
        "candidates": candidates,
        "ui_url": f"https://mcp-schedule-server.onrender.com/choose?{encoded_candidates}&body={encoded_body}"
    }

# ✅ /chooseエンドポイント：候補日時を選ぶ画面
@app.get("/choose", response_class=HTMLResponse)
async def choose_get(
    request: Request,
    candidates: List[str] = Query(default=[]),
    body: str = ""
):
    return templates.TemplateResponse("choose.html", {
        "request": request,
        "candidates": candidates,
        "body": body
    })

from fastapi.responses import RedirectResponse

@app.post("/choose")
async def choose_post(request: Request):
    form = await request.form()
    selected = form.get("selected", "")
    body = form.get("body", "")

    # 予定作成画面のURLを生成（仮）
    outlook_url = (
        f"https://outlook.office.com/calendar/0/deeplink/compose?"
        f"subject=打ち合わせ&body={urllib.parse.quote(body)}&startdt={selected}"
    )

    # ユーザーを予定作成画面にリダイレクト
    return RedirectResponse(outlook_url, status_code=302)
