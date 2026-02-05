// ========== 風格定義 ==========
const STYLE_DEFINITIONS = {
    "Minimalist": "黑白灰素色、剪裁俐落、冷淡風",
    "Japanese Cityboy": "寬鬆Oversized、多層次、大地色、自然舒適",
    "Korean Chic": "修身剪裁、顯高顯瘦、都會精緻、流行元素",
    "American Vintage": "牛仔、格紋、大學T、古著感",
    "Streetwear": "大Logo、強烈配色、工裝、球鞋文化",
    "Formal": "西裝、襯衫、適合職場",
    "Athleisure": "瑜珈褲、防風材質、機能舒適",
    "French Chic": "條紋、針織、隨性優雅",
    "Y2K": "元氣亮色、短版上衣、低腰褲、科技復古",
    "Old Money": "質感針織、Polo衫、低調奢華",
    "Bohemian": "碎花、流蘇、圖騰、民族風",
    "Grunge": "破損、鉚釘、全黑層次、個性叛逆",
    "Techwear": "全黑、多口袋、扣環織帶、未來感",
    "Coquette": "蝴蝶結、蕾絲、粉嫩、可愛夢幻",
    "Gorpcore": "登山機能、大地撞色、露營感"
};

// ========== 個人設定 UI 邏輯 ==========
const ProfileUI = {
    favoriteStyles: [],
    currentUser: null,

    init() {
        this.cacheDOM();
        this.bindEvents();
        this.loadProfile();
    },

    cacheDOM() {
        this.tabButtons = document.querySelectorAll('.profile-tab-btn');
        this.tabPages = document.querySelectorAll('.tab-page');
        this.genderSelect = document.getElementById('gender');
        this.heightInput = document.getElementById('height');
        this.weightInput = document.getElementById('weight');
        this.thermalRadios = document.querySelectorAll('input[name="thermal"]');
        this.styleSelect = document.getElementById('style-select');
        this.styleDesc = document.getElementById('style-desc');
        this.favoriteStylesList = document.getElementById('favorite-styles-list');
        this.dislikesTextarea = document.getElementById('dislikes');
        this.customDescTextarea = document.getElementById('custom-desc');
        this.historyList = document.getElementById('history-list');
        
        // ✅ 驗證關鍵元素是否存在
        const missingElements = [];
        if (!this.tabButtons || this.tabButtons.length === 0) missingElements.push('profile-tab-btn');
        if (!this.tabPages || this.tabPages.length === 0) missingElements.push('tab-page');
        if (missingElements.length > 0) {
            console.warn('⚠️ 缺少必要的 DOM 元素:', missingElements.join(', '));
        }
    },

    bindEvents() {
        this.tabButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
    },

    switchTab(tabName) {
        // 更新按鈕狀態
        this.tabButtons.forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // 顯示對應的 tab 內容
        this.tabPages.forEach(page => {
            if (page.id === tabName) {
                page.classList.add('active');
                // 如果切換到歷史頁面，則載入歷史
                if (tabName === 'history') {
                    this.loadHistory();
                }
            } else {
                page.classList.remove('active');
            }
        });
    },

    async loadProfile() {
        const user = AppState.getUser();
        if (!user) {
            alert('未登入，請先登入');
            return;
        }

        this.currentUser = user;

        try {
            const result = await API.getProfile(user.id);
            
            if (result.success && result.profile) {
                const profile = result.profile;
                
                // 填充表單
                this.genderSelect.value = profile.gender || '';
                this.heightInput.value = profile.height || '';
                this.weightInput.value = profile.weight || '';
                this.dislikesTextarea.value = profile.dislikes || '';
                this.customDescTextarea.value = profile.custom_style_desc || '';
                
                // 設定體感偏好
                const thermalValue = profile.thermal_preference || 'normal';
                document.querySelector(`input[name="thermal"][value="${thermalValue}"]`).checked = true;
                
                // 載入喜好風格
                this.favoriteStyles = profile.favorite_styles || [];
                this.renderFavoriteStyles();
                
                console.log('✅ 個人資料已載入');
            }
        } catch (error) {
            console.error('載入個人資料失敗:', error);
        }
    },

    showStyleDescription() {
        const selectedStyle = this.styleSelect.value;
        if (selectedStyle && STYLE_DEFINITIONS[selectedStyle]) {
            this.styleDesc.textContent = STYLE_DEFINITIONS[selectedStyle];
        } else {
            this.styleDesc.textContent = '選擇一個風格查看詳細描述';
        }
    },

    addStyle() {
        const selectedStyle = this.styleSelect.value;
        if (!selectedStyle) {
            alert('請先選擇風格');
            return;
        }

        if (this.favoriteStyles.includes(selectedStyle)) {
            alert('此風格已在列表中');
            return;
        }

        this.favoriteStyles.push(selectedStyle);
        this.renderFavoriteStyles();
        this.styleSelect.value = '';
        this.styleDesc.textContent = '選擇一個風格查看詳細描述';
    },

    renderFavoriteStyles() {
        this.favoriteStylesList.innerHTML = '';
        
        if (this.favoriteStyles.length === 0) {
            this.favoriteStylesList.innerHTML = '<div style="color: #999; font-size: 12px;">未選擇任何風格</div>';
            return;
        }

        this.favoriteStyles.forEach(style => {
            const tag = document.createElement('div');
            tag.className = 'style-tag';
            tag.innerHTML = `
                <span>${style}</span>
                <button onclick="ProfileUI.removeStyle('${style}')">×</button>
            `;
            this.favoriteStylesList.appendChild(tag);
        });
    },

    removeStyle(style) {
        this.favoriteStyles = this.favoriteStyles.filter(s => s !== style);
        this.renderFavoriteStyles();
    },

    async savePersonalInfo() {
        const user = AppState.getUser();
        if (!user) return;

        // ✅ 驗證身高和體重
        const height = this.heightInput.value;
        const weight = this.weightInput.value;

        if (height && (isNaN(height) || parseInt(height) < 140 || parseInt(height) > 220)) {
            Toast.error('❌ 身高必須在 140-220 cm 之間');
            return;
        }

        if (weight && (isNaN(weight) || parseInt(weight) < 30 || parseInt(weight) > 150)) {
            Toast.error('❌ 體重必須在 30-150 kg 之間');
            return;
        }

        try {
            const result = await API.updateProfile(
                user.id,
                this.genderSelect.value,
                height,
                weight,
                null,
                null,
                document.querySelector('input[name="thermal"]:checked').value,
                null
            );

            if (result.success) {
                Toast.success('✅ 個人資料已儲存');
            } else {
                Toast.error('❌ 儲存失敗: ' + result.message);
            }
        } catch (error) {
            Toast.error('❌ 儲存失敗: ' + error.message);
        }
    },

    async savePreferences() {
        const user = AppState.getUser();
        if (!user) return;

        // ✅ 驗證避雷清單和自訂描述長度
        const dislikes = this.dislikesTextarea.value;
        const customDesc = this.customDescTextarea.value;

        if (dislikes.length > 500) {
            Toast.error('❌ 避雷清單最多 500 字');
            return;
        }

        if (customDesc.length > 500) {
            Toast.error('❌ 自訂描述最多 500 字');
            return;
        }

        try {
            const result = await API.updateProfile(
                user.id,
                null,
                null,
                null,
                JSON.stringify(this.favoriteStyles),
                dislikes,
                null,
                customDesc
            );

            if (result.success) {
                Toast.success('✅ 偏好設定已儲存');
            } else {
                Toast.error('❌ 儲存失敗: ' + result.message);
            }
        } catch (error) {
            Toast.error('❌ 儲存失敗: ' + error.message);
        }
    },

    async loadHistory() {
        const user = AppState.getUser();
        if (!user) return;

        try {
            const result = await API.getHistory(user.id);

            if (result.success && result.history) {
                if (result.history.length === 0) {
                    this.historyList.innerHTML = `<div class="empty-state"><p>暫無推薦記錄</p></div>`;
                    return;
                }

                this.historyList.innerHTML = '';
                result.history.forEach((item, index) => {
                    // ✅ 驗證日期有效性
                    let dateStr = '未知時間';
                    try {
                        const dateObj = new Date(item.created_at);
                        if (!isNaN(dateObj.getTime())) {
                            dateStr = dateObj.toLocaleString('zh-TW');
                        }
                    } catch (e) {
                        console.warn('日期解析失敗:', item.created_at);
                    }

                    const historyHTML = `
                        <div class="history-item">
                            <div class="history-info">
                                <strong>${index + 1}. ${item.city || '未知城市'} - ${item.occasion || '未知場合'}</strong>
                                <div class="history-detail">風格: ${item.style || '未知'}</div>
                                <div class="history-date">📅 ${dateStr}</div>
                            </div>
                            <button class="history-button" onclick="ProfileUI.deleteHistory(${item.id})">刪除</button>
                        </div>
                    `;
                    this.historyList.innerHTML += historyHTML;
                });
            } else {
                this.historyList.innerHTML = `<div class="empty-state"><p>暫無推薦記錄</p></div>`;
            }
        } catch (error) {
            console.error('載入歷史失敗:', error);
            this.historyList.innerHTML = `<div class="empty-state"><p>載入失敗</p></div>`;
        }
    },

    async deleteHistory(historyId) {
        if (!confirm('確定要刪除此推薦記錄嗎？')) {
            return;
        }

        const user = AppState.getUser();
        if (!user) return;

        try {
            const result = await API.deleteHistory(user.id, historyId);

            if (result.success) {
                alert('✅ 記錄已刪除');
                this.loadHistory();
            } else {
                alert('❌ 刪除失敗: ' + result.message);
            }
        } catch (error) {
            alert('❌ 刪除失敗: ' + error.message);
        }
    }
};

// ========== 初始化 ==========
window.addEventListener('load', () => {
    // 延遲初始化以確保 AppState 已定義
    if (typeof ProfileUI !== 'undefined' && typeof AppState !== 'undefined') {
        ProfileUI.init();
    }
});
