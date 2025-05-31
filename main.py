from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
from openai import OpenAI
import urllib.parse
import os
import re
from datetime import datetime, timedelta

app = FastAPI()
templates = Jinja2Templates(directory="templates")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def strip_html_tags(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)  # HTMLタグ除去
    text = text.replace('\uFEFF', '')    # BOM除去（&#65279;）
    return text.strip()

def generate_subject_suggestion(current_subject: str, email_body: str) -> str:
    prompt = f"""
以下は受信したメールの件名と本文です。
この内容から、会議予定のタイトルとして自然で要点が伝わるような件名を1文で生成してください。

件名:
{current_subject}

本文:
{email_body}

# 出力形式：件名のみ（例：「○○に関する初回打ち合わせ」）
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ 件名生成エラー:", e)
        return "打ち合わせ"

def extract_datetime_candidates(email_body: str) -> List[str]:
    prompt = f"""
以下のメール本文から、打ち合わせ候補日時を ISO8601形式（例: 2024-05-15T15:00:00）で最大3件抽出してください。
本文:
{email_body}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        lines = content.splitlines()
        return [line.strip() for line in lines if line.strip()]
    except Exception as e:
        print("❌ GPT呼び出しエラー:", e)
        return []

@app.post("/context")
async def receive_context(request: Request):
    body = await request.json()
    email = body["context"]["email"]
    subject = email["subject"]
    email_body_raw = email["body"].replace('\uFEFF', '')
    email_body = strip_html_tags(email_body_raw)

    if not subject or subject.strip() in ["", "打ち合わせ", "ご連絡", "相談", "確認"]:
        subject = generate_subject_suggestion(subject, email_body)

    from_ = email["from"]
    cc = email.get("cc", "").replace('\uFEFF', '').strip()
    candidates = body["context"].get("candidates", [])
    conflicts = body["context"].get("conflicts", [])
    encoded_candidates = urllib.parse.urlencode([("candidates", dt) for dt in candidates])
    encoded_conflicts = urllib.parse.urlencode([("conflicts", c) for c in conflicts])
    encoded_subject = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(email_body)
    encoded_from = urllib.parse.quote(from_)
    encoded_cc = urllib.parse.quote(cc)

    return {
        "candidates": candidates,
        "ui_url": (
            f"https://mcp-schedule-server.onrender.com/choose?"
            f"{encoded_candidates}&{encoded_conflicts}"
            f"&subject={encoded_subject}"
            f"&from={encoded_from}"
            f"&cc={encoded_cc}"
            f"&body={encoded_body}"
        )
    }

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
    cc_display = ", ".join(cc.split(",")) if cc else ""
    return templates.TemplateResponse("choose.html", {
        "request": request,
        "candidates": candidates,
        "conflicts": conflicts,
        "subject": subject,
        "from_": from_,
        "body": body,
        "cc": cc_display,
    })

@app.post("/choose")
async def choose_post(request: Request):
    form = await request.form()
    selected = form.get("selected", "")
    body = form.get("body", "")
    subject = form.get("subject", "打ち合わせ")
    from_ = form.get("from", "")
    cc = form.get("cc", "")

    start_dt = datetime.fromisoformat(selected)
    end_dt = start_dt + timedelta(minutes=30)

    # ✅ 出席者の組み立て（from_ + cc）
    attendees = []
    if from_:
        attendees.append(from_)
    if cc:
        attendees += [addr.strip() for addr in cc.split(",") if addr.strip()]
    to_param = ",".join(attendees)

    outlook_url = (
        f"https://outlook.office.com/calendar/0/deeplink/compose?"
        f"subject={urllib.parse.quote(subject)}"
        f"&body={urllib.parse.quote(body)}"
        f"&startdt={start_dt.isoformat()}"
        f"&enddt={end_dt.isoformat()}"
        f"&to={urllib.parse.quote(to_param)}"
        f"&cc={urllib.parse.quote(cc)}"    
    )

    return RedirectResponse(outlook_url, status_code=302)
