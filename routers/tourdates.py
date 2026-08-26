from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import CurrentUser
import models
from schemas import TourDateCreate, TourDateUpdate, TourDateResponse

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

@router.get("", response_model=list[TourDateResponse])
async def list_my_tour_dates(db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(models.TourDates)
        .where(models.TourDates.user_id == current_user.id)
        .order_by(models.TourDates.date)
    )
    return result.scalars().all()

@router.post("", response_model=TourDateResponse, status_code=status.HTTP_201_CREATED)
async def create_tour_date(tour_date_in: TourDateCreate, db: DbSession, current_user: CurrentUser):
    tour_date = models.TourDates(**tour_date_in.model_dump(), user_id=current_user.id)
    db.add(tour_date)
    await db.commit()
    await db.refresh(tour_date)
    return tour_date

@router.patch("/{tour_date_id}", response_model=TourDateResponse)
async def update_tour_date(tour_date_id: int, tour_date_in: TourDateUpdate, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(models.TourDates).where(models.TourDates.id == tour_date_id))
    tour_date = result.scalars().first()

    if not tour_date:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour date not found")
    if tour_date.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this tour date")

    for field, value in tour_date_in.model_dump(exclude_unset=True).items():
        setattr(tour_date, field, value)

    await db.commit()
    await db.refresh(tour_date)
    return tour_date

@router.delete("/{tour_date_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tour_date(tour_date_id: int, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(models.TourDates).where(models.TourDates.id == tour_date_id))
    tour_date = result.scalars().first()

    if not tour_date:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tour date not found")
    if tour_date.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this tour date")

    await db.delete(tour_date)
    await db.commit()
