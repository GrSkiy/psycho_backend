from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.db.schemas.diary import DiaryEntry
from app.core.service_hub import get_service_hub, ServiceHub

router = APIRouter()

@router.get("/{user_id}/entries", response_model=List[DiaryEntry])
async def get_user_diary_entries(
    user_id: int, 
    skip: int = 0, 
    limit: int = 50,
    service_hub: ServiceHub = Depends(get_service_hub)
):
    """Get diary entries for a user."""
    # TODO: Добавить проверку авторизации
    entries = await service_hub.diary_service.get_user_entries(
        user_id=user_id, skip=skip, limit=limit
    )
    return entries

@router.post("/{user_id}/entries", response_model=DiaryEntry)
async def create_diary_entry(
    user_id: int,
    title: str,
    content: str,
    event_type: str = None,
    service_hub: ServiceHub = Depends(get_service_hub)
):
    """Create a new diary entry."""
    # TODO: Добавить проверку авторизации
    entry = await service_hub.diary_service.create_entry(
        user_id=user_id,
        title=title,
        content=content,
        event_type=event_type
    )
    return entry
