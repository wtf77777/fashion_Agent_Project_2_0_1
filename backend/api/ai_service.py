"""
AI 服務層
處理所有與 Gemini API 相關的業務邏輯
"""
import json
import time
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple
from database.models import ClothingItem, WeatherData

from google.api_core.exceptions import ResourceExhausted

class AIService:
    def __init__(self, api_key: str, rate_limit_seconds: int = 15):
        self.api_key = api_key
        # ... (init skipped for brevity, keeping existing) ...
        self.rate_limit_seconds = rate_limit_seconds
        self.last_request_time = 0
        genai.configure(api_key=api_key)
        # 設定安全過濾 (關閉以避免誤判衣物圖片)
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
        
        # 使用使用者指定的版本 2.5-flash
        self.model = genai.GenerativeModel('gemini-3-flash-preview', safety_settings=self.safety_settings)
    
    def _rate_limit_wait(self):
        """API 速率限制保護"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_seconds:
            wait_time = self.rate_limit_seconds - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()

    def batch_auto_tag(self, img_bytes_list: List[bytes]) -> Optional[List[Dict]]:
        # ... (skipping docstring) ...
        try:
            print(f"[AI] 開始批次辨識 {len(img_bytes_list)} 張圖片...")
            
            # 初始速率限制等待
            self._rate_limit_wait()
            
            prompt = f"""請仔細分析這 {len(img_bytes_list)} 件衣服... (省略 prompt 內容以節省 tokens，實際替換請保留完整 prompt) ..."""
            
            # (重建 prompt 和 content_parts 的代碼)
            prompt = f"""請仔細分析這 {len(img_bytes_list)} 件衣服,為每件衣服分別回傳 JSON 格式的標籤。

回傳格式必須是一個 JSON 陣列,包含 {len(img_bytes_list)} 個物件:
[
  {{
    "name": "衣服名稱(如:白色T恤、牛仔褲)",
    "category": "上衣|下身|外套|鞋子|配件",
    "color": "主要顏色",
    "style": "風格(如:休閒、正式、運動)",
    "warmth": 保暖度1-10的數字
  }},
  ... (依序對應每張圖片)
]

