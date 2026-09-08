import cv2
import numpy as np
import os
import ctypes

# --- 啟用 Windows 多螢幕高 DPI 感知 (防止視窗被系統縮放放大) ---
try:
    # 針對 Windows 10/11，設定 Process 為 DPI 感知
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # 2 = PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- 基礎路徑設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 設定要讀取的圖片路徑 ---
# 您可以修改這裡的檔名來讀取不同的截圖
TARGET_IMAGE_NAME = "capture_20260907_105334.png"
IMAGE_PATH = os.path.join(BASE_DIR, "manual_samples", TARGET_IMAGE_NAME)

# --- 全域變數 ---
drawing = False # 是否正在畫圖
ix, iy = -1, -1 # 起始座標
img_display = None # 用於顯示的影像副本
img_original = None # 原始影像

def cv2_imread_unicode(path):
    """
    支援中文路徑的影像讀取函數 (使用 numpy 解碼)
    """
    try:
        # 使用 np.fromfile 讀取位元流，避免路徑編碼問題
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"讀取影像失敗: {e}")
        return None

def draw_rectangle(event, x, y, flags, param):
    """
    滑鼠回呼函數 (Mouse Callback Function)
    處理滑鼠點擊、移動、放開的邏輯
    """
    global ix, iy, drawing, img_display, img_original

    # 按下左鍵：紀錄起始點
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    # 滑鼠移動：若正在畫圖，即時更新矩形框
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            img_display = img_original.copy()
            # 畫出綠色矩形框
            cv2.rectangle(img_display, (ix, iy), (x, y), (0, 255, 0), 1)

    # 放開左鍵：結束畫圖，計算並輸出座標
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        cv2.rectangle(img_display, (ix, iy), (x, y), (0, 255, 0), 1)
        
        # 計算數值 (確保座標不會因滑鼠拖曳方向而變負數)
        width = abs(x - ix)
        height = abs(y - iy)
        start_x = min(ix, x)
        start_y = min(iy, y)
        
        print("-" * 30)
        print(f"選取區域結果 (基於原始像素)：")
        print(f"左上角座標 (X, Y): ({start_x}, {start_y})")
        print(f"矩形尺寸 (W, H): ({width}, {height})")
        print(f"右下角座標: ({start_x + width}, {start_y + height})")
        print(f"NumPy 裁切語法: img[{start_y}:{start_y + height}, {start_x}:{start_x + width}]")
        print("-" * 30)

def main():
    global img_original, img_display

    if not os.path.exists(IMAGE_PATH):
        print(f"錯誤：找不到圖片檔案 -> {IMAGE_PATH}")
        return

    # 讀取影像
    img_original = cv2_imread_unicode(IMAGE_PATH)
    if img_original is None:
        print("無法解析影像內容。")
        return

    # 獲取影像原始尺寸
    orig_h, orig_w = img_original.shape[:2]
    img_display = img_original.copy()

    # 建立視窗
    # WINDOW_NORMAL 允許我們手動設定或調整視窗大小
    window_name = "Coordinate Picker"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # 強制設定視窗顯示的大小為 1000x600 (若您的圖片本身就是 1000x600，這將達成 1:1)
    # 若圖片較大，這會將其縮小顯示；若圖片較小，則放大。但滑鼠回傳的 x,y 依然對應原始像素。
    cv2.resizeWindow(window_name, orig_w, orig_h)
    
    # 綁定滑鼠事件
    cv2.setMouseCallback(window_name, draw_rectangle)

    print("=== 座標選取器 (修正 DPI 版) ===")
    print(f"正在讀取: {TARGET_IMAGE_NAME}")
    print(f"影像原始尺寸: {orig_w}x{orig_h}")
    print("-" * 30)
    print("操作說明:")
    print("1. [滑鼠左鍵拖曳] 選取範圍。")
    print("2. 終端機將顯示精確的像素座標。")
    print("3. [R] 鍵重置影像。")
    print("4. [Q] 鍵結束。")

    while True:
        cv2.imshow(window_name, img_display)
        
        key = cv2.waitKey(1) & 0xFF
        
        # 按下 Q 退出
        if key == ord('q'):
            break
        # 按下 R 重置
        elif key == ord('r'):
            img_display = img_original.copy()
            print("影像已重置。")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()