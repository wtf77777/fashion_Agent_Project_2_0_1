"""
FastAPI 後端 - 取代 Streamlit
部署到 Render 的主程式
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pathlib import Path
import sys
import os

# 添加 backend 到路徑
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from config import AppConfig
from database.supabase_client import SupabaseClient
from api.ai_service import AIService
from api.weather_service import WeatherService
from api.wardrobe_service import WardrobeService
from database.models import ClothingItem

# ========== 初始化 FastAPI ==========
app = FastAPI(
    title="AI Fashion Assistant API",
    description="AI 智慧衣櫥管理系統",
    version="2.0.0"
)

# ========== CORS 設定 ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 載入配置 ==========
config = AppConfig.from_env()
# ========== 初始化服務 ==========
supabase_client = SupabaseClient(config.supabase_url, config.supabase_key)
ai_service = AIService(config.gemini_api_key)
weather_service = WeatherService(config.weather_api_key)
wardrobe_service = WardrobeService(supabase_client)

# ========== 掛載靜態文件 ==========
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ========== 根路由 ==========
@app.get("/")
async def read_root():
    """返回前端 HTML 頁面"""
    return FileResponse("frontend/index.html")

# ========== 健康檢查 ==========
@app.get("/health")
async def health_check():
    """Render 健康檢查"""
    db_ok = supabase_client.test_connection()
    return {
        "status": "healthy",
        "database": "connected" if db_ok else "disconnected"
    }

# ========== 認證 API ==========
@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """使用者登入"""
    try:
        result = supabase_client.client.table("users")\
            .select("*")\
            .eq("username", username)\
            .eq("password", password)\
            .execute()
        
        if result.data:
            return {
                "success": True,
                "user_id": result.data[0]['id'],
                "username": username
            }
        else:
            return {"success": False, "message": "帳號或密碼錯誤"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/register")
async def register(username: str = Form(...), password: str = Form(...)):
    """使用者註冊"""
    try:
        existing = supabase_client.client.table("users")\
            .select("id")\
            .eq("username", username)\
            .execute()
        
        if existing.data:
            return {"success": False, "message": "使用者名稱已存在"}
        
        result = supabase_client.client.table("users")\
            .insert({"username": username, "password": password})\
            .execute()
        
        return {"success": True, "message": "註冊成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== 天氣 API ==========
@app.get("/api/weather")
async def get_weather(city: str = "Taipei"):
    """獲取天氣資料"""
    weather = weather_service.get_weather(city)
    if weather:
        return weather.to_dict()
    raise HTTPException(status_code=404, detail="無法獲取天氣資料")

# ========== 上傳 API ==========
@app.post("/api/upload")
async def upload_images(
    files: List[UploadFile] = File(...),
    user_id: int = Form(...)
):
    """批次上傳圖片並進行 AI 辨識"""
    try:
        img_bytes_list = []
        file_names = []
        
        for file in files:
            content = await file.read()
            img_bytes_list.append(content)
            file_names.append(file.filename)
        
        tags_list = ai_service.batch_auto_tag(img_bytes_list)
        
        if not tags_list:
            return {"success": False, "message": "AI 辨識失敗"}
        
        success_items = []
        duplicate_count = 0
        fail_count = 0
        
        for img_bytes, tags, filename in zip(img_bytes_list, tags_list, file_names):
            img_hash = wardrobe_service.get_image_hash(img_bytes)
            is_duplicate, _ = wardrobe_service.check_duplicate_image(user_id, img_hash)
            
            if is_duplicate:
                duplicate_count += 1
                continue
            
            item = ClothingItem(
                user_id=user_id,
                name=tags.get('name', filename),
                category=tags.get('category', '其他'),
                color=tags.get('color', '未知'),
                style=tags.get('style', ''),
                warmth=tags.get('warmth', 5)
            )
            
            success, msg = wardrobe_service.save_item(item, img_bytes)
            
            if success:
                success_items.append(tags)
            else:
                fail_count += 1
        
        return {
            "success": True,
            "success_count": len(success_items),
            "duplicate_count": duplicate_count,
            "fail_count": fail_count,
            "items": success_items
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== 衣櫥 API ==========
@app.get("/api/wardrobe")
async def get_wardrobe(user_id: int):
    """獲取使用者衣櫥"""
    items = wardrobe_service.get_wardrobe(user_id)
    return {
        "success": True,
        "items": [item.to_dict() for item in items]
    }

@app.post("/api/wardrobe/delete")
async def delete_item(user_id: int = Form(...), item_id: int = Form(...)):
    """刪除單件衣物"""
    success = wardrobe_service.delete_item(user_id, item_id)
    return {"success": success}

@app.post("/api/wardrobe/batch-delete")
async def batch_delete(user_id: int = Form(...), item_ids: List[int] = Form(...)):
    """批次刪除衣物"""
    success, success_count, fail_count = wardrobe_service.batch_delete_items(user_id, item_ids)
    return {
        "success": success,
        "success_count": success_count,
        "fail_count": fail_count
    }

# ========== 推薦 API ==========
@app.post("/api/recommendation")
async def get_recommendation(
    user_id: int = Form(...),
    city: str = Form(...),
    style: str = Form(""),
    occasion: str = Form("外出遊玩")
):
    """獲取穿搭推薦"""
    try:
        wardrobe = wardrobe_service.get_wardrobe(user_id)
        
        if not wardrobe:
            return {"success": False, "message": "衣櫥是空的,請先上傳衣服"}
        
        weather = weather_service.get_weather(city)
        
        if not weather:
            return {"success": False, "message": "無法獲取天氣資料"}
        
        recommendation = ai_service.generate_outfit_recommendation(
            wardrobe, weather, style, occasion
        )
        
        if not recommendation:
            return {"success": False, "message": "AI 推薦生成失敗"}
        
        recommended_items = ai_service.parse_recommended_items(recommendation, wardrobe)
        
        return {
            "success": True,
            "recommendation": recommendation,
            "items": [item.to_dict() for item in recommended_items]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== 啟動 ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
