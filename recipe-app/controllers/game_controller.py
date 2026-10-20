from uuid import UUID
import logging
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel, Field
from models import game_model
from services.exercise_rules import RuleError
router = APIRouter(prefix='/api/game', tags=['Game Mechanics'])
log = logging.getLogger(__name__)


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (RuleError, ValueError) as e:
        raise HTTPException(409, detail=str(e)) from e
    except Exception as e:
        log.exception('Game request failed')
        raise HTTPException(503, detail='暫時無法處理，請使用相同請求 ID 重試') from e


class ExpUpdateReq(BaseModel):
    user_id: int
    building_type: int
    base_exp: int


@router.post('/complete_task')
def complete_task(req: ExpUpdateReq):
    raise HTTPException(410, detail='請使用 Session 同步')


@router.post('/sync_exp')
def sync_exp(user_id: int = Form(...), building_type: int = Form(...), exp_amount: int = Form(...)):
    raise HTTPException(410, detail='請使用 Session 同步')


@router.get('/scenes/{user_id}')
def get_scenes(user_id: int):
    return dict(success=True, scenes=_call(game_model.get_all_scene_status, user_id))


class UpgradeRequest(BaseModel):
    user_id: int = Field(gt=0)
    scene_id: int = Field(gt=0)
    target_level: int = Field(ge=2)
    request_id: UUID


@router.post('/scene/upgrade')
def upgrade(req: UpgradeRequest):
    return _call(game_model.purchase_scene_level, **req.model_dump())


@router.post('/scene/display_level')
def display(user_id: int = Form(...), scene_id: int = Form(...), display_level: int = Form(...)):
    return _call(game_model.set_scene_display_level, user_id, scene_id, display_level)


@router.get('/scene/{scene_id}/appearances')
def appearances(scene_id: int, user_id: int):
    return dict(success=True, appearances=_call(game_model.get_appearances, user_id, scene_id))


class AppearanceRequest(BaseModel):
    user_id: int = Field(gt=0)
    scene_id: int = Field(gt=0)
    appearance_stage_id: int = Field(gt=0)


@router.post('/scene/appearance')
def appearance(req: AppearanceRequest):
    return _call(game_model.select_appearance, **req.model_dump())
