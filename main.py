from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS許可（外部アクセス用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/context")
async def receive_context(request: Request):
    body = await request.json()
    print("✅ 受け取ったリクエスト:", body)

    return {
        "candidates": [
            "2024-05-15T15:00:00",
            "2024-05-17T15:00:00"
        ],
        "ui_url": "https://example.com/choose"
    }
from fastapi import Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import urllib.parse

templates = Jinja2Templates(directory="templates")

@app.get("/choose", response_class=HTMLResponse)
async def choose_get(request: Request, candidates: List[str] = [], body: str = ""):
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
