from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.schemas.auth import AuthRequest, AuthResponse, User
from src.api.services.auth_service import authenticate, get_user_from_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> User:
    if not credentials:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authentication required.")
    return User(**get_user_from_token(credentials.credentials))


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(request: AuthRequest):
    return authenticate(request.email, request.password, create=True)


@router.post("/login", response_model=AuthResponse)
def login(request: AuthRequest):
    return authenticate(request.email, request.password)