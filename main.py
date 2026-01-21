from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from config import AppConfig
from database.supabase_client import SupabaseClient
from api.ai_service import AIService
from api.weather_service import WeatherService
from api.wardrobe_service import WardrobeService
from database.models import ClothingItem

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = AppConfig.from_env()
supabase_client = SupabaseClient(config.supabase_url, config.supabase_key)
ai_service = AIService(config.gemini_api_key)
weather_service = WeatherService(config.weather_api_key)
wardrobe_service = WardrobeService(supabase_client)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ========== 認證 ==========

@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """登入"""
    try:
        result = supabase_client.client.table("users")\
            .select("id")\
            .eq("username", username)\
            .eq("password", password)\
            .execute()
        
        if result.data:
            return {
                "success": True,
                "user_id": str(result.data[0]['id']),
                "username": username
            }
        
        return {"success": False, "message": "帳號或密碼錯誤"}
    except Exception as e:
        print(f"[ERROR] 登入: {str(e)}")
        return {"success": False, "message": "登入失敗"}

@app.post("/api/register")
async def register(username: str = Form(...), password: str = Form(...)):
    """註冊"""
    try:
        # 檢查重複
        existing = supabase_client.client.table("users")\
            .select("id")\
            .eq("username", username)\
            .execute()
        
        if existing.data:
            return {"success": False, "message": "使用者名稱已存在"}
        
        # 新增用戶（讓 Supabase 自動生成 UUID）
        result = supabase_client.client.table("users")\
            .insert({"username": username, "password": password})\
            .execute()
        
        if result.data:
            return {"success": True, "message": "註冊成功"}
        
        return {"success": False, "message": "註冊失敗"}
    except Exception as e:
        print(f"[ERROR] 註冊: {str(e)}")
        return {"success": False, "message": "註冊失敗"}

# ========== 天氣 ==========

@app.get("/api/weather")
async def get_weather(city: str = "Taipei"):
    """天氣"""
    try:
        weather = weather_service.get_weather(city)
        return weather.to_dict() if weather else {"error": "無法獲取天氣"}
    except Exception as e:
        print(f"[ERROR] 天氣: {str(e)}")
        return {"error": str(e)}

# ========== 上傳 ==========

@app.post("/api/upload")
async def upload_images(request: Request):
    """上傳衣物 - 完整除錯版本"""
    try:
        print("[DEBUG] ========== 開始上傳流程 ==========")
        
        form = await request.form()
        user_id = form.get("user_id")
        files = form.getlist("files")
        
        print(f"[INFO] user_id: {user_id} (type: {type(user_id)})")
        print(f"[INFO] 檔案數量: {len(files) if files else 0}")
        
        if not user_id or not files:
            print("[ERROR] 缺少必要參數")
            return {"success": False, "message": "缺少必要參數"}
        
        # 讀取圖片
        img_bytes_list = []
        file_names = []
        
        for idx, file in enumerate(files):
            content = await file.read()
            img_bytes_list.append(content)
            file_names.append(file.filename)
            print(f"[INFO] 檔案 {idx+1}: {file.filename} ({len(content)} bytes)")
        
        # AI 辨識
        print("[INFO] 開始 AI 辨識...")
        tags_list = ai_service.batch_auto_tag(img_bytes_list)
        print(f"[INFO] AI 辨識結果: {tags_list}")
        
        if not tags_list:
            print("[ERROR] AI 辨識返回 None")
            return {"success": False, "message": "AI 辨識失敗"}
        
        # 儲存
        print("[INFO] 開始儲存到資料庫...")
        success_count = 0
        fail_count = 0
        success_items = []
        
        for idx, (img_bytes, tags, filename) in enumerate(zip(img_bytes_list, tags_list, file_names)):
            try:
                print(f"[INFO] 處理第 {idx+1} 件: {tags.get('name')}")
                
                item = ClothingItem(
                    user_id=str(user_id),  # ✅ 確保是字串
                    name=tags.get('name', filename),
                    category=tags.get('category', '其他'),
                    color=tags.get('color', '未知'),
                    style=tags.get('style', ''),
                    warmth=int(tags.get('warmth', 5))
                )
                
                print(f"[DEBUG] 準備儲存: user_id={item.user_id}, name={item.name}")
                success, msg = wardrobe_service.save_item(item, img_bytes)
                
                if success:
                    print(f"[SUCCESS] 第 {idx+1} 件儲存成功")
                    success_count += 1
                    success_items.append(tags)
                else:
                    print(f"[ERROR] 第 {idx+1} 件儲存失敗: {msg}")
                    fail_count += 1
                    
            except Exception as e:
                print(f"[ERROR] 處理第 {idx+1} 件時發生異常:")
                print(f"  錯誤類型: {type(e).__name__}")
                print(f"  錯誤訊息: {str(e)}")
                import traceback
                print(f"[TRACE] {traceback.format_exc()}")
                fail_count += 1
        
        print(f"[INFO] ========== 上傳完成: 成功 {success_count}, 失敗 {fail_count} ==========")
        
        return {
            "success": True,
            "success_count": success_count,
            "fail_count": fail_count,
            "duplicate_count": 0,
            "items": success_items
        }
        
    except Exception as e:
        print(f"[ERROR] 上傳流程異常:")
        print(f"  錯誤類型: {type(e).__name__}")
        print(f"  錯誤訊息: {str(e)}")
        import traceback
        print(f"[TRACE] {traceback.format_exc()}")
        return {"success": False, "message": f"上傳失敗: {str(e)}"}

