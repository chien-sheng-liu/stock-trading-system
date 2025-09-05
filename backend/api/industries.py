from fastapi import APIRouter

router = APIRouter()

# 固定產業清單（可自行增刪）
INDUSTRIES = [
    "半導體業",
    "電腦及週邊設備業",
    "金融業",
    "通信網路業",
    "生技醫療業",
    "汽車業",
    "塑膠工業",
    "水泥工業"
]

@router.get("/industries")
def list_industries():
    """回傳固定的產業分類"""
    return {"industries": INDUSTRIES}
