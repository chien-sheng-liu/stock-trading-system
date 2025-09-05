from fastapi import APIRouter
from data_fetcher import get_industries

router = APIRouter()

# 固定產業清單（可自行增刪）
INDUSTRIES = [
"食品工業",
  "玻璃陶瓷",
  "塑膠工業",
  "化學工業",
  "綠能環保",
  "數位雲端",
  "其他業",
  "油電燃氣業",
  "電子零組件業",
  "運動休閒",
  "電腦及週邊設備業",
  "居家生活",
  "橡膠工業",
  "電子通路業",
  "電機機械",
  "鋼鐵工業",
  "電器電纜",
  "建材營造業",
  "貿易百貨業",
  "金融保險業",
  "通信網路業",
  "航運業",
  "半導體業",
  "水泥工業",
  "汽車工業",
  "造紙工業",
  "生技醫療業",
  "紡織纖維",
  "其他電子業",
  "觀光餐旅",
  "資訊服務業",
  "光電業"
]

@router.get("/industries")
def list_industries():
    return {"industries": get_industries()}
