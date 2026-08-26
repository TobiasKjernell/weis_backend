from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import CurrentUser
import models
from schemas import YoutubeVideoCreate, YoutubeVideoUpdate, YoutubeVideoResponse

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

@router.get("", response_model=list[YoutubeVideoResponse])
async def list_my_youtube_videos(db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(models.YoutubeVideo)
        .where(models.YoutubeVideo.user_id == current_user.id)
        .order_by(models.YoutubeVideo.position)
    )
    return result.scalars().all()

@router.post("", response_model=YoutubeVideoResponse, status_code=status.HTTP_201_CREATED)
async def create_youtube_video(video_in: YoutubeVideoCreate, db: DbSession, current_user: CurrentUser):
    video = models.YoutubeVideo(**video_in.model_dump(), user_id=current_user.id)
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video

@router.patch("/{video_id}", response_model=YoutubeVideoResponse)
async def update_youtube_video(video_id: int, video_in: YoutubeVideoUpdate, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(models.YoutubeVideo).where(models.YoutubeVideo.id == video_id))
    video = result.scalars().first()

    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if video.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this video")

    for field, value in video_in.model_dump(exclude_unset=True).items():
        setattr(video, field, value)

    await db.commit()
    await db.refresh(video)
    return video

@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_youtube_video(video_id: int, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(models.YoutubeVideo).where(models.YoutubeVideo.id == video_id))
    video = result.scalars().first()

    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if video.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this video")

    await db.delete(video)
    await db.commit()
