"""
FastAPI 後端 - AI Fashion Assistant
修復版本：正確處理 UUID
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request  # ✅ 添加 Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pathlib import Path
import sys
import os
import uuid

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
    """✅ 使用者登入 - 修復版本"""
    try:
        print(f"[INFO] 登入嘗試: {username}")
        
        # 查詢用戶
        result = supabase_client.client.table("users")\
            .select("*")\
            .eq("username", username)\
            .eq("password", password)\
            .execute()
        
        # ✅ 安全的檢查：只檢查是否不為空
        if result.data:
            user_id = result.data[0]['id']
            print(f"[INFO] 登入成功: {username} (ID: {user_id})")
            
            return {
                "success": True,
                "user_id": str(user_id),  # ✅ 確保返回字串
                "username": username
            }
        else:
            print(f"[WARNING] 登入失敗: {username} - 帳號或密碼錯誤")
            return {
                "success": False,
                "message": "帳號或密碼錯誤"
            }
            
    except Exception as e:
        print(f"[ERROR] 登入異常: {str(e)}")
        # ✅ 返回錯誤響應，而不是拋出異常
        return {
            "success": False,
            "message": f"登入失敗: {str(e)}"
        }


@app.post("/api/register")
async def register(username: str = Form(...), password: str = Form(...)):
    """✅ 使用者註冊 - 修復版本"""
    try:
        print(f"[INFO] 註冊嘗試: {username}")
        
        # ✅ 驗證輸入
        if not username or not password:
            return {
                "success": False,
                "message": "使用者名稱和密碼不能為空"
            }
        
        if len(password) < 6:
            return {
                "success": False,
                "message": "密碼至少需要 6 個字元"
            }
        
        # 檢查使用者是否已存在
        existing = supabase_client.client.table("users")\
            .select("id")\
            .eq("username", username)\
            .execute()
        
        # ✅ 安全的檢查
        if existing.data:
            print(f"[WARNING] 使用者已存在: {username}")
            return {
                "success": False,
                "message": "使用者名稱已存在"
            }
        
        # 插入新用戶
        # ✅ 重要：不提供 id，讓 Supabase 自動生成 UUID
        result = supabase_client.client.table("users")\
            .insert({
                "username": username,
                "password": password
            })\
            .execute()
        
        # ✅ 安全的檢查
        if result.data:
            new_user_id = result.data[0]['id']
            print(f"[INFO] 註冊成功: {username} (ID: {new_user_id})")
            
            return {
                "success": True,
                "message": "註冊成功"
            }
        else:
            # 如果 data 為空，檢查是否有錯誤
            print(f"[WARNING] 插入返回空結果: {result}")
            return {
                "success": False,
                "message": "註冊失敗，請稍後重試"
            }
            
    except Exception as e:
        print(f"[ERROR] 註冊異常: {str(e)}")
        # ✅ 返回錯誤響應，而不是拋出 HTTPException（會導致 503）
        return {
            "success": False,
            "message": f"註冊失敗: {str(e)}"
        }

# ========== 天氣 API ==========
@app.get("/api/weather")
async def get_weather(city: str = "Taipei"):
    """獲取天氣資料"""
    try:
        weather = weather_service.get_weather(city)
        if weather:
            return weather.to_dict()
        raise HTTPException(status_code=404, detail="無法獲取天氣資料")
    except Exception as e:
        print(f"[ERROR] 天氣查詢失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== 上傳 API ==========
@app.post("/api/upload")
async def upload_images(request: Request):
    """✅ 批次上傳圖片並進行 AI 辨識"""
    try:
        form = await request.form()
        
        # 獲取參數
        user_id = form.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="缺少 user_id")
        
        # ✅ 驗證 UUID 格式
        if not _is_valid_uuid(user_id):
            return {"success": False, "message": "無效的 UUID 格式"}
        
        print(f"[INFO] 上傳開始: user_id={user_id}")
        
        # 獲取所有檔案
        files = form.getlist("files")
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="沒有選擇檔案")
        
        if len(files) > config.max_batch_upload:
            raise HTTPException(
                status_code=400, 
                detail=f"最多只能上傳 {config.max_batch_upload} 張圖片"
            )
        
        # 讀取所有圖片 bytes
        img_bytes_list = []
        file_names = []
        
        for file in files:
            if not file.filename:
                continue
            
            if file.content_type not in ['image/jpeg', 'image/png', 'image/jpg']:
                continue
            
            content = await file.read()
            
            if len(content) > 10 * 1024 * 1024:  # 10MB
                continue
            
            img_bytes_list.append(content)
            file_names.append(file.filename)
        
        if not img_bytes_list:
            raise HTTPException(status_code=400, detail="沒有有效的圖片檔案")
        
        # 呼叫 AI 服務
        tags_list = ai_service.batch_auto_tag(img_bytes_list)
        
        if not tags_list:
            return {
                "success": False,
                "message": "AI 辨識失敗，請稍後重試"
            }
        
        # 儲存到資料庫
        success_items = []
        duplicate_count = 0
        fail_count = 0
        
        for img_bytes, tags, filename in zip(img_bytes_list, tags_list, file_names):
            try:
                # 檢查重複
                img_hash = wardrobe_service.get_image_hash(img_bytes)
                is_duplicate, existing_name = wardrobe_service.check_duplicate_image(
                    user_id, img_hash
                )
                
                if is_duplicate:
                    duplicate_count += 1
                    print(f"[INFO] 重複圖片: {filename}")
                    continue
                
                # 建立衣物項目
                item = ClothingItem(
                    user_id=user_id,  # ✅ UUID 字串
                    name=tags.get('name', filename),
                    category=tags.get('category', '其他'),
                    color=tags.get('color', '未知'),
                    style=tags.get('style', ''),
                    warmth=int(tags.get('warmth', 5))
                )
                
                # 儲存到 DB
                success, msg = wardrobe_service.save_item(item, img_bytes)
                
                if success:
                    success_items.append(tags)
                    print(f"[INFO] 成功儲存: {item.name}")
                else:
                    fail_count += 1
                    print(f"[ERROR] 儲存失敗: {filename}")
                    
            except Exception as e:
                fail_count += 1
                print(f"[ERROR] 處理圖片失敗: {str(e)}")
        
        return {
            "success": True,
            "success_count": len(success_items),
            "duplicate_count": duplicate_count,
            "fail_count": fail_count,
            "items": success_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 上傳端點異常: {str(e)}")
        raise HTTPException(status_code=500, detail="上傳處理失敗")

# ========== 衣櫥 API ==========
@app.get("/api/wardrobe")
async def get_wardrobe(user_id: str):
    """✅ 獲取使用者衣櫥"""
    try:
        # ✅ 驗證 UUID 格式
        if not _is_valid_uuid(user_id):
            return {"success": False, "message": "無效的 UUID 格式"}
        
        print(f"[INFO] 查詢衣櫥: user_id={user_id}")
        
        items = wardrobe_service.get_wardrobe(user_id)
        print(f"[INFO] 查詢完成: {len(items)} 件衣物")
        
        return {
            "success": True,
            "items": [item.to_dict() for item in items]
        }
    except Exception as e:
        print(f"[ERROR] 衣櫥查詢失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wardrobe/delete")
async def delete_item(user_id: str = Form(...), item_id: int = Form(...)):
    """✅ 刪除單件衣物"""
    try:
        # ✅ 驗證 UUID
        if not _is_valid_uuid(user_id):
            return {"success": False, "message": "無效的 UUID 格式"}
        
        success = wardrobe_service.delete_item(user_id, item_id)
        return {"success": success}
    except Exception as e:
        print(f"[ERROR] 刪除失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wardrobe/batch-delete")
async def batch_delete(user_id: str = Form(...), item_ids: List[int] = Form(...)):
    """✅ 批次刪除衣物"""
    try:
        # ✅ 驗證 UUID
        if not _is_valid_uuid(user_id):
            return {"success": False, "message": "無效的 UUID 格式"}
        
        success, success_count, fail_count = wardrobe_service.batch_delete_items(
            user_id, item_ids
        )
        return {
            "success": success,
            "success_count": success_count,
            "fail_count": fail_count
        }
    except Exception as e:
        print(f"[ERROR] 批量刪除失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== 推薦 API ==========
@app.post("/api/recommendation")
async def get_recommendation(
    user_id: str = Form(...),
    city: str = Form(...),
    style: str = Form(""),
    occasion: str = Form("外出遊玩")
):
    """✅ 獲取穿搭推薦"""
    try:
        # ✅ 驗證 UUID
        if not _is_valid_uuid(user_id):
            return {"success": False, "message": "無效的 UUID 格式"}
        
        print(f"[INFO] 推薦請求: user_id={user_id}, city={city}")
        
        wardrobe = wardrobe_service.get_wardrobe(user_id)
        
        if not wardrobe:
            return {"success": False, "message": "衣櫥是空的，請先上傳衣服"}
        
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
        print(f"[ERROR] 推薦生成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== 輔助函數 ==========

def _is_valid_uuid(value: str) -> bool:
    """✅ 驗證字串是否為有效的 UUID"""
    if not value or not isinstance(value, str):
        return False
    
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False

# ========== 啟動 ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
