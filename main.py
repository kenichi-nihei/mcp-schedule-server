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
