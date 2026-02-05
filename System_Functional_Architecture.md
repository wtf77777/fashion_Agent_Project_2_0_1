# System Functional Architecture / 系統功能架構圖

## 1. System Overview (系統總覽)
本系統為基於 AI (Google Gemini) 與數據分析的智慧穿搭顧問平台，整合「智慧衣櫥管理」、「個人化偏好設定」與「情境式穿搭推薦」三大核心支柱。

## 2. Functional Modules (功能模組架構)

### 2.1 Smart Wardrobe Management (智慧衣櫥管理)
*   **Image Upload & Processing (圖片上傳處理)**
    *   支援多張衣物圖片批次上傳。
    *   自動去背與圖片正規化。
*   **AI Auto-Tagging (AI 自動標籤)**
    *   **Tier 1 / Tier 2 Model Strategy**: 採用階梯式 AI 模型 (Gemini Flash/Pro) 進行穩健辨識。
    *   **Attribute Recognition**: 自動辨識 `Category` (類別), `Color` (顏色), `Style` (15種風格).
    *   **Fallback Mechanism**: 若雲端 AI 繁忙，自動切換至本地模型 (Model A) 進行基礎辨識。
*   **Inventory CRUD (庫存管理)**
    *   檢視衣櫥列表、編輯單品資訊、刪除單品。

### 2.2 Personalization Engine (個人化引擎) - *[Planned]*
*   **User Profile (個人檔案)**
    *   **Body Metrics**: 身高 (Height)、體重 (Weight) 紀錄。
    *   **Thermal Preference**: 體感偏好設定 (怕冷 Cold Sensitive / 正常 Normal / 怕熱 Heat Sensitive)。
*   **Style DNA (風格基因)**
    *   **Favorite Styles**: 透過下拉選單選擇喜好風格 (支援多選)，並即時檢視風格定義。
    *   **Dislikes Management**: 避雷清單 (如：「不穿涼鞋」、「拒絕動物紋」)，AI 強制過濾。
    *   **Custom Notes**: 自訂風格文字描述。
*   **History & Feedback (歷史與回饋)**
    *   **Recommendation History**: 自動儲存過往的推薦結果、場合與日期。

### 2.3 AI Expert Recommendation (AI 專家推薦)
*   **Context Awareness (情境感知)**
    *   **Weather Integration**: 自動抓取當地即時天氣 (Temp, Description)，判斷保暖需求。
    *   **Occasion Parsing**: 解析使用者輸入場合 (如：約會、面試)，轉換為穿搭策略。
*   **Outfit Generation (穿搭生成)**
    *   **Rule-Based Filtering**: 根據天氣與避雷清單初篩衣物。
    *   **Generative Styling**: AI 根據「使用者身形」與「風格偏好」挑選上衣、下身、外套與配件的組合。
    *   **Stylist Advice**: 生成約 100 字的專業穿搭顧問建議 (包含修飾身形技巧)。
*   **Advanced Control (進階控制) - *[Planned]***
    *   **Anchor Item**: 指定單品搭配 (指定「今日必穿」的某件單品，AI 補完其餘部分)。
    *   **Shop the Look**: 缺件智慧導購 (若推薦單品衣櫥缺乏，提供外部購買連結)。

## 3. Technology Stack (技術架構)
*   **Frontend**: HTML5, Vanilla JavaScript, CSS3 (Modern UI).
*   **Backend**: Python FastAPI (High Performance Async API).
*   **Database**: Supabase (PostgreSQL) + JSONB for flexible data.
*   **AI Core**: Google Gemini API (Vision & Text Generation).
*   **External APIs**: Weather Service.
