"""
檔案上傳控制器 (Controller)
依架構圖規範:使用 FastAPI 的 UploadFile 處理圖片上傳。
"""
import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter(prefix="/api/upload", tags=["Upload"])

# 上傳儲存資料夾
UPLOAD_DIR = "image"
# 允許的副檔名
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    """
    接收前端傳來的圖片檔,儲存到 image/ 資料夾。
    回傳檔名,前端可用 /image/{filename} 取得圖片。
    """
    # 1. 檢查 MIME type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只允許上傳圖片檔案")

    # 2. 檢查副檔名
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支援的圖片格式: {ext}")

    # 3. 確認資料夾存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 4. 用 UUID 產生唯一檔名,避免覆蓋
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, safe_filename)

    # 5. 寫入檔案
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    return {
        "success": True,
        "filename": safe_filename,
        "url": f"/image/{safe_filename}",
    }
