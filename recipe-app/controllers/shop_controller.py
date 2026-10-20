"""
商店控制器 (Controller)
處理商品清單、購買、玩家庫存的 HTTP 請求。

API 設計:
    GET  /api/shop/items              取得上架商品清單
    POST /api/shop/purchase           購買商品(扣 user_stats.money,寫入 user_items)
    GET  /api/shop/inventory/{user_id} 取得玩家庫存
"""
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel, Field
from models import shop_model
from services.exercise_rules import RuleError
router = APIRouter(prefix='/api/shop', tags=['Shop'])


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (RuleError, ValueError) as e:
        raise HTTPException(409, detail=str(e)) from e
    except Exception as e:
        logging.getLogger(__name__).exception('Shop operation failed')
        raise HTTPException(503, detail='暫時無法處理，請使用相同請求 ID 重試') from e


@router.get('/items')
def items(): return dict(success=True, items=_call(shop_model.fetch_shop_items))


@router.get('/inventory/{user_id}')
def inventory(user_id: int): return dict(
    success=True, items=_call(shop_model.fetch_user_inventory, user_id))


@router.post('/purchase')
def purchase(user_id: int = Form(...), item_id: int = Form(...), quantity: int = Form(1), request_id: UUID = Form(...)):
    return _call(shop_model.purchase_item, user_id, item_id, quantity, request_id)


class BonusRequest(BaseModel):
    user_id: int = Field(gt=0)
    task_progress_id: int = Field(gt=0)
    bind_request_id: UUID


@router.post('/bonus/bind')
def bind(req: BonusRequest): return _call(
    shop_model.bind_bonus, **req.model_dump())
