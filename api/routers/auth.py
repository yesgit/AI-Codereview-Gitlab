"""
认证相关 API
"""
import os
import hmac
import hashlib
import base64
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel

router = APIRouter()

# 从环境变量中读取用户名和密码
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {
    DASHBOARD_USER: DASHBOARD_PASSWORD
}

# 用于生成和验证token的密钥
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "fac8cf149bdd616c07c1a675c4571ccacc40d7f7fe16914cfe0f9f9d966bb773")

# Token 过期时间（30天）
TOKEN_EXPIRE_DAYS = 30


class LoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    expires_at: str


class UserResponse(BaseModel):
    username: str


def generate_token(username: str) -> tuple[str, datetime]:
    """生成包含时间戳的认证token"""
    timestamp = str(int(time.time()))
    message = f"{username}:{timestamp}"

    # 使用HMAC-SHA256生成签名
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()

    # 将消息和签名编码为base64
    token = base64.b64encode(f"{message}:{base64.b64encode(signature).decode()}".encode()).decode()
    
    # 计算过期时间
    expires_at = datetime.now() + timedelta(days=TOKEN_EXPIRE_DAYS)
    
    return token, expires_at


def verify_token(token: str) -> Optional[str]:
    """验证token的有效性并提取用户名"""
    try:
        # 解码token
        decoded = base64.b64decode(token.encode()).decode()
        message, signature = decoded.rsplit(":", 1)
        username, timestamp = message.split(":", 1)

        # 验证签名
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()

        actual_signature = base64.b64decode(signature)

        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        # 检查token是否过期
        if int(time.time()) - int(timestamp) > TOKEN_EXPIRE_DAYS * 24 * 60 * 60:
            return None

        return username
    except:
        return None


async def get_current_user(authorization: str = Header(None)) -> str:
    """获取当前用户（依赖注入）"""
    # 从 Authorization 头中提取 token
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证格式",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:]  # 移除 "Bearer " 前缀
    username = verify_token(token)
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return username


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录"""
    if request.username not in USER_CREDENTIALS or USER_CREDENTIALS[request.username] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    token, expires_at = generate_token(request.username)
    
    return TokenResponse(
        access_token=token,
        username=request.username,
        expires_at=expires_at.isoformat()
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(username=current_user)
