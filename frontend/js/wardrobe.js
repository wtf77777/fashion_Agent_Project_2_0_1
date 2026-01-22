// ========== 衣櫥頁面 UI 邏輯 - 正確順序版本 ==========
const WardrobeUI = {
    items: [],
    selectedItems: new Set(),
    isBatchDeleteMode: false,

    // ========== 初始化 ==========
    init() {
        this.bindEvents();
    },

    // ========== 事件綁定 ==========
    bindEvents() {
        const refreshBtn = document.getElementById('refresh-wardrobe-btn');
        const deleteBtn = document.getElementById('batch-delete-btn');

        if (!refreshBtn || !deleteBtn) {
            console.error('❌ 衣櫥按鈕未找到');
            return;
        }

        refreshBtn.addEventListener('click', () => {
            console.log('🔄 用戶點擊刷新按鈕');
            this.loadWardrobe();
        });

        deleteBtn.addEventListener('click', () => {
            console.log('🗑️ 用戶點擊批量刪除按鈕');
            this.toggleBatchDeleteMode();
        });
    },

    // ========== 輔助函數 - 放在最前面 ==========

    escapeHtml(text) {
        /**防止 XSS 攻擊*/
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**✅ 安全版本的 updateStats - 必須放在 loadWardrobe 之前*/
    updateStatsSafely() {
        const totalItemsEl = document.getElementById('total-items');
        const statsGridEl = document.getElementById('wardrobe-stats');

        // 如果元素不存在（可能在不同頁面 tab），直接返回而不報錯
        if (!totalItemsEl || !statsGridEl) {
            // console.debug('ℹ️ 統計元素當前不可見，跳過更新');
            return;
        }

        try {
            totalItemsEl.textContent = this.items.length;

            const categories = {};
            this.items.forEach(item => {
                const cat = item.category || '其他';
                categories[cat] = (categories[cat] || 0) + 1;
            });

            statsGridEl.innerHTML = `
                <div class="stat-card">
                    <span class="stat-label">總計</span>
                    <span class="stat-value">${this.items.length}</span>
                </div>
                ${Object.entries(categories).map(([cat, count]) => `
                    <div class="stat-card">
                        <span class="stat-label">${this.escapeHtml(cat)}</span>
                        <span class="stat-value">${count}</span>
                    </div>
                `).join('')}
            `;

            console.log('📊 統計資訊已更新');
        } catch (error) {
            console.error('❌ 更新統計資訊失敗:', error);
        }
    },

    // ========== 主要邏輯 - 在輔助函數之後 ==========

    async loadWardrobe() {
        AppState.setLoading(true);

        try {
            console.log('📥 開始載入衣櫥...');

            const result = await API.getWardrobe();
            console.log('📊 API 返回結果:', result);

            if (result.success) {
                this.items = result.items || [];
                console.log(`✅ 成功載入 ${this.items.length} 件衣服`);

                const wardrobeGrid = document.getElementById('wardrobe-grid');
                if (!wardrobeGrid) {
                    console.error('❌ wardrobe-grid 元素不存在');
                    Toast.error('頁面載入失敗，請重新整理');
                    return;
                }

                this.renderWardrobe();

                // ✅ 現在 updateStatsSafely 已經定義了
                this.updateStatsSafely();

                Toast.success(`✅ 已載入 ${this.items.length} 件衣服`);
            } else {
                console.error('❌ API 返回失敗:', result.message);
                Toast.error(result.message || '載入衣櫥失敗');
            }
        } catch (error) {
            console.error('💥 載入衣櫥發生錯誤:', error);
            Toast.error('載入失敗: ' + error.message);

            const wardrobeGrid = document.getElementById('wardrobe-grid');
            const emptyState = document.getElementById('wardrobe-empty');
            if (wardrobeGrid && emptyState) {
                wardrobeGrid.style.display = 'none';
                emptyState.style.display = 'block';
                emptyState.innerHTML = `
                    <p>⚠️ 載入失敗: ${error.message}</p>
                    <p>請檢查網路連線或重新整理頁面</p>
                `;
            }
        } finally {
            AppState.setLoading(false);
        }
    },

    renderWardrobe() {
        const grid = document.getElementById('wardrobe-grid');
        const emptyState = document.getElementById('wardrobe-empty');

        if (!grid || !emptyState) {
            console.error('❌ 衣櫥渲染元素不存在');
            return;
        }

        if (this.items.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'block';
            console.log('📭 衣櫥為空');
            return;
        }

        grid.style.display = 'grid';
        emptyState.style.display = 'none';
        grid.innerHTML = '';

        console.log(`🎨 正在渲染 ${this.items.length} 件衣物...`);

        this.items.forEach((item, index) => {
            try {
                const card = this.createItemCard(item);
                grid.appendChild(card);
            } catch (error) {
                console.error(`❌ 渲染第 ${index + 1} 件衣物失敗:`, error);
            }
        });

        console.log('✅ 衣物渲染完成');
    },

    createItemCard(item) {
        if (!item.id || !item.name) {
            console.warn('⚠️ 衣物缺少必要欄位:', item);
            return document.createElement('div');
        }

        const card = document.createElement('div');
        card.className = 'wardrobe-item';
        card.dataset.itemId = item.id;

        let checkboxHTML = '';
        if (this.isBatchDeleteMode) {
            const isSelected = this.selectedItems.has(item.id);
            checkboxHTML = `
                <div class="item-checkbox">
                    <input type="checkbox" 
                           id="check-${item.id}" 
                           ${isSelected ? 'checked' : ''}
                           onchange="WardrobeUI.toggleItemSelection(${item.id})">
                    <label for="check-${item.id}">選擇</label>
                </div>
            `;
        }

        const imageSrc = item.image_data ?
            `data:image/jpeg;base64,${item.image_data}` :
            'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22%3E%3Crect fill=%22%23ddd%22 width=%22100%22 height=%22100%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22%23999%22%3E無圖片%3C/text%3E%3C/svg%3E';

        const category = item.category || '其他';
        const color = item.color || '未知';
        const style = item.style || 'N/A';
        const warmth = Math.max(1, Math.min(10, item.warmth || 5));

        card.innerHTML = `
            ${checkboxHTML}
            <div class="item-image">
                <img src="${imageSrc}" 
                     alt="${item.name}"
                     loading="lazy"
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22%3E%3Crect fill=%22%23ddd%22 width=%22100%22 height=%22100%22/%3E%3C/svg%3E'">
            </div>
            <div class="item-info">
                <h3 class="item-name">${this.escapeHtml(item.name)}</h3>
                <div class="item-details">
                    <p><strong>類別:</strong> ${this.escapeHtml(category)}</p>
                    <p><strong>顏色:</strong> ${this.escapeHtml(color)}</p>
                    <p><strong>風格:</strong> ${this.escapeHtml(style)}</p>
                    <p><strong>保暖度:</strong> ${'🔥'.repeat(warmth)}</p>
                </div>
                ${!this.isBatchDeleteMode ? `
                    <button class="btn btn-secondary btn-delete" 
                            onclick="WardrobeUI.deleteItem(${item.id})"
                            data-item-id="${item.id}">
                        🗑️ 刪除
                    </button>
                ` : ''}
            </div>
        `;

        return card;
    },

    toggleBatchDeleteMode() {
        this.isBatchDeleteMode = !this.isBatchDeleteMode;

        const btn = document.getElementById('batch-delete-btn');
        if (!btn) {
            console.error('❌ batch-delete-btn 不存在');
            return;
        }

        if (this.isBatchDeleteMode) {
            btn.textContent = '✅ 完成選擇';
            btn.classList.add('btn-primary');
            btn.classList.remove('btn-secondary');
            this.selectedItems.clear();
            console.log('📝 進入批量刪除模式');
        } else {
            btn.textContent = '🗑️ 批量刪除';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');

            if (this.selectedItems.size > 0) {
                console.log(`🗑️ 要刪除 ${this.selectedItems.size} 件衣物`);
                this.executeBatchDelete();
            } else {
                console.log('ℹ️ 未選擇任何衣物');
            }
        }

        this.renderWardrobe();
    },

    toggleItemSelection(itemId) {
        if (this.selectedItems.has(itemId)) {
            this.selectedItems.delete(itemId);
        } else {
            this.selectedItems.add(itemId);
        }

        const btn = document.getElementById('batch-delete-btn');
        if (!btn) return;

        if (this.selectedItems.size > 0) {
            btn.textContent = `🗑️ 刪除選中的 ${this.selectedItems.size} 件`;
        } else {
            btn.textContent = '✅ 完成選擇';
        }
    },

    async deleteItem(itemId) {
        if (!confirm('確定要刪除這件衣服嗎？')) {
            return;
        }

        AppState.setLoading(true);

        try {
            const result = await API.deleteItem(itemId);

            if (result.success) {
                Toast.success('✅ 已刪除');
                this.items = this.items.filter(item => item.id !== itemId);
                this.renderWardrobe();
                this.updateStatsSafely();
            } else {
                Toast.error('刪除失敗');
            }
        } catch (error) {
            console.error('刪除錯誤:', error);
            Toast.error('刪除失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    },

    async executeBatchDelete() {
        if (this.selectedItems.size === 0) {
            return;
        }

        if (!confirm(`確定要刪除選中的 ${this.selectedItems.size} 件衣服嗎？`)) {
            this.selectedItems.clear();
            this.isBatchDeleteMode = false;
            this.renderWardrobe();
            return;
        }

        AppState.setLoading(true);

        try {
            const itemIds = Array.from(this.selectedItems);
            const result = await API.batchDeleteItems(itemIds);

            if (result.success) {
                Toast.success(`✅ 已刪除 ${result.success_count} 件衣服`);

                if (result.fail_count > 0) {
                    Toast.warning(`⚠️ ${result.fail_count} 件刪除失敗`);
                }

                await this.loadWardrobe();
                this.selectedItems.clear();
            } else {
                Toast.error('批量刪除失敗');
            }
        } catch (error) {
            console.error('批量刪除錯誤:', error);
            Toast.error('批量刪除失敗: ' + error.message);
        } finally {
            AppState.setLoading(false);
        }
    }
};
