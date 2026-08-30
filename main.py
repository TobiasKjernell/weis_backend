from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from database import engine
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import users, youtube, tourdates, artists, images
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(title="Moroii", lifespan=lifespan)

allowed_origins = ["http://localhost:5173"]
if settings.frontend_url:
    allowed_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(youtube.router, prefix="/api/youtube", tags=["Youtube"])
app.include_router(tourdates.router, prefix="/api/tour-dates", tags=["Tour Dates"])
app.include_router(artists.router, prefix="/api/artists", tags=["Artists"])
app.include_router(images.router, prefix="/api/images", tags=["Images"])

@app.get("/")
async def ping():
    return {"message": "Moroii backend"}

@app.exception_handler(StarletteHTTPException)
async def http_exception_override(request: Request, exception: StarletteHTTPException):
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

@app.exception_handler(RequestValidationError)
async def validation_exception_override(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
