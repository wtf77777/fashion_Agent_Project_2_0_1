# Outfit Recommendation Improvement Plan (Draft) / 穿搭推薦優化計畫 (草案)

## Status
**Phase**: Discussion (討論階段)
**User**: oreore

---

## 1. Goal (目標)
Enhance the existing AI outfit recommendation system to be more interactive, personalized, and practical.
提升現有的 AI 穿搭推薦系統，使其更具互動性、個人化且實用。

## 2. Selected Features (已選定功能)

### A. Advanced Anchor Item & Shopping (指定單品與智慧導購)
- **Selection Method (操作方式)**: Option B (In-page selection).
- **Details (細節)**:
    - User can select **multiple items** from their wardrobe (e.g., "I want to wear this top AND these shoes") via a pop-up selector in the specific recommendation interface.
    - AI builds the outfit around these locked items.
    - **[NEW] Shop the Look (缺件導購)**:
        - If the AI suggests an item category that the user *does not* have in their wardrobe (or if the best match is missing), the system will display a **Purchase Link**.
        - *Implementation strategy*: Generate dynamic search links (e.g., Shopee, Google Shopping, Uniqlo) based on the AI's suggested keywords (e.g., "Beige Wide-leg Trousers").
- **中文描述**:
    - **指定多件**: 在推薦頁面新增按鈕，跳出視窗讓使用者選擇一件或多件「今日必穿」的單品（如：指定上衣+鞋子）。
    - **智慧導購**: 如果 AI 推薦了某個單品（例如「米色寬褲」），但您的衣櫃裡沒有這類衣服，系統會自動生成 **購買連結**（搜尋各大電商平台），方便您補貨。

### B. Recommendation Diversity (智慧多樣性平衡)
- **Problem**: Current top 3 recommendations often repeat high-score items unnecessarily.
- **Solution (解決方案)**: Implement a "Soft Penalty" mechanism (倒扣分機制).
- **Logic**:
    - **Soft Penalty**: When calculating Outfit #2 and #3, items used in previous outfits will have their scores reduced (e.g., -20 points).
    - **Outcome**: The system will prefer *new* items. However, if a repeated item is an **exceptional match** (score is high enough to withstand the penalty), it will still be selected.
    - Matches user request: "Avoid repetition unless the outfit is exceptionally good."
- **中文描述**:
    - **智慧扣分機制**: 當一件單品在第一套被選用後，計算第二套時會**暫時扣除該單品的分數** (例如扣 20 分)。
    - **保留彈性**: 如果該單品與第二套的其他衣服**極度相配**（分數極高，即使被扣分後仍贏過其他選手），系統**依然會保留**它。
    - 達成目標：「原則上不重複，除非真的超搭」。

---

## 3. Updated AI Prompts (更新後的 AI 提示詞)
*Based on the new Personal Settings and Style Guide alignment.*

### A. Analysis Prompt (意圖解析)
```python
style_guide_text = "...(15種風格定義)..."

analysis_prompt = f"""
使用者資料:
- 性別/身形: {user_profile.gender} / {user_profile.height}cm / {user_profile.weight}kg
- 體感偏好: {user_profile.thermal_preference} (若為'怕冷'請增加保暖度權重)
- 避雷清單: {user_profile.dislikes} (絕對不可推薦此類單品)
- 自訂備註: {user_profile.custom_style_desc}

本次需求:
- 場合: "{occasion}"
- 風格偏好: "{style}" (若空白則參考: {user_profile.favorite_styles})
- 當地天氣: {weather.temp}°C ({weather.desc})

風格與規則:
請從以下【標準風格清單】中，解析出最符合使用者當下需求的一個核心風格標籤(parsed_style)，必須完全一致以便資料庫搜尋。
{style_guide_text}

請解析穿搭策略 (回傳 JSON): {{
    "normalized_occasion": "約會|日常|運動|上班|正式",
    "needs_outer": bool, (考量天氣與體感偏好)
    "vibe_description": "一段專為使用者寫的 30 字開場，需考慮其身形與風格",
    "parsed_style": "必須是上述 15 個風格之一 (例如: 日系(Japanese Cityboy))",
    "avoid_keywords": ["避雷關鍵字1", "避雷關鍵字2"]
}}
"""
```

### B. Detail Prompt (詳細建議)
```python
detail_prompt = f"""
身為專業穿搭顧問，請針對這位使用者({user_profile.height}cm/{user_profile.weight}kg)與以下 3 套方案寫一段建議。
重點：
1. 解釋為何適合今天的天氣({weather.temp}°C)與場合({occasion})。
2. 若使用者有設定體感偏好({user_profile.thermal_preference})或避雷，請提到你如何貼心考量。
3. 針對其身形給予修飾建議(例如: 顯高、顯瘦)。

方案內容:
{outfit_descriptions}

請輸出一段約 100 字的溫馨專業建議:
"""
```

---


---

## 4. Implementation Priorities (實作優先順序)
1. [ ] **Advanced Anchor Item & Shopping** (指定單品 + 導購連結)
2. [ ] **Recommendation Diversity** (解決重複推薦問題)
