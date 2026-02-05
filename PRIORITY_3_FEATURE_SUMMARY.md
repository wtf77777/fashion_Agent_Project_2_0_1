# 優先級 3 功能實現概要

## ✅ 已完成：指定單品鎖定 + 導購連結

### 1️⃣ **指定單品鎖定 (Anchor Items)**
**目的**: 允許使用者在獲取推薦前，指定必須包含的衣物

#### 前端組件
- **anchor-item.js** (新建)
  - `AnchorItemUI` 物件：管理單品選擇狀態
  - `openModal()`: 載入衣櫥並顯示選擇界面
  - `confirmSelection()`: 儲存選擇到 localStorage
  - 限制：最多選擇 3 件

- **anchor-item.css** (新建)
  - Modal 樣式 (overlay + 卡片網格)
  - 選擇狀態視覺反饋（綠色邊框 + 勾選符號）
  - 響應式設計

- **index.html** (修改)
  - 添加「🔒 指定單品」按鈕（帶計數徽章）
  - 插入 anchor-modal HTML

#### 後端集成
- **main.py** (修改)
  - POST /api/recommendation 新增 `locked_items` 參數
  - 接收 JSON 格式的指定單品 ID 列表

- **ai_service.py** (修改)
  - `generate_outfit_recommendation()` 簽名新增 `locked_items` 參數
  - 在 AI 提示詞中添加「【指定今日單品】必須包含:...」約束
  - AI 將根據此約束生成包含指定單品的推薦

#### 工作流程
```
使用者點擊「🔒 指定單品」
  ↓
Modal 顯示衣櫥所有單品（卡片視圖）
  ↓
使用者選擇最多 3 件
  ↓
點擊「✅ 確認指定」
  ↓
儲存到 localStorage (anchorItems)
  ↓
獲取推薦時，從 localStorage 讀取指定單品 ID
  ↓
API 傳遞 locked_items 參數給後端
  ↓
AI 在生成推薦時遵循約束
```

---

### 2️⃣ **缺件導購連結 (Shopping Links)**
**目的**: 若 AI 推薦的單品不在衣櫥中，提供購物平台直接連結

#### 前端組件
- **ShoppingLinkUI** 物件 (anchor-item.js)
  - `generateShoppingLinks(itemName)`: 生成 5 大平台搜尋連結
    - 🔴 蝦皮 (Shopee)
    - 💗 momo購物網
    - 🔵 Google購物
    - 🔴 UNIQLO
    - ⚫ PChome 24h購物
  
  - `renderShoppingButtons()`: 渲染購物按鈕組

- **recommendation.js** (修改)
  - `renderClothingItem()`: 檢測單品是否在衣櫥中
  - 若不在，添加購物連結容器
  - 在 `renderRecommendationSets()` 後執行購物按鈕渲染

#### 購物連結格式
```
蝦皮: https://shopee.tw/search?keyword=[商品名稱]
momo: https://www.momoshop.com.tw/search/searchShop.jsp?searchKeyword=[商品名稱]
Google: https://www.google.com/shopping/search?q=[商品名稱]
UNIQLO: https://www.uniqlo.com/tw/zh_TW/search?q=[商品名稱]
PChome: https://ecshop.pchome.com.tw/search/[商品名稱]
```

#### 檢測邏輯
```javascript
if (!item.id || item.id === 'ai_suggested' || !item.image_data) {
    // → 這是 AI 建議的新單品，顯示導購連結
}
```

---

## 🔧  技術整合

### 數據流
```
前端 recommendation.js
  ├─ 讀取 localStorage(anchorItems) → 取得指定單品 ID 列表
  └─ API.getRecommendation(city, style, occasion, lockedItemIds)
      ↓
後端 main.py
  ├─ 接收 locked_items 參數
  └─ AIService.generate_outfit_recommendation(..., locked_items=locked_item_ids)
      ↓
AI 服務層
  ├─ 將指定單品詳情添加到 AI 提示詞
  ├─ "【指定今日單品】必須包含: 黑色長褲, 米色上衣..."
  └─ 生成包含這些單品的 3 套推薦
      ↓
前端渲染推薦結果
  ├─ 若單品在衣櫥 (image_data 存在) → 顯示圖片
  └─ 若單品是 AI 建議 (無 image_data) → 顯示購物連結
```

### 文件修改清單
| 文件 | 類型 | 修改內容 |
|------|------|--------|
| **anchor-item.js** | 新建 | AnchorItemUI + ShoppingLinkUI 物件 |
| **anchor-item.css** | 新建 | Modal 樣式 + 購物按鈕樣式 |
| **index.html** | 修改 | CSS/JS 引入 + 按鈕 + Modal HTML |
| **api.js** | 修改 | getRecommendation() 簽名添加 lockedItemIds 參數 |
| **recommendation.js** | 修改 | handleGetRecommendation() 讀取 anchorItems, renderClothingItem() 添加購物連結邏輯 |
| **main.py** | 修改 | POST /api/recommendation 添加 locked_items 參數 |
| **ai_service.py** | 修改 | generate_outfit_recommendation() 簽名 + 提示詞約束 |

---

## 🎯 使用者體驗

### 場景 1：指定必穿單品
```
Alice 買了一條新牛仔褲，想看看如何搭配
→ 點擊「🔒 指定單品」
→ 在衣櫥中選擇這條牛仔褲
→ 點擊「獲取推薦」
→ AI 生成的 3 套推薦都包含這條牛仔褲
```

### 場景 2：缺件導購
```
AI 推薦「白色運動鞋」，但 Bob 衣櫥沒有
→ 在推薦卡片上看到「🛍️ 缺件導購」
→ 點擊「蝦皮」或「UNIQLO」
→ 直接跳轉到搜尋頁面，購買建議的鞋子
```

---

## ✅ 驗證清單

- [x] 所有 5 個新/修改文件通過語法檢查
- [x] 優先級 3 完整集成到推薦流程
- [x] 指定單品約束傳遞到 AI 引擎
- [x] 購物連結支持 5 大平台
- [x] Modal UI 響應式設計
- [x] 計數徽章動態更新
- [x] localStorage 狀態持久化

---

## 📌 後續優化建議

1. **購物連結優化**
   - 新增「複製連結」按鈕
   - 支援更多電商平台 (露天拍賣、蝦皮美妝等)
   - 根據商品分類智能選擇平台

2. **指定單品增強**
   - 支援按分類篩選衣櫥
   - 排序選項（最新、最常用等）
   - 預設情境模板 (運動日、約會、上班等)

3. **推薦結果優化**
   - 顯示「衣櫥中有 / 推薦購買」標籤
   - 添加「複製清單」功能（共享推薦給好友）
   - 價格預估（基於搜尋結果）

---

**實現日期**: 2024 年
**優先級**: 3 (後期功能)
**狀態**: ✅ 完成
