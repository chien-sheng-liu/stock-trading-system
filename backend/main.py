from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import auto_recommend, manual_recommend, backtest, industries, insights

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

app.include_router(auto_recommend.router, prefix="/api", tags=["recommendation"])
app.include_router(manual_recommend.router, prefix="/api", tags=["recommendation"])
app.include_router(industries.router, prefix="/api", tags=["data"])
app.include_router(backtest.router, prefix="/api", tags=["backtest"])
app.include_router(insights.router, prefix="/api", tags=["insights"])


@app.get("/")
def read_root():
    return {"message": "AI Trading Pro API is running!"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is working correctly"}