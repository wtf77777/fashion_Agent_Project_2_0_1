// ========== API 配置 ==========
const API_BASE_URL = window.location.origin;

// ========== API 請求封裝 ==========
const API = {
    // ========== 認證 API ==========
    async login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch(`${API_BASE_URL}/api/login`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    },
    
    async register(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch(`${API_BASE_URL}/api/register`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    },
    
    // ========== 天氣 API ==========
    async getWeather(city) {
        const response = await fetch(
            `${API_BASE_URL}/api/weather?city=${encodeURIComponent(city)}`
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    },
    
    // ========== 上傳 API ==========
    async uploadImages(files) {
        const formData = new FormData();
        
        files.forEach(file => {
            formData.append('files', file);
        });
        
        const user = AppState.getUser();
        // ✅ 改這裡：傳送 UUID 而不是 BIGINT
        formData.append('user_id', user.id);
        
        console.log(`[INFO] 上傳: user_id=${user.id}`);
        
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`上傳失敗: ${response.statusText}`);
        }
        
        return response.json();
    },
    
    // ========== 衣櫥 API ==========
    async getWardrobe() {
        const user = AppState.getUser();
        
        // ✅ 改這裡：驗證 user_id 存在
        if (!user || !user.id) {
            throw new Error('未登入或 user_id 無效');
        }
        
        console.log(`[INFO] 查詢衣櫥: user_id=${user.id}`);
        
        const response = await fetch(
            `${API_BASE_URL}/api/wardrobe?user_id=${encodeURIComponent(user.id)}`  // ✅ encodeURIComponent
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    },
    
    async deleteItem(itemId) {
        const user = AppState.getUser();
        const formData = new FormData();
        formData.append('user_id', user.id);
        formData.append('item_id', itemId);
        
        const response = await fetch(`${API_BASE_URL}/api/wardrobe/delete`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    },
    
    async batchDeleteItems(itemIds) {
        const user = AppState.getUser();
        const formData = new FormData();
        formData.append('user_id', user.id);
        
        // ✅ 改這裡：正確的陣列格式
        itemIds.forEach(id => {
            formData.append('item_ids', id);
        });
        
        const response = await fetch(`${API_BASE_URL}/api/wardrobe/batch-delete`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    },
    
    // ========== 推薦 API ==========
    async getRecommendation(city, style, occasion) {
        const user = AppState.getUser();
        
        // ✅ 改這裡：驗證 user_id
        if (!user || !user.id) {
            throw new Error('未登入');
        }
        
        const formData = new FormData();
        formData.append('user_id', user.id);
        formData.append('city', city);
        formData.append('style', style || '不限定風格');
        formData.append('occasion', occasion || '外出遊玩');
        
        const response = await fetch(`${API_BASE_URL}/api/recommendation`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    }
};

// ========== 圖片處理工具 ==========
const ImageUtils = {
    // 壓縮圖片
    async compressImage(file, maxWidth = 1200, maxHeight = 1200, quality = 0.8) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                const img = new Image();
                
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    let width = img.width;
                    let height = img.height;
                    
                    // 計算縮放比例
                    if (width > height) {
                        if (width > maxWidth) {
                            height = height * (maxWidth / width);
                            width = maxWidth;
                        }
                    } else {
                        if (height > maxHeight) {
                            width = width * (maxHeight / height);
                            height = maxHeight;
                        }
                    }
                    
                    canvas.width = width;
                    canvas.height = height;
                    
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);
                    
                    canvas.toBlob((blob) => {
                        resolve(new File([blob], file.name, {
                            type: 'image/jpeg',
                            lastModified: Date.now()
                        }));
                    }, 'image/jpeg', quality);
                };
                
                img.onerror = reject;
                img.src = e.target.result;
            };
            
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },
    
    // 生成預覽 URL
    createPreviewURL(file) {
        return URL.createObjectURL(file);
    },
    
    // 清理預覽 URL
    revokePreviewURL(url) {
        URL.revokeObjectURL(url);
    },
    
    // 驗證圖片文件
    validateImageFile(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (!validTypes.includes(file.type)) {
            throw new Error(`不支援的檔案類型: ${file.type}`);
        }
        
        if (file.size > maxSize) {
            throw new Error(`檔案過大: ${(file.size / 1024 / 1024).toFixed(2)}MB (最大 10MB)`);
        }
        
        return true;
    }
};

// ========== 本地儲存工具 ==========
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('儲存失敗:', error);
        }
    },
    
    get(key) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : null;
        } catch (error) {
            console.error('讀取失敗:', error);
            return null;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('刪除失敗:', error);
        }
    },
    
    clear() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('清空失敗:', error);
        }
    }
};

// ========== 防抖和節流工具 ==========
const Utils = {
    // 防抖
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // 節流
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    // 格式化日期
    formatDate(date) {
        return new Date(date).toLocaleDateString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    },
    
    // 格式化檔案大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
};
