import os
import hashlib
import sys

# --- 基礎路徑設定 ---
# 獲取目前執行程式碼檔案 (.py) 的絕對路徑目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 設定區域 ---
# 請在下方清單中加入您想要掃描的資料夾名稱 (相對於程式碼位置)
# 依照您之前的需求，預設加入 "1" 與 "2" 資料夾
TARGET_FOLDERS = ["1", "2"]

# 支援的圖片副檔名格式
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}

def calculate_file_hash(file_path):
    """
    計算檔案的 MD5 哈希值 (Hash Value)。
    讀取檔案的二進位內容，確保「內容完全相同」即便「檔名不同」也能被識別。
    """
    # 使用 MD5 演算法，效能與衝突率在處理圖片時非常平衡
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            # 分塊讀取 (Chunking)，避免超大型檔案佔滿記憶體 (RAM)
            buf = f.read(8192)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(8192)
        return hasher.hexdigest()
    except Exception as e:
        print(f"無法讀取檔案 {file_path}: {e}")
        return None

def remove_duplicate_images(folder_path):
    """
    掃描特定資料夾並刪除內容重複的圖片。
    """
    if not os.path.exists(folder_path):
        print(f"跳過：資料夾不存在 -> {folder_path}")
        return

    print(f"\n>>> 正在掃描資料夾: {folder_path}")
    
    # 紀錄已出現過的哈希值 {hash: filename}
    seen_hashes = {}
    duplicates_count = 0
    total_files = 0

    # 取得資料夾內所有檔案名稱
    files = os.listdir(folder_path)
    
    for filename in files:
        file_ext = os.path.splitext(filename)[1].lower()
        
        # 只處理圖片檔案
        if file_ext in IMAGE_EXTENSIONS:
            total_files += 1
            file_path = os.path.join(folder_path, filename)
            
            # 計算該圖片的內容指紋
            file_hash = calculate_file_hash(file_path)
            
            if file_hash:
                if file_hash in seen_hashes:
                    # 如果哈希值已存在，代表這張圖是重複的
                    original_file = seen_hashes[file_hash]
                    print(f"[重複] 發現內容一致圖片: '{filename}' (與 '{original_file}' 相同) -> 執行刪除")
                    
                    try:
                        os.remove(file_path)
                        duplicates_count += 1
                    except Exception as e:
                        print(f"刪除失敗: {filename}, 錯誤: {e}")
                else:
                    # 第一次見到此內容，記錄下來
                    seen_hashes[file_hash] = filename

    print(f"掃描完成！總計掃描 {total_files} 張圖片，刪除 {duplicates_count} 張重複圖片。")

def main():
    print("=== 重複圖片清理工具 (MD5 內容比對版) ===")
    print(f"執行目錄: {BASE_DIR}")
    
    # 遍歷所有設定的目標資料夾
    for folder_name in TARGET_FOLDERS:
        full_path = os.path.join(BASE_DIR, folder_name)
        remove_duplicate_images(full_path)
    
    print("\n所有任務已處理完畢。")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n使用者手動終止。")
        sys.exit()