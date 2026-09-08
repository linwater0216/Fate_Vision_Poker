import cv2
import numpy as np
import os

# --- 基礎路徑設定 (以程式碼所在位置為基準) ---
# 獲取目前執行程式碼檔案 (.py) 的絕對路徑目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 子目錄路徑設定 ---
SAMP_DIR = os.path.join(BASE_DIR, "samp")             # 存放小圖 A 的資料夾
MANUAL_SAMPLES_DIR = os.path.join(BASE_DIR, "manual_samples") # 存放背景大圖 B 的資料夾

# --- 設定比對目標 ---
# 小圖 A (Template)
IMAGE_A_PATH = os.path.join(SAMP_DIR, "1.png") 
# 背景大圖 B (Target)
IMAGE_B_PATH = os.path.join(MANUAL_SAMPLES_DIR, "capture_20260906_011510.png")

# 模板匹配閾值 (Confidence Threshold)
THRESHOLD = 0.8 

def cv2_imread_unicode(path):
    """
    解決 OpenCV 無法讀取中文字元路徑的問題。
    使用 numpy 先將圖檔讀入，再進行解碼。
    """
    try:
        # np.fromfile 處理 Unicode 路徑，以 uint8 讀取檔案
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"讀取檔案時發生異常: {path}, 錯誤: {e}")
        return None

def find_a_in_b():
    """
    執行單一圖片比對任務，尋找圖片 A 在圖片 B 中的位置。
    """
    # 1. 檢查檔案是否存在
    if not os.path.exists(IMAGE_A_PATH):
        print(f"錯誤：找不到小圖 A -> {IMAGE_A_PATH}")
        return
    if not os.path.exists(IMAGE_B_PATH):
        print(f"錯誤：找不到背景大圖 B -> {IMAGE_B_PATH}")
        return

    # 2. 讀取影像
    img_template = cv2_imread_unicode(IMAGE_A_PATH) # 小圖 A
    img_target = cv2_imread_unicode(IMAGE_B_PATH)   # 大圖 B
    
    if img_template is None or img_target is None:
        print("錯誤：影像讀取失敗，請檢查檔案格式或編碼。")
        return

    # 取得小圖 A 的尺寸
    h, w = img_template.shape[:2]

    print(f"開始比對任務...")
    print(f"小圖 A: {os.path.basename(IMAGE_A_PATH)} ({w}x{h})")
    print(f"大圖 B: {os.path.basename(IMAGE_B_PATH)} ({img_target.shape[1]}x{img_target.shape[0]})")
    print("-" * 50)

    # 3. 執行模板匹配 (Template Matching)
    # 使用 TM_CCOEFF_NORMED 歸一化相關係數匹配
    res = cv2.matchTemplate(img_target, img_template, cv2.TM_CCOEFF_NORMED)
    
    # 尋找矩陣中最大值與其位置
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    # 4. 輸出結果
    if max_val >= THRESHOLD:
        print(f"【匹配成功】")
        print(f"  - 左上角座標: X={max_loc[0]}, Y={max_loc[1]}")
        print(f"  - 中心點座標: X={int(max_loc[0] + w/2)}, Y={int(max_loc[1] + h/2)}")
        print(f"  - 信任度 (Confidence): {max_val:.4f}")
    else:
        print(f"【匹配失敗】")
        print(f"  - 未達閾值 {THRESHOLD} (當前最高信任度: {max_val:.4f})")

if __name__ == "__main__":
    # 執行比對
    find_a_in_b()