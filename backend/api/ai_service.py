"""
AI 服務層 - Oreoooooo 終極穩定整合版
處理所有與 Gemini API 相關的業務邏輯，包含重試機制、高品質 Prompt 與階梯式辨識
"""
import json
import time
import re
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple, Tuple
from database.models import ClothingItem, WeatherData

from google.api_core.exceptions import ResourceExhausted, InternalServerError
from api.model_a_adapter import ModelAAdapter
from api.recommendation_engine import RecommendationEngine

class AIService:
    def __init__(self, api_key: str, rate_limit_seconds: int = 15):
        self.api_key = api_key
        self.rate_limit_seconds = rate_limit_seconds
        self.last_request_time = 0
        genai.configure(api_key=api_key)
        
        # 設定安全過濾 (關閉以避免誤判衣物圖片)
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        # 依照 Oreoooooo 要求，定義階梯模型 (Tier 1 & Tier 2)
        # 注意: 確保系統環境支援此模型名稱
        self.model_t1 = genai.GenerativeModel('gemini-2.5-flash', safety_settings=self.safety_settings)
        self.model_t2 = genai.GenerativeModel('gemini-3-flash-preview', safety_settings=self.safety_settings)
    
    def _rate_limit_wait(self):
        """API 速率限制保護 - 嚴格版"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_seconds:
            wait_time = self.rate_limit_seconds - time_since_last
            print(f"[AI] ⏳ 速率限制保護中，等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()

    def batch_auto_tag(self, img_bytes_list: List[bytes]) -> Optional[List[Dict]]:
        """
        Oreoooooo 階梯式自動標籤辨識:
        1. 先嘗試 Gemini 2.5-flash (具備重試)
        2. 若爆流量則試 Gemini 3-flash-preview (具備重試)
        3. 均失敗則 Fallback 到本地 Model A
        """
        print(f"[AI] 開始對 {len(img_bytes_list)} 件衣物進行階梯式辨識分析...")
        
        # A. 嘗試模型 1 (2.5-flash)
        results = self._call_gemini_with_robust_logic(self.model_t1, img_bytes_list, "Tier 1 (2.5-flash)")
        if results: return results
        
        # B. 嘗試模型 2 (3-preview)
        results = self._call_gemini_with_robust_logic(self.model_t2, img_bytes_list, "Tier 2 (3-preview)")
        if results: return results

        # C. 最終 Fallback - 本地 Model A (當 API 均不可用時)
        print("[AI] ⚠️ 所有 Gemini 模型均已達流量上限或失敗，啟動本地 Model A 辨識...")
        adapter = ModelAAdapter()
        final_results = []
        for idx, img_bytes in enumerate(img_bytes_list):
            local_result = adapter.analyze_image(img_bytes)
            if local_result:
                final_results.append({
                    "name": f"{local_result['colors'][0]} {local_result['category_zh']}" if local_result['colors'] else local_result['category_zh'],
                    "category": self._map_category_to_frontend(local_result['category']),
                    "color": local_result['colors'][0] if local_result['colors'] else "未知",
                    "style": local_result['style'][0] if local_result['style'] else "休閒"
                })
            else:
                final_results.append({"name": f"未知衣物 {idx+1}", "category": "上衣", "color": "未知", "style": "休閒"})
        
        print(f"[AI] ✅ 回歸本地 Model A辨識完成 ({len(final_results)} 件)")
        return final_results

    def _call_gemini_with_robust_logic(self, model, img_bytes_list, label) -> Optional[List[Dict]]:
        """原本最穩健的呼叫邏輯 (包含 Retry, JSON 清洗, Candidates 檢查)"""
        try:
            self._rate_limit_wait()
            print(f"[AI] 🚀 正在嘗試 {label}...")

            style_guide = """
            請從以下 15 種核心風格中，選擇最符合的一種(必選其一):
            1. 極簡(Minimalist): 黑白灰素色、剪裁俐落、冷淡風
            2. 日系(Japanese Cityboy): 寬鬆Oversized、多層次、大地色、自然舒適
            3. 韓系(Korean Chic): 修身剪裁、顯高顯瘦、都會精緻、流行元素
            4. 美式復古(American Vintage): 牛仔、格紋、大學T、古著感
            5. 街頭潮流(Streetwear): 大Logo、強烈配色、工裝、球鞋文化
            6. 正裝商務(Formal): 西裝、襯衫、適合職場
            7. 運動休閒(Athleisure): 瑜珈褲、防風材質、機能舒適
            8. 法式慵懶(French Chic): 條紋、針織、隨性優雅
            9. 千禧復古(Y2K): 元氣亮色、短版上衣、低腰褲、科技復古
            10. 老錢風(Old Money): 質感針織、Polo衫、低調奢華
            11. 波西米亞(Bohemian): 碎花、流蘇、圖騰、民族風
            12. 暗黑搖滾(Grunge/Punk): 破損、鉚釘、全黑層次、個性叛逆
            13. 賽博機能(Techwear): 全黑、多口袋、扣環織帶、未來感
            14. 甜美少女(Coquette): 蝴蝶結、蕾絲、粉嫩、可愛夢幻
            15. 山系戶外(Gorpcore): 登山機能、大地撞色、露營感
            (若皆不符則填"其他混搭")
            """

            # 補回最高品質的 Prompt
            prompt = f"""請仔細分析這 {len(img_bytes_list)} 件衣服,為每件衣服分別回傳 JSON 格式的標籤。
 
