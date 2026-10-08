"""受保护的文件下载:/files 不再公开挂载,必须带 token 且只能访问自己的文件。

浏览器 <audio>/<img> 标签无法携带 Authorization 头,因此支持 ?token= 查询参数。
文件路径格式: audio/<user_id>/<uuid>.m4a 或 images/<user_id>/<uuid>.jpg
第一段即属主用户 id,用于归属校验。
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import decode_access_token
from app.core.config import UPLOAD_DIR
from app.dependencies.auth import bearer_scheme

router = APIRouter(tags=["文件"])

ALLOWED_KINDS = {"audio", "images"}


def resolve_user_id(credentials: HTTPAuthorizationCredentials | None, token: str | None) -> int:
    raw = credentials.credentials if credentials else token
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 token")
    user_id = decode_access_token(raw)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或已过期的 token")
    return user_id


@router.get("/files/{kind}/{owner_id}/{filename}", summary="下载音频/批注图片(需认证,只能访问自己的文件)")
def get_file(
    kind: str,
    owner_id: str,
    filename: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token: str | None = Query(default=None),
):
    user_id = resolve_user_id(credentials, token)

    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    # 归属校验:路径第一段必须是当前用户 id
    if not owner_id.isdigit() or int(owner_id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该文件")
    # 防路径穿越
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法文件名")

    path = UPLOAD_DIR / kind / owner_id / filename
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return FileResponse(path)