# ========== 衣櫥 ==========

@app.get("/api/wardrobe")
async def get_wardrobe(user_id: str):
    """取得衣櫥"""
    try:
        items = wardrobe_service.get_wardrobe(user_id)
        return {"success": True, "items": [item.to_dict() for item in items]}
    except Exception as e:
        print(f"[ERROR] 衣櫥: {str(e)}")
        return {"success": False, "message": "查詢失敗"}

@app.post("/api/wardrobe/delete")
async def delete_item(user_id: str = Form(...), item_id: int = Form(...)):
    """刪除衣物"""
    try:
        success = wardrobe_service.delete_item(user_id, item_id)
        return {"success": success}
    except Exception as e:
        print(f"[ERROR] 刪除: {str(e)}")
        return {"success": False}

@app.post("/api/wardrobe/batch-delete")
async def batch_delete(user_id: str = Form(...), item_ids: List[int] = Form(...)):
    """批量刪除"""
    try:
        success, count, fail = wardrobe_service.batch_delete_items(user_id, item_ids)
        return {"success": success, "success_count": count, "fail_count": fail}
    except Exception as e:
        print(f"[ERROR] 批量刪除: {str(e)}")
        return {"success": False, "success_count": 0, "fail_count": len(item_ids)}

# ========== 推薦 ==========

@app.post("/api/recommendation")
async def get_recommendation(
    user_id: str = Form(...),
    city: str = Form(...),
    style: str = Form(""),
    occasion: str = Form("外出遊玩")
):
    """推薦衣搭"""
    try:
        wardrobe = wardrobe_service.get_wardrobe(user_id)
        if not wardrobe:
            return {"success": False, "message": "衣櫥是空的"}
        
        weather = weather_service.get_weather(city)
        if not weather:
            return {"success": False, "message": "無法獲取天氣"}
        
        recommendation = ai_service.generate_outfit_recommendation(
            wardrobe, weather, style or "不限", occasion
        )
        if not recommendation:
            return {"success": False, "message": "推薦生成失敗"}
        
        items = ai_service.parse_recommended_items(recommendation, wardrobe)
        
        return {
            "success": True,
            "recommendation": recommendation,
            "items": [item.to_dict() for item in items]
        }
    except Exception as e:
        print(f"[ERROR] 推薦: {str(e)}")
        return {"success": False, "message": "推薦失敗"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
