from fastapi import FastAPI
import os
import importlib
from fastapi.middleware.cors import CORSMiddleware

from api import auto_recommend, backtest, industries, insights, ai_recommend, config

app = FastAPI(title="AI Trading Pro API", version="1.0.0")

# CORS middleware - 允許前端連接
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auto_recommend.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(industries.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(ai_recommend.router, prefix="/api")
app.include_router(config.router, prefix="/api")


def _detect_openai_sdk():
    info = {"installed": False, "sdk": "none", "version": "unknown"}
    try:
        openai = importlib.import_module("openai")
        info["installed"] = True
        info["version"] = getattr(openai, "__version__", "unknown")
        try:
            from openai import OpenAI  # type: ignore
            info["sdk"] = "new"
        except Exception:
            info["sdk"] = "legacy" if hasattr(openai, "ChatCompletion") else "unknown"
    except ImportError:
        pass
    return info


@app.on_event("startup")
async def startup_check():
    key = os.getenv("OPENAI_API_KEY")
    # Default to an instruct-capable model for the Completions API
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-instruct")
    sdk = _detect_openai_sdk()

    print("--- OpenAI Integration Check ---")
    if not key:
        print("[WARN] OPENAI_API_KEY is not set. AI summaries are disabled. ")
    else:
        print("[OK] OPENAI_API_KEY is set.")
    print(f"[INFO] OPENAI_MODEL: {model}")
    # Heuristic: completions API requires an instruct-capable model
    instruct_like = any(x in model.lower() for x in ["instruct", "text-davinci", "babbage-002", "davinci-002"])
    chat_like = any(x in model.lower() for x in ["gpt-4o", "gpt-4", "gpt-3.5-turbo"]) and not instruct_like
    if not sdk["installed"]:
        print("[WARN] openai package not installed. Install requirements to enable AI.")
    else:
        print(f"[INFO] openai SDK detected: {sdk['sdk']} (version {sdk['version']})")
        if sdk["sdk"] == "legacy":
            print("[INFO] Using legacy ChatCompletion path. Consider upgrading to 1.x.")
    if chat_like:
        print("[WARN] OPENAI_MODEL appears to be a chat model. The backend currently uses the Completions API; set OPENAI_MODEL to an instruct-capable model such as 'gpt-3.5-turbo-instruct'.")
    print("--------------------------------")


@app.get("/")
def read_root():
    return {"message": "AI Trading Pro API is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is working correctly"}
