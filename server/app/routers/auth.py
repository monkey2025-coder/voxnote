from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=TokenResponse, summary="注册")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == req.username).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    user = User(username=req.username, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse, summary="登录")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse, summary="当前用户信息")
def me(current_user: User = Depends(get_current_user)):
    return current_user
