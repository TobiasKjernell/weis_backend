import enum
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, Enum as SqlEnum
from datetime import datetime, UTC
from sqlalchemy.orm  import Mapped, mapped_column, relationship
from database import Base

class MerchType(str, enum.Enum):
    clothing = "clothing"
    misc = "misc"

class MerchSize(str, enum.Enum):
    xs = "XS"
    s = "S"
    m = "M"
    l = "L"
    xl = "XL"
    xxl = "XXL"

class ReservationStatus(str, enum.Enum):
    pending = "pending"
    contacted = "contacted"
    fulfilled = "fulfilled"
    cancelled = "cancelled"

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
    gallery_images: Mapped[list["GalleryImage"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    merch_items: Mapped[list["MerchItem"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class YoutubeVideo(Base):
    __tablename__= "youtube"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    video: Mapped[str] = mapped_column(String(200), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=True)    
    position: Mapped[int] = mapped_column(Integer)
    owner: Mapped["User"] = relationship(back_populates="youtube_videos")

class GalleryImage(Base):
    __tablename__= "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    key: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    owner: Mapped["User"] = relationship(back_populates="gallery_images")

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

class MerchItem(Base):
    __tablename__ = "merch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[MerchType] = mapped_column(SqlEnum(MerchType, name="merch_type"), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="merch_items")
    variants: Mapped[list["MerchVariant"]] = relationship(back_populates="item", cascade="all, delete-orphan")

class MerchVariant(Base):
    __tablename__ = "merch_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    merch_item_id: Mapped[int] = mapped_column(ForeignKey("merch_items.id"), nullable=False, index=True)
    size: Mapped[MerchSize | None] = mapped_column(SqlEnum(MerchSize, name="merch_size"), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    item: Mapped["MerchItem"] = relationship(back_populates="variants")
    reservations: Mapped[list["MerchReservation"]] = relationship(back_populates="variant", cascade="all, delete-orphan")

class MerchReservation(Base):
    __tablename__ = "merch_reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    merch_variant_id: Mapped[int] = mapped_column(ForeignKey("merch_variants.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_instagram: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ReservationStatus] = mapped_column(
        SqlEnum(ReservationStatus, name="reservation_status"), nullable=False, default=ReservationStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    variant: Mapped["MerchVariant"] = relationship(back_populates="reservations")
