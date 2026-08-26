from fastapi import APIRouter, Depends, status, HTTPException
from schemas import Token, ArtistCreate, ArtistAdminResponse
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from database import get_db
from auth import create_access_token, verify_password, hash_password, CurrentAdmin
from sqlalchemy import select
import models

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    result = await db.execute(select(models.User).where(models.User.username == form_data.username.lower()))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})

    token = create_access_token(data={"sub": str(user.username)})

    return Token(access_token=token, token_type="bearer")

@router.post("", response_model=ArtistAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_artist(artist_in: ArtistCreate, db: DbSession, _admin: CurrentAdmin):
    new_artist = models.User(
        username=artist_in.username,
        password_hash=hash_password(artist_in.password),
        slug=artist_in.slug,
        display_name=artist_in.display_name,
        is_admin=False,
    )
    db.add(new_artist)
    try:
        await db.commit()
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or slug already taken") from err

    await db.refresh(new_artist)
    return new_artist

@router.get("", response_model=list[ArtistAdminResponse])
async def list_artists_admin(db: DbSession, _admin: CurrentAdmin):
    result = await db.execute(select(models.User).order_by(models.User.display_name))
    return result.scalars().all()

@router.get("/{slug}", response_model=ArtistAdminResponse)
async def get_artist_admin(slug: str, db: DbSession, _admin: CurrentAdmin):
    result = await db.execute(select(models.User).where(models.User.slug == slug))
    artist = result.scalars().first()
    if not artist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artist not found")
    return artist
