"""
商店控制器 (Controller)
處理商品清單、購買、玩家庫存的 HTTP 請求。

API 設計:
    GET  /api/shop/items              取得上架商品清單
    POST /api/shop/purchase           購買商品(扣 user_stats.money,寫入 user_items)
    GET  /api/shop/inventory/{user_id} 取得玩家庫存
"""
from fastapi import APIRouter, HTTPException, Form
from models import shop_model

router = APIRouter(prefix="/api/shop", tags=["Shop"])


@router.get("/items")
def get_items():
    return {"success": True, "items": shop_model.fetch_shop_items()}


@router.post("/purchase")
def purchase(user_id: int = Form(...), item_id: int = Form(...), quantity: int = Form(1)):
    if quantity < 1:
        raise HTTPException(status_code=400, detail="quantity 必須大於 0")

    result = shop_model.purchase_item(user_id, item_id, quantity)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/inventory/{user_id}")
def get_inventory(user_id: int):
    return {"success": True, "items": shop_model.fetch_user_inventory(user_id)}
