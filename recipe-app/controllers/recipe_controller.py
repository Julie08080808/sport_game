"""
食譜控制器 (Controller)
處理食譜相關的 HTTP 請求,並呼叫 Model 取資料。
"""
from fastapi import APIRouter, HTTPException
from models import recipe_model

router = APIRouter(prefix="/api", tags=["Recipes"])


@router.get("/recipes")
def get_all_recipes():
    """取得所有食譜清單(含食材)。"""
    return recipe_model.fetch_all_recipes()


@router.get("/recipes/{recipe_id}/steps")
def get_recipe_steps(recipe_id: int):
    """取得指定食譜的步驟說明。"""
    steps = recipe_model.fetch_recipe_steps(recipe_id)
    if not steps:
        raise HTTPException(status_code=404, detail="找不到步驟")
    return steps