重要規則:
1. 只回傳 JSON 陣列,不要任何其他文字
2. 不要包含 ```json 或任何 Markdown 標籤
3. 陣列中的順序必須與圖片順序一致
4. 每個物件都必須包含所有 5 個欄位
"""
            
            content_parts = [prompt]
            for idx, img_bytes in enumerate(img_bytes_list):
                content_parts.append({
                    "mime_type": "image/jpeg",
                    "data": img_bytes
                })
                print(f"[AI] 準備圖片 {idx+1}/{len(img_bytes_list)}, 大小={len(img_bytes)} bytes")
            
            print(f"[AI] 發送請求到 Gemini API...")
            
            # 重試機制
            max_retries = 3
            retry_count = 0
            response = None
            
            while retry_count < max_retries:
                try:
                    response = self.model.generate_content(content_parts)
                    break # 成功則跳出迴圈
                except ResourceExhausted as e:
                    retry_count += 1
                    wait_time = 30 * retry_count # 30s, 60s, 90s
                    print(f"[AI] ⚠️ 觸發速率限制 (429)，等待 {wait_time} 秒後重試 ({retry_count}/{max_retries})...")
                    print(f"[AI] 錯誤訊息: {str(e)}")
                    time.sleep(wait_time)
                    if retry_count == max_retries:
                        raise e # 達到最大重試次數，拋出異常
            
            print(f"[AI] 收到 API 回應")
            
            # ... (接續原本的回應處理邏輯) ...
            try:
                raw_text = response.text
            except ValueError:
                # ... (error handling) ...
                if response.candidates and response.candidates[0].content.parts:
                    raw_text = response.candidates[0].content.parts[0].text
                else:
                    raise ValueError("AI 回應為空，無法解析")
            
            print(f"[AI] 原始回應長度: {len(raw_text)} 字元")
            print(f"[AI] 原始回應前 200 字元: {raw_text[:200]}")
            
            clean_text = raw_text.strip()
            clean_text = clean_text.replace('```json', '').replace('```', '').strip()
            print(f"[AI] 清理後回應長度: {len(clean_text)} 字元")
            
            # 解析 JSON
            print(f"[AI] 開始解析 JSON...")
            tags_list = json.loads(clean_text)
            print(f"[AI] JSON 解析成功")
            
            # 驗證回應
            if not isinstance(tags_list, list):
                raise ValueError(f"AI 回傳格式錯誤: 應為陣列,實際為 {type(tags_list)}")
            
            print(f"[AI] 驗證陣列長度: 預期={len(img_bytes_list)}, 實際={len(tags_list)}")
            if len(tags_list) != len(img_bytes_list):
                raise ValueError(f"AI 回傳數量不符: 預期 {len(img_bytes_list)} 件,實際 {len(tags_list)} 件")
            
            # 驗證必要欄位
            required_fields = ['name', 'category', 'color', 'warmth']
            for idx, tags in enumerate(tags_list):
                print(f"[AI] 驗證第 {idx+1} 件衣服: {tags}")
                for field in required_fields:
                    if field not in tags:
                        raise ValueError(f"第 {idx+1} 件衣服缺少必要欄位: {field}")
                
                tags['warmth'] = int(tags['warmth'])
            
            print(f"[AI] ✅ 批次辨識完成,成功辨識 {len(tags_list)} 件衣服")
            return tags_list
            
        except json.JSONDecodeError as e:
            print(f"[AI] ❌ JSON 解析錯誤: {str(e)}")
            print(f"[AI] 錯誤位置: 第 {e.lineno} 行, 第 {e.colno} 列")
            print(f"[AI] 問題文字: {e.doc[:500] if hasattr(e, 'doc') else '無法取得'}")
            return None
        except Exception as e:
            print(f"[AI] ❌ 批次 AI 標籤失敗: {str(e)}")
            import traceback
            print(f"[AI] 詳細錯誤: {traceback.format_exc()}")
            return None
    
    def generate_outfit_recommendation(
        self, 
        wardrobe: List[ClothingItem],
        weather: WeatherData,
        style: str,
        occasion: str
    ) -> Optional[str]:
        """
        生成穿搭推薦
        
        Args:
            wardrobe: 衣櫥列表
            weather: 天氣資料
            style: 風格偏好
            occasion: 場合
            
        Returns:
            AI 推薦文字或 None
        """
        try:
            self._rate_limit_wait()
            
            # 準備衣櫥摘要（不含圖片資料）
            wardrobe_summary = [
                {k: v for k, v in item.to_dict().items() if k != 'image_data'}
                for item in wardrobe
            ]
            
            prompt = f"""
你是一位專業的 AI 時尚顧問。請根據以下資訊推薦今日穿搭:

**情境資訊:**
- 城市: {weather.city}
- 溫度: {weather.temp}°C (體感 {weather.feels_like}°C)
- 天氣: {weather.desc}
- **場合/活動: {occasion}**
- **指定風格: {style}**

**使用者衣櫥:**
{json.dumps(wardrobe_summary, ensure_ascii=False, indent=2)}

**請提供:**
1. 推薦的完整穿搭組合,必須符合「{style}」風格並適合「{occasion}」場合。
2. 每件單品的選擇理由 (需綜合考慮天氣、風格特色與場合得體度)。
3. 整體風格說明與針對「{occasion}」的穿搭小建議。

請用親切、專業的口吻回答,使用繁體中文。
"""
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"AI 推薦失敗: {str(e)}")
            return None
    
    def parse_recommended_items(
        self, 
        ai_response: str, 
        wardrobe: List[ClothingItem]
    ) -> List[ClothingItem]:
        """
        解析 AI 推薦文字,提取推薦的衣物 ID
        
        Args:
            ai_response: AI 回應文字
            wardrobe: 完整衣櫥列表
            
        Returns:
            推薦的衣物列表
        """
        recommended_items = []
        response_lower = ai_response.lower()
        
        for item in wardrobe:
            item_name = item.name.lower()
            item_category = item.category.lower()
            item_color = item.color.lower()
            
            # 使用名稱、類別、顏色進行匹配
            if (item_name and item_name in response_lower) or \
               (item_color and item_category and f"{item_color}{item_category}" in response_lower.replace(' ', '')):
                recommended_items.append(item)
        
        return recommended_items
