from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import CurrentUser, hash_password, verify_password
import models
from schemas import PressAccessCreate, PressAccessUpdate, PressAccessResponse

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

async def list_access(db: DbSession, user_id: int) -> list[models.PressAccess]:
    result = await db.execute(
        select(models.PressAccess).where(models.PressAccess.user_id == user_id).order_by(models.PressAccess.name)
    )
    return list(result.scalars().all())

def _find_match(entries: list[models.PressAccess], password: str) -> models.PressAccess | None:
    # ponytail: linear argon2 scan; fine for a handful of labels per artist
    return next((e for e in entries if verify_password(password, e.password_hash)), None)

async def _assert_password_free(db: DbSession, user_id: int, password: str, exclude_id: int | None = None) -> None:
    # Passwords alone identify a label, so two entries must never share one.
    entries = [e for e in await list_access(db, user_id) if e.id != exclude_id]
    if _find_match(entries, password):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Password already in use")

async def get_entry(access_id: int, db: DbSession, user_id: int) -> models.PressAccess:
    result = await db.execute(
        select(models.PressAccess).where(models.PressAccess.id == access_id, models.PressAccess.user_id == user_id)
    )
    entry = result.scalars().first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Press access not found")
    return entry

async def create_entry(data: PressAccessCreate, db: DbSession, user_id: int) -> models.PressAccess:
    await _assert_password_free(db, user_id, data.password)
    entry = models.PressAccess(user_id=user_id, name=data.name, password_hash=hash_password(data.password))
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry

async def update_entry(access_id: int, data: PressAccessUpdate, db: DbSession, user_id: int) -> models.PressAccess:
    entry = await get_entry(access_id, db, user_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("password"):
        await _assert_password_free(db, user_id, changes["password"], exclude_id=entry.id)
        entry.password_hash = hash_password(changes["password"])
    if changes.get("name") is not None:
        entry.name = changes["name"]
    if changes.get("is_blocked") is not None:
        entry.is_blocked = changes["is_blocked"]
    await db.commit()
    await db.refresh(entry)
    return entry

async def delete_entry(access_id: int, db: DbSession, user_id: int) -> None:
    await db.delete(await get_entry(access_id, db, user_id))
    await db.commit()

@router.get("", response_model=list[PressAccessResponse])
async def list_press_access(db: DbSession, current_user: CurrentUser):
    return await list_access(db, current_user.id)

@router.post("", response_model=PressAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_press_access(data: PressAccessCreate, db: DbSession, current_user: CurrentUser):
    return await create_entry(data, db, current_user.id)

@router.patch("/{access_id}", response_model=PressAccessResponse)
async def update_press_access(access_id: int, data: PressAccessUpdate, db: DbSession, current_user: CurrentUser):
    return await update_entry(access_id, data, db, current_user.id)

@router.delete("/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_press_access(access_id: int, db: DbSession, current_user: CurrentUser):
    await delete_entry(access_id, db, current_user.id)
