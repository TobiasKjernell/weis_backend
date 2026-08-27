from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean
from datetime import datetime, UTC
from sqlalchemy.orm  import Mapped, mapped_column, relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer,primary_key=True, index=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    youtube_videos: Mapped[list["YoutubeVideo"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    tour_dates: Mapped[list["TourDates"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class YoutubeVideo(Base):
    __tablename__= "youtube"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    video: Mapped[str] = mapped_column(String(200), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=True)    
    position: Mapped[int] = mapped_column(Integer)
    owner: Mapped["User"] = relationship(back_populates="youtube_videos")

class Images(Base):
    __tablename__= "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  

class TourDates(Base):
    __tablename__ = "tourdates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    venue: Mapped[str] = mapped_column(String(200), nullable=False)
    tickets_state: Mapped[bool] = mapped_column(Boolean, default=True)
    tickets_url: Mapped[str] = mapped_column(String(500), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    owner: Mapped["User"] = relationship(back_populates="tour_dates")
