import re
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)

class UserPublic(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class Token(BaseModel):
    access_token: str
    token_type: str

class ArtistCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=200)
    slug: str = Field(min_length=3, max_length=50)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.lower()

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        value = value.lower()
        if not SLUG_PATTERN.match(value):
            raise ValueError("slug must be lowercase letters, numbers, and hyphens only")
        return value

class ArtistAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    slug: str
    display_name: str
    is_admin: bool

class ArtistPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    display_name: str

class YoutubeVideoBase(BaseModel):
    video: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    position: int

class YoutubeVideoCreate(YoutubeVideoBase):
    pass

class YoutubeVideoUpdate(BaseModel):
    video: str | None = Field(default=None, min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    position: int | None = None

class YoutubeVideoResponse(YoutubeVideoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int

class TourDateBase(BaseModel):
    date: datetime
    location: str = Field(min_length=1, max_length=200)
    venue: str = Field(min_length=1, max_length=200)
    tickets_state: bool = True
    tickets_url: str = Field(min_length=1, max_length=500)

class TourDateCreate(TourDateBase):
    pass

class TourDateUpdate(BaseModel):
    date: datetime | None = None
    location: str | None = Field(default=None, min_length=1, max_length=200)
    venue: str | None = Field(default=None, min_length=1, max_length=200)
    tickets_state: bool | None = None
    tickets_url: str | None = Field(default=None, min_length=1, max_length=500)

class TourDateResponse(TourDateBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
