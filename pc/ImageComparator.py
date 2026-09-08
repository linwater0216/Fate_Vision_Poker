import cv2
import numpy as np
import os

# --- 基礎路徑設定 (以程式碼所在位置為基準) ---
# 獲取目前執行程式碼檔案 (.py) 的絕對路徑目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 子目錄路徑設定 ---
SAMP_DIR = os.path.join(BASE_DIR, "samp")             # 存放模板圖片的資料夾
MANUAL_SAMPLES_DIR = os.path.join(BASE_DIR, "manual_samples") # 存放截圖大圖的資料夾

# --- 設定目標圖片 (背景圖 D) ---
# TARGET_IMAGE_D 指向 manual_samples 資料夾內的特定圖片
TARGET_IMAGE_D = os.path.join(MANUAL_SAMPLES_DIR, "capture_20260906_011530.png")

# --- 設定模板圖片 (A, B, C, D) ---
TEMPLATES = {
    "大盲 (A)": os.path.join(SAMP_DIR, "大盲.png"),
    "小盲 (B)": os.path.join(SAMP_DIR, "小盲.png"),
    "莊家 (C)": os.path.join(SAMP_DIR, "D.png"),
    "ALL (D)": os.path.join(SAMP_DIR, "ALL_IN.png")
}

# 模板匹配閾值 (Confidence Threshold)
THRESHOLD = 0.8 

def cv2_imread_unicode(path):
    """
    解決 OpenCV 無法讀取中文字元路徑的問題。
    使用 numpy 先將圖檔讀入，再進行解碼。
    """
    try:
        # np.fromfile 可以正確處理 Unicode 路徑
        # 以 uint8 (無符號 8 位元整數) 讀取檔案
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"讀取檔案時發生異常: {path}, 錯誤: {e}")
        return None

def compare_images():
    """
    執行模板匹配任務，比對多張小圖在大圖中的位置與信心度。
    修正版：支援中文檔案路徑。
    """
    # 1. 檢查並讀取目標大圖
    if not os.path.exists(TARGET_IMAGE_D):
        print(f"錯誤：找不到目標圖片 D (背景圖) -> {TARGET_IMAGE_D}")
        return

    # 改用支援中文路徑的讀取方式
    img_rgb = cv2_imread_unicode(TARGET_IMAGE_D)
    
    if img_rgb is None:
        print(f"錯誤：無法解析背景圖檔案，請確認檔案路徑或損壞情況 -> {TARGET_IMAGE_D}")
        return
    
    print(f"開始比對任務...")
    print(f"目標圖片來源: {TARGET_IMAGE_D}")
    print(f"目標圖片尺寸: {img_rgb.shape[1]} (寬) x {img_rgb.shape[0]} (高)")
    print("-" * 60)

    # 2. 遍歷所有模板進行比對
    for name, path in TEMPLATES.items():
        if not os.path.exists(path):
            print(f"跳過 [{name}]: 找不到模板檔案 -> {path}")
            continue

        # 改用支援中文路徑的讀取方式讀取模板 (Template)
        template = cv2_imread_unicode(path)
        
        if template is None:
            print(f"警告：無法讀取/解析模板檔案 (可能是中文編碼問題或檔案毀損) -> {path}")
            continue
            
        h, w = template.shape[:2] # 取得模板的原始長寬

        # 執行模板匹配 (使用歸一化相關係數方法 TM_CCOEFF_NORMED)
        # 結果 res 是一個二維矩陣，每個點代表該位置的匹配程度 (0.0 ~ 1.0)
        res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
        
        # 使用 minMaxLoc 找出矩陣中數值最高（最匹配）的位置
        # max_val 代表最高信任度 (Confidence Score)
        # max_loc 代表最高信任度的座標 (x, y)，即模板左上角在背景圖的位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        # 3. 判斷是否超過預設閾值
        if max_val >= THRESHOLD:
            print(f"【匹配成功】目標: {name}")
            print(f"  - 檔案名稱: {os.path.basename(path)}")
            print(f"  - 最佳座標 (左上角): X={max_loc[0]}, Y={max_loc[1]}")
            print(f"  - 最佳座標 (中心點): X={int(max_loc[0] + w/2)}, Y={int(max_loc[1] + h/2)}")
            print(f"  - 模板尺寸: {w} (寬) x {h} (高)")
            print(f"  - 信任度 (Confidence): {max_val:.4f}")
        else:
            print(f"【匹配失敗】目標: {name}")
            print(f"  - 未達閾值 {THRESHOLD} (當前最高信任度: {max_val:.4f})")
            
        print("-" * 40)

if __name__ == "__main__":
    # 執行環境檢查提示
    # 本程式於 Lenovo LOQ Essential 15IRX11 (RTX5060, Windows 11) 環境開發
    compare_images()