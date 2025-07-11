from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from models.database import get_db
from models.models import User
from utils.auth import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    get_current_user
)

router = APIRouter()

# Pydantic 모델
class UserCreate(BaseModel):
    email: str
    name: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    user_name: str
    user_email: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str

@router.post("/users/signup", 
    response_model=UserResponse,
    summary="회원가입",
    description="새로운 사용자 계정을 생성합니다. 이메일 중복 확인 후 비밀번호를 해싱하여 데이터베이스에 저장합니다.",
    response_description="생성된 사용자 정보")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    사용자 회원가입
    """
    try:
        # 이메일 중복 확인
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 이메일입니다"
            )
        
        # 비밀번호 해싱
        hashed_password = get_password_hash(user_data.password)
        
        # 사용자 생성
        user = User(
            email=user_data.email,
            name=user_data.name,
            password=hashed_password
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"회원가입 실패: {str(e)}"
        )

@router.post("/users/login", 
    response_model=Token,
    summary="로그인",
    description="사용자 이메일과 비밀번호로 로그인합니다. 인증 성공 시 JWT 토큰을 발급합니다.",
    response_description="로그인 성공 시 토큰 정보")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    사용자 로그인
    """
    try:
        # 사용자 조회
        user = db.query(User).filter(
            User.email == user_data.email,
            User.is_deleted == False
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 잘못되었습니다"
            )
        
        # 비밀번호 검증
        if not verify_password(user_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 잘못되었습니다"
            )
        
        # JWT 토큰 생성
        access_token = create_access_token(
            data={"user_id": user.id, "email": user.email}
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            user_name=user.name,
            user_email=user.email
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"로그인 실패: {str(e)}"
        )

@router.get("/users", 
    response_model=UserResponse,
    summary="내 정보 조회",
    description="현재 로그인한 사용자의 정보를 조회합니다.",
    response_description="현재 사용자 정보")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    현재 로그인한 사용자 정보 조회
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name
    )

@router.delete("/users",
    summary="내 계정 삭제",
    description="현재 로그인한 사용자의 계정을 삭제합니다. 소프트 삭제 방식으로 실제 데이터는 보존됩니다.",
    response_description="계정 삭제 완료 메시지")
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    현재 사용자 계정 삭제 (소프트 삭제)
    """
    try:
        # 소프트 삭제 (실제 삭제하지 않고 플래그만 변경)
        current_user.is_deleted = True
        db.commit()
        
        return {"message": f"사용자 {current_user.name}의 계정이 삭제되었습니다"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 삭제 실패: {str(e)}"
        )

@router.post("/auth/logout",
    summary="로그아웃",
    description="사용자를 로그아웃합니다. 클라이언트에서 토큰을 삭제하도록 안내합니다.",
    response_description="로그아웃 완료 메시지")
async def logout():
    """
    로그아웃 (클라이언트에서 토큰 삭제)
    """
    return {"message": "로그아웃되었습니다"}



@router.put("/users/{user_id}",
    summary="사용자 정보 수정",
    description="사용자 정보를 수정합니다. 본인 또는 관리자만 수정 가능합니다.",
    response_description="수정된 사용자 정보")
async def update_user(
    user_id: int,
    user_update: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    사용자 정보 수정
    - 본인만 수정 가능
    - 관리자는 다른 사용자 수정 가능
    """
    try:
        # 수정할 사용자 조회
        user_to_update = db.query(User).filter(
            User.id == user_id,
            User.is_deleted == False
        ).first()
        
        if not user_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 권한 확인: 본인 또는 관리자만 수정 가능
        if current_user.id != user_id and current_user.email != "admin@samsung.com":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="수정 권한이 없습니다"
            )
        
        # 이메일 중복 확인 (본인 제외)
        if user_update.email != user_to_update.email:
            existing_user = db.query(User).filter(
                User.email == user_update.email,
                User.is_deleted == False
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 사용 중인 이메일입니다"
                )
        
        # 비밀번호 해싱
        hashed_password = get_password_hash(user_update.password)
        
        # 사용자 정보 업데이트
        user_to_update.email = user_update.email
        user_to_update.name = user_update.name
        user_to_update.password = hashed_password
        
        db.commit()
        
        return UserResponse(
            id=user_to_update.id,
            email=user_to_update.email,
            name=user_to_update.name
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 수정 실패: {str(e)}"
        ) 