@app.post("/api/upload")
async def upload_images(request: Request):
    """上傳衣物"""
    try:
        form = await request.form()
        user_id = form.get("user_id")
        files = form.getlist("files")
        
        print(f"[INFO] 收到上傳請求: user_id={user_id}, 檔案數={len(files)}")
        
        if not user_id or not files:
            print("[ERROR] 缺少必要參數")
            return {"success": False, "message": "缺少必要參數"}
        
        # 讀取圖片
        img_bytes_list = []
        file_names = []
        
        for file in files:
            content = await file.read()
            img_bytes_list.append(content)
            file_names.append(file.filename)
            print(f"[INFO] 讀取檔案: {file.filename}, 大小: {len(content)} bytes")
        
        # AI 辨識
        print(f"[INFO] 開始 AI 辨識 {len(img_bytes_list)} 張圖片...")
        tags_list = ai_service.batch_auto_tag(img_bytes_list)
        
        if not tags_list:
            print("[ERROR] AI 辨識失敗，tags_list 為 None")
            return {"success": False, "message": "AI 辨識失敗"}
        
        print(f"[INFO] AI 辨識成功，回傳 {len(tags_list)} 個標籤")
        print(f"[DEBUG] 標籤內容: {tags_list}")
        
        # 儲存
        success_count = 0
        duplicate_count = 0
        fail_count = 0
        saved_items = []
        
        for img_bytes, tags, filename in zip(img_bytes_list, tags_list, file_names):
            try:
                # 檢查重複
                img_hash = wardrobe_service.get_image_hash(img_bytes)
                is_duplicate, existing_name = wardrobe_service.check_duplicate_image(user_id, img_hash)
                
                if is_duplicate:
                    print(f"[WARN] 重複圖片: {filename} (已存在: {existing_name})")
                    duplicate_count += 1
                    continue
                
                item = ClothingItem(
                    user_id=user_id,
                    name=tags.get('name', filename),
                    category=tags.get('category', '其他'),
                    color=tags.get('color', '未知'),
                    style=tags.get('style', ''),
                    warmth=int(tags.get('warmth', 5))
                )
                
                success, msg = wardrobe_service.save_item(item, img_bytes)
                
                if success:
                    print(f"[INFO] 儲存成功: {item.name}")
                    success_count += 1
                    saved_items.append(tags)
                else:
                    print(f"[ERROR] 儲存失敗: {msg}")
                    fail_count += 1
                    
            except Exception as e:
                print(f"[ERROR] 處理圖片失敗 {filename}: {str(e)}")
                fail_count += 1
        
        print(f"[INFO] 上傳完成: 成功={success_count}, 重複={duplicate_count}, 失敗={fail_count}")
        
        return {
            "success": True,
            "success_count": success_count,
            "duplicate_count": duplicate_count,
            "fail_count": fail_count,
            "items": saved_items
        }
        
    except Exception as e:
        print(f"[ERROR] 上傳異常: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"上傳失敗: {str(e)}"}
