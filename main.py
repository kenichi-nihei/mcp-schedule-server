from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
import urllib.parse
import os

from openai import OpenAI

# FastAPI アプリとテンプレート設定
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# OpenAI API クライアントの初期化（APIキーはRenderの環境変数から取得）
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ GPT で日時候補を抽出
def extract_datetime_candidates(email_body: str) -> List[str]:
    prompt = f"""
以下のメール本文から、打ち合わせ候補日時を ISO8601形式（例: 2024-05-15T15:00:00）で最大3件抽出してください。
本文:
{email_body}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",  # 必要に応じて gpt-3.5-turbo に変更
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        lines = content.splitlines()
        return [line.strip() for line in lines if line.strip()]
    except Exception as e:
        print("❌ GPT呼び出しエラー:", e)
        return []

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
    print("✅ GPT抽出候補日時:", candidates)

    # クエリパラメータ用にエンコード
    encoded_candidates = urllib.parse.urlencode([
        ("candidates", dt) for dt in candidates
    ])
    encoded_body = urllib.parse.quote(subject)

    return {
        "candidates": candidates,
        "ui_url": f"https://mcp-schedule-server.onrender.com/choose?{encoded_candidates}&body={encoded_body}"
    }

# ✅ /choose（GET）：候補日時を選ぶ画面
@app.get("/choose", response_class=HTMLResponse)
async def choose_get(
    request: Request,
    candidates: List[str] = Query(default=[]),
    conflicts: List[str] = Query(default=[]),
    subject: str = "",
    from_: str = Query(alias="from", default=""),
    body: str = "",
    cc: str = ""
):
    # ← ここで見やすい形式に整形
    cc_display = ", ".join(cc.split(",")) if cc else ""

    return templates.TemplateResponse("choose.html", {
        "request": request,
        "candidates": candidates,
        "conflicts": conflicts,
        "subject": subject,
        "from_": from_,
        "body": body,
        "cc": cc_display,  # ← 表示用に整形されたccを渡す
    })

# ✅ /choose（POST）：選択後に予定作成画面へリダイレクト
@app.post("/choose")
async def choose_post(request: Request):
    form = await request.form()
    selected = form.get("selected", "")
    body = form.get("body", "")

    # Outlook予定作成画面のURL生成
    outlook_url = (
        f"https://outlook.office.com/calendar/0/deeplink/compose?"
        f"subject=打ち合わせ&body={urllib.parse.quote(body)}&startdt={selected}"
    )

    return RedirectResponse(outlook_url, status_code=302)
