from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .adapters.memory_uow import InMemoryUnitOfWork
from .config import Settings
from .dependencies.settings import get_settings
from .dependencies.uow import get_uow
from .errors import Problem, problem
from .interfaces.errors import ConflictError, NotFoundError, ValidationError
from .logging_config import configure_logging
from .routers import listings, matches,  seekers, swipes, auth, users


class HealthResponse(BaseModel):
    status: str
    app_name: str


class SeedCounts(BaseModel):
    seekers: int
    hosts: int
    listings: int
    swipes: int
    matches: int


configure_logging()

app = FastAPI(title="Sublease Matcher API")
settings_instance = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_instance.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(seekers.router)
app.include_router(seekers.profiles_router)
app.include_router(listings.router)
app.include_router(listings.public_router)
app.include_router(swipes.router)
app.include_router(swipes.public_router)
app.include_router(matches.router)
app.include_router(auth.router)
app.include_router(users.router)


@app.get("/", response_model=HealthResponse, tags=["root"])
def root(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name)


@app.get("/healthz", response_model=HealthResponse, tags=["health"])
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name)


@app.get("/_debug/seed_counts", response_model=SeedCounts, tags=["debug"])
def seed_counts(uow: InMemoryUnitOfWork = Depends(get_uow)) -> SeedCounts:
    return SeedCounts(
        seekers=len(uow.seekers._data),
        hosts=len(uow.hosts._data),
        listings=len(uow.listings._data),
        swipes=len(uow.swipes._data),
        matches=len(uow.matches._data),
    )


def _problem_response(pb: Problem) -> JSONResponse:
    return JSONResponse(
        status_code=pb.status,
        content=pb.model_dump(),
        media_type="application/problem+json",
    )


@app.exception_handler(NotFoundError)
async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
    pb = problem(status=404, title="Not Found", detail=str(exc) or None)
    return _problem_response(pb)


@app.exception_handler(ValidationError)
async def handle_validation(_: Request, exc: ValidationError) -> JSONResponse:
    pb = problem(status=422, title="Validation Error", detail=str(exc) or None)
    return _problem_response(pb)


@app.exception_handler(ConflictError)
async def handle_conflict(_: Request, exc: ConflictError) -> JSONResponse:
    pb = problem(status=409, title="Conflict", detail=str(exc) or None)
    return _problem_response(pb)


@app.exception_handler(RequestValidationError)
async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    pb = problem(status=422, title="Request Validation Error", detail=str(exc))
    return _problem_response(pb)
