from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List
import urllib.parse

app = FastAPI()

# CORS許可（外部アクセス用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

@app.post("/context")
async def receive_context(request: Request):
    body = await request.json()

    # 👇 context.email.subject に変更
    subject = body["context"]["email"]["subject"]

    candidates = ["2024-05-15T15:00:00", "2024-05-17T15:00:00"]
    encoded_candidates = urllib.parse.urlencode([
        ("candidates", dt) for dt in candidates
    ])
    encoded_body = urllib.parse.quote(subject)

    return {
        "candidates": candidates,
        "ui_url": f"https://mcp-schedule-server.onrender.com/choose?{encoded_candidates}&body={encoded_body}"
    }

from fastapi import Query

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


@app.post("/choose", response_class=RedirectResponse)
async def choose_post(selected: str = Form(...)):
    subject = "打ち合わせ予定"
    body = f"以下日時で打ち合わせをお願いします。\n{selected}"
    outlook_url = f"https://outlook.office.com/calendar/0/deeplink/compose?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
    return RedirectResponse(url=outlook_url, status_code=303)