回傳格式必須是一個 JSON 陣列,包含 {len(img_bytes_list)} 個物件:
[
  {{
    "name": "衣服名稱(如:白色T恤、牛仔褲)",
    "category": "上衣|下身|外套|鞋子|配件",
    "color": "主要顏色",
    "style": "請依據下方[風格定義清單]填寫"
  }},
  ... (依序對應每張圖片)
]

[風格定義清單]:
{style_guide}
 
重要規則:
1. 只回傳 JSON 陣列,不要任何其他文字
2. 不要包含 ```json 或任何 Markdown 標籤
3. 陣列中的順序必須與圖片順序一致
4. 每個物件都必須包含這 4 個欄位
5. 風格欄位必須嚴格遵守上述 15 種分類名稱
"""
            content_parts = [{"mime_type": "image/jpeg", "data": img} for img in img_bytes_list]
            content_parts.insert(0, prompt)

            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = model.generate_content(content_parts)
                    return self._parse_and_validate_response(response, len(img_bytes_list))
                except ResourceExhausted:
                    retry_count += 1
                    wait_time = 30 * retry_count
                    print(f"[AI] ⚠️ {label} 速率限制，等待 {wait_time} 秒後重試 ({retry_count}/{max_retries})...")
                    time.sleep(wait_time)
                except Exception as e:
                    print(f"[AI] {label} 呼叫異常: {e}")
                    break
            return None
        except Exception as e:
            print(f"[AI] {label} 區塊執行失敗: {e}")
            return None

    def _parse_and_validate_response(self, response, count):
        """原本代碼中最完整的解析邏輯"""
        try:
            # 檢查是否存在 content
            try:
                raw_text = response.text
            except ValueError:
                if response.candidates and response.candidates[0].content.parts:
                    raw_text = response.candidates[0].content.parts[0].text
                else:
                    return None
            
            clean_text = raw_text.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_text)
            
            if isinstance(data, list) and len(data) == count:
                return data
            return None
        except:
            return None

    def _extract_response_text(self, response) -> str:
        """安全取得 Gemini 回傳文字內容"""
        if response is None:
            return ""

        try:
            raw_text = response.text
            if raw_text:
                return str(raw_text)
        except ValueError:
            pass
        except Exception:
            pass

        try:
            if response.candidates and response.candidates[0].content.parts:
                return str(response.candidates[0].content.parts[0].text or "")
        except Exception:
            return ""

        return ""

    def _safe_json_loads(self, text: str):
        """嘗試解析 JSON，失敗時再抽取最可能的 JSON 區塊"""
        if not text:
            return None

        cleaned = text.strip().replace('```json', '').replace('```', '').strip()
        if not cleaned:
            return None

        try:
            return json.loads(cleaned)
        except Exception:
            pass

        # 嘗試抓出第一段 JSON 物件或陣列
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                return None

        return None

    def generate_outfit_recommendation(
        self, wardrobe: List[ClothingItem], weather: WeatherData, style: str, occasion: str,
        user_profile: Optional[Dict] = None,
        locked_items: Optional[List[str]] = None  # ✅ 優先級 3：指定單品鎖定
    ) -> Optional[Dict]:
        """產出智能穿搭組合 - 含完整解析與 Gemini 結語、支援個人偏好 & 指定單品"""
        try:
            self._rate_limit_wait()

            locked_item_ids = list(locked_items) if locked_items else []
            locked_item_ids_set = set(locked_item_ids)
            locked_item_ids_str = set(str(x) for x in locked_item_ids)

            def is_locked(item_id) -> bool:
                return item_id in locked_item_ids_set or str(item_id) in locked_item_ids_str
            
            # ✅ 解析個人資料
            dislikes = ""
            thermal_preference = "normal"
            custom_desc = ""
            
            if user_profile:
                dislikes = user_profile.get("dislikes", "") or ""
                thermal_preference = user_profile.get("thermal_preference", "normal") or "normal"
                custom_desc = user_profile.get("custom_style_desc", "") or ""
            
            # 1. 意圖解析 - 增強提示詞融入個人資料
            user_height = user_profile.get("height") if user_profile else None
            user_weight = user_profile.get("weight") if user_profile else None
            user_gender = user_profile.get("gender") if user_profile else "中性"
            favorite_styles = user_profile.get("favorite_styles", []) if user_profile else []
            
            # ✅ 處理 None 值
            user_height_str = f"{user_height} cm" if user_height else "未設定"
            user_weight_str = f"{user_weight} kg" if user_weight else "未設定"
            favorite_styles_str = "、".join(favorite_styles) if favorite_styles else "無特殊偏好"
            
            # ✅ 優先級 3：處理指定單品
            locked_item_details = ""
            if locked_items:
                locked_wardrobe = [item for item in wardrobe if is_locked(item.id)]
                if locked_wardrobe:
                    locked_desc = "、".join([f"{item.name}({item.color})" for item in locked_wardrobe])
                    locked_item_details = f"\n【指定今日單品】必須包含: {locked_desc}"
            
            analysis_prompt = f"""
            【使用者資料】
            性別/身形: {user_gender} / {user_height_str} / {user_weight_str}
            習慣風格: {favorite_styles_str}
            體感偏好：{thermal_preference} (若為'cold_sensitive'請增加保暖度權重)
            避雷清單：{dislikes if dislikes else '無'}
            自訂備註：{custom_desc if custom_desc else '無'}{locked_item_details}
            
            【本次需求】
            場合："{occasion}"
            風格偏好：{style}
            天氣：{weather.temp}度 ({weather.desc})
            
            請解析場景意圖與天氣影響。
            回傳 JSON: {{
                "normalized_occasion": "約會|日常|運動|上班|正式",
                "needs_outer": bool,
                "vibe_description": "一段專為使用者寫的 30 字開場",
                "parsed_style": "核心風格標籤"
            }}
            """
            res = self.model_t1.generate_content(analysis_prompt)
            analysis_text = self._extract_response_text(res)
            analysis = self._safe_json_loads(analysis_text)

            if not isinstance(analysis, dict):
                print("[AI] ⚠️ 場景解析回傳非 JSON，改用預設解析值")
                analysis = {
                    "normalized_occasion": "日常",
                    "needs_outer": weather.temp < 22,
                    "vibe_description": "今天就走舒適俐落的日常穿搭風格。",
                    "parsed_style": style or "日常"
                }

            # ✅ 根據體感偏好調整保暖需求
            needs_outer = bool(analysis.get("needs_outer", weather.temp < 22))
            if thermal_preference == "cold_sensitive" and weather.temp < 24:
                needs_outer = True  # 強制加外套
            elif thermal_preference == "heat_sensitive" and weather.temp > 25:
                needs_outer = False  # 儘量不穿外套

            normalized_occasion = analysis.get("normalized_occasion") or "日常"
            parsed_style = analysis.get("parsed_style") or style or "日常"
            
            # 2. 引擎從真實衣櫥挑選 - 實現軟扣分機制（推薦 3 套時追蹤已使用單品）
            engine = RecommendationEngine()
            outfits = []
            # ✅ 優先級 3 修復：初始化 used_items 為空，但稍後會加入 locked_items
            used_items = list(locked_item_ids)  # 初始化為指定單品（必須包含）
            
            for set_idx in range(3):
                try:
                    # 在每一套時傳入已使用單品，實現軟扣分
                    single_outfit = engine.recommend(
                        wardrobe, weather, normalized_occasion, "中性", 
                        parsed_style, needs_outer, used_items=used_items
                    )
                    
                    if single_outfit:
                        outfits.append(single_outfit[0])  # 取第 1 套即可
                        
                        # ✅ 提取該套中的單品 ID 加入 used_items（不包括指定單品，防止後續套裝排除它們）
                        if single_outfit[0].get('items'):
                            for item in single_outfit[0]['items']:
                                if item.get('id') and not is_locked(item['id']):
                                    # 只追蹤非指定的單品，指定單品應在每套中重複出現
                                    used_items.append(item['id'])
                except Exception as e:
                    print(f"[AI] 第 {set_idx+1} 套推薦出錯: {e}")
                    continue
            
            if not outfits:
                return None
            
            # ✅ 過濾避雷清單
            if dislikes:
                dislike_keywords = [kw.strip().lower() for kw in dislikes.split(',')]
                filtered_outfits = []
                
                for outfit in outfits:
                    should_include = True
                    for item in outfit['items']:
                        item_name = (item.get('name', '') + item.get('color', '')).lower()
                        if any(kw in item_name for kw in dislike_keywords):
                            should_include = False
                            break
                    
                    if should_include:
                        filtered_outfits.append(outfit)
                
                outfits = filtered_outfits[:3] if filtered_outfits else outfits[:3]

            # 3. 針對具體衣服產出 100 字溫馨總結 (Gemini 結語) - 融入身形修飾建議
            body_shape_tip = ""
            if user_height and user_weight:
                try:
                    height_cm = float(user_height)
                    weight_kg = float(user_weight)
                    # 簡單 BMI 計算幫助判斷修飾建議
                    bmi = weight_kg / ((height_cm / 100) ** 2)
                    if bmi < 18.5:
                        body_shape_tip = "此使用者偏瘦，應選擇有蓬度/紋理的衣服來增加視覺豐盈感，避免過度貼身。"
                    elif bmi > 25:
                        body_shape_tip = "此使用者偏重，應選擇直線條/深色/豎紋路的衣服來顯瘦，避免過度鬆散或橫紋。"
                    else:
                        body_shape_tip = f"此使用者身材勻稱({height_cm}cm/{weight_kg}kg)，可選擇符合氣質的任何剪裁。"
                except (ValueError, TypeError):
                    body_shape_tip = "無法解析身形數據，建議無身形限制。"
            
            detail_prompt = f"""身為專業穿搭顧問，請針對以下這位使用者({user_gender}/{user_height_str}/{user_weight_str})寫一段約 100 字的溫馨專業建議。

{body_shape_tip}

重點：
1. 解釋為何這 3 套適合今天的天氣({weather.temp}度)與場合({occasion})
2. 若使用者有體感偏好({thermal_preference})或避雷，提到你如何貼心考量
3. 針對其身形給予修飾建議
4. 根據其習慣風格({favorite_styles_str})評論搭配是否符合氣質

方案詳情：
"""
            for i, o in enumerate(outfits):
                names = [f"{it['color']}{it['name']}" for it in o['items']]
                detail_prompt += f"方案{i+1}: {', '.join(names)}\n"
            
            self._rate_limit_wait()
            reason_res = self.model_t1.generate_content(detail_prompt)
            
            return {
                "vibe": analysis.get("vibe_description") or "今天就走舒適俐落的日常穿搭風格。",
                "detailed_reasons": reason_res.text,
                "recommendations": outfits
            }
        except Exception as e:
            print(f"[AI Recommendation Error] {e}")
            return None

    def _map_category_to_frontend(self, model_cat: str) -> str:
        """將 Model A 的類別對應到前端 (Oreoooooo 指定完整版)"""
        UPPER = ['Tee', 'Blouse', 'Top', 'Tank', 'Jersey', 'Hoodie', 'Sweater']
        LOWER = ['Jeans', 'Shorts', 'Skirt', 'Sweatpants', 'Joggers', 'Leggings', 'Chinos']
        OUTER = ['Jacket', 'Coat', 'Blazer', 'Cardigan', 'Parka', 'Kimono']
        FULL = ['Dress', 'Jumpsuit', 'Romper']
        
        if model_cat in UPPER: return "上衣"
        if model_cat in LOWER: return "下身"
        if model_cat in OUTER: return "外套"
        if model_cat in FULL: return "上衣"
        return "配件"

    def parse_recommended_items(self, ai_response: str, wardrobe: List[ClothingItem]) -> List[ClothingItem]:
        """保留解析函數以支援主流程"""
        recommended_items = []
        res = str(ai_response).lower()
        for item in wardrobe:
            if (item.name and item.name.lower() in res) or \
               (f"{item.color}{item.category}".lower() in res.replace(' ', '')):
                recommended_items.append(item)
        return recommended_items
