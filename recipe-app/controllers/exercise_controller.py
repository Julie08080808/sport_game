from typing import Optional, Literal
from uuid import UUID
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from models import exercise_model
from services.exercise_rules import RuleError

router = APIRouter(prefix='/api/exercise', tags=['Exercise Sessions'])
log = logging.getLogger(__name__)


class StartRequest(BaseModel):
    user_id: int = Field(gt=0)
    client_session_id: UUID
    task_progress_id: Optional[int] = Field(default=None, gt=0)
    exercise_id: Optional[int] = Field(default=None, gt=0)
    goal_type: Optional[Literal['count', 'time']] = None
    target_count: Optional[int] = Field(default=None, gt=0)
    target_seconds: Optional[int] = Field(default=None, gt=0)


class SyncRequest(BaseModel):
    user_id: int = Field(gt=0)
    session_id: int = Field(gt=0)
    sync_sequence: int = Field(gt=0)
    cumulative_count: int = Field(ge=0)
    cumulative_seconds: int = Field(ge=0)
    state: Literal['active', 'paused', 'ended', 'interrupted'] = 'active'


def _call(fn, **kwargs):
    try:
        return fn(**kwargs)
    except exercise_model.OpenSessionExists as exc:
        raise HTTPException(409, detail={'code': 'OPEN_SESSION_EXISTS',
                                         'message': str(exc),
                                         'session_id': exc.session_id,
                                         'task_progress_id': exc.task_progress_id}) from exc
    except (RuleError, ValueError) as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    except Exception as exc:
        log.exception('Session request failed')
        raise HTTPException(503, detail='暫時無法保存成果，請保留本機資料並重試') from exc


@router.post('/session/start')
def start(req: StartRequest):
    return _call(exercise_model.start_session, **req.model_dump())


@router.post('/session/sync')
def sync(req: SyncRequest):
    return _call(exercise_model.sync_session, **req.model_dump())


@router.get('/session/open')
def get_open_session(user_id: int):
    return _call(exercise_model.get_open_session, user_id=user_id)


@router.get('/session/{session_id}')
def get_session(session_id: int, user_id: int):
    return _call(exercise_model.get_session, user_id=user_id, session_id=session_id)
