import numpy as np
import cv2
import time
import pyautogui
import pygetwindow as gw
import win32gui
import win32con
import win32api
from PIL import ImageGrab
import ctypes
import os
from collections import deque

# --- 啟用 Windows 多螢幕高 DPI 感知 (防止座標偏移) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- 基礎路徑與資料夾設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMP_DIR = os.path.join(BASE_DIR, "samp")
SAVE_DIR_1 = os.path.join(BASE_DIR, "1")
SAVE_DIR_2 = os.path.join(BASE_DIR, "2")
DEBUG_DIR = os.path.join(BASE_DIR, "debug")

for folder in [SAVE_DIR_1, SAVE_DIR_2, DEBUG_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- 設定區域 ---
EMULATOR_WINDOW_TITLE = "Poker Fate"
TARGET_WIDTH = 1000
TARGET_HEIGHT = 600

# 模板匹配信心度 (Confidence Threshold)
THRESHOLD = 0.85
# 狀態緩衝幀數 (Buffer Size)
BUFFER_SIZE = 10

# --- 手牌座標設定 (X, Y, W, H) ---
HAND_CARD_1_ROI = (547, 405, 30, 46)
HAND_CARD_2_ROI = (586, 401, 30, 46)

FOLD_BTN_PATH = os.path.join(SAMP_DIR, "棄牌.png")

def cv2_imread_unicode(path):
    """支援中文路徑的讀取函數"""
    try:
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        return img
    except:
        return None

def init_emulator_window():
    """初始化視窗並強制鎖定大小"""
    try:
        windows = gw.getWindowsWithTitle(EMULATOR_WINDOW_TITLE)
        if not windows:
            return None
        hwnd = windows[0]._hWnd
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        # 初始嘗試縮放
        win32gui.MoveWindow(hwnd, left, top, TARGET_WIDTH + 16, TARGET_HEIGHT + 39, True) 
        return hwnd
    except Exception as e:
        print(f"初始化視窗失敗: {e}")
        return None

def get_emulator_screen(hwnd):
    """擷取繪圖區畫面並回傳螢幕絕對座標偏移"""
    try:
        if not win32gui.IsWindow(hwnd):
            return None, 0, 0, 0, 0
        
        c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
        width, height = c_right - c_left, c_bottom - c_top
        
        if width != TARGET_WIDTH or height != TARGET_HEIGHT:
            diff_w = TARGET_WIDTH - width
            diff_h = TARGET_HEIGHT - height
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            win32gui.MoveWindow(hwnd, l, t, (r - l) + diff_w, (b - t) + diff_h, True)
            c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
            width, height = c_right - c_left, c_bottom - c_top

        # 獲取繪圖區左上角的螢幕絕對座標
        screen_left, screen_top = win32gui.ClientToScreen(hwnd, (0, 0))

        screen_pil = ImageGrab.grab(
            bbox=(screen_left, screen_top, screen_left + width, screen_top + height),
            all_screens=True
        )
        img_cv = cv2.cvtColor(np.array(screen_pil), cv2.COLOR_RGB2BGR)
        return img_cv, width, height, screen_left, screen_top
    except Exception as e:
        return None, 0, 0, 0, 0

def find_image_on_screen(screen, template_img):
    """
    在畫面上尋找圖片，並回傳座標與尺寸資訊。
    回傳: (x, y, w, h) 或 None
    """
    if template_img is None or screen is None:
        return None
    
    h, w = template_img.shape[:2]
    res = cv2.matchTemplate(screen, template_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    if max_val >= THRESHOLD:
        return (max_loc[0], max_loc[1], w, h)
    return None

def click_at_center(off_x, off_y, match_res):
    """
    計算匹配目標的中心點並執行點擊。
    off_x, off_y: 視窗繪圖區在螢幕上的絕對起始點
    match_res: (x, y, w, h) 匹配到的相對座標與尺寸
    """
    target_x = off_x + match_res[0] + match_res[2] // 2
    target_y = off_y + match_res[1] + match_res[3] // 2
    
    pyautogui.moveTo(target_x, target_y)
    pyautogui.click()
    print(f">>> 執行自動棄牌點擊: ({target_x}, {target_y})")

def save_hand_images(screen, debug=True):
    """裁切手牌並儲存"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    x1, y1, w1, h1 = HAND_CARD_1_ROI
    x2, y2, w2, h2 = HAND_CARD_2_ROI
    
    card1 = screen[y1 : y1 + h1, x1 : x1 + w1]
    card2 = screen[y2 : y2 + h2, x2 : x2 + w2]
    
    if card1.size == 0 or card2.size == 0:
        return

    cv2.imwrite(os.path.join(SAVE_DIR_1, f"card1_{ts}.png"), card1)
    cv2.imwrite(os.path.join(SAVE_DIR_2, f"card2_{ts}.png"), card2)
    
    if debug:
        debug_screen = screen.copy()
        cv2.rectangle(debug_screen, (x1, y1), (x1+w1, y1+h1), (0, 255, 0), 2)
        cv2.rectangle(debug_screen, (x2, y2), (x2+w2, y2+h2), (0, 0, 255), 2)
        cv2.imwrite(os.path.join(DEBUG_DIR, f"debug_{ts}.png"), debug_screen)

    print(f"[{ts}] 手牌照片已保存。")

def main():
    print(f"=== 手牌採集與自動棄牌腳本 啟動 ===")
    hwnd = init_emulator_window()
    fold_template = cv2_imread_unicode(FOLD_BTN_PATH)
    
    if fold_template is None:
        print(f"錯誤：找不到模板圖片 '棄牌.png'")
        return

    # 狀態緩衝紀錄 (True/False 代表是否有按鈕)
    state_history = deque(maxlen=BUFFER_SIZE)
    
    try:
        while True:
            # Q 鍵退出
            if win32api.GetAsyncKeyState(0x51) & 0x8000:
                break

            # 獲取畫面與螢幕絕對座標偏移
            screen, width, height, offset_x, offset_y = get_emulator_screen(hwnd)
            if screen is None:
                hwnd = init_emulator_window()
                time.sleep(1)
                continue

            # 偵測棄牌按鈕
            match_res = find_image_on_screen(screen, fold_template)
            is_fold_visible = match_res is not None
            
            # 狀態機邏輯：前 10 幀為 False，當前幀為 True
            if len(state_history) == BUFFER_SIZE:
                all_false_in_history = all(s == False for s in state_history)
                
                if all_false_in_history and is_fold_visible:
                    print("偵測到新對局開始 (輪到我行動)...")
                    
                    # 1. 稍微等待發牌動畫完成 (0.5秒)
                    time.sleep(0.5)
                    
                    # 2. 重新獲取最新畫面進行裁切
                    current_screen, _, _, cur_off_x, cur_off_y = get_emulator_screen(hwnd)
                    if current_screen is not None:
                        # 儲存照片
                        save_hand_images(current_screen)
                        
                        # 3. 再次偵測最新畫面中「棄牌」按鈕的位置並點擊中心
                        latest_match = find_image_on_screen(current_screen, fold_template)
                        if latest_match:
                            click_at_center(cur_off_x, cur_off_y, latest_match)
            
            state_history.append(is_fold_visible)
            time.sleep(0.05)

    except Exception as e:
        print(f"程式發生錯誤: {e}")
    finally:
        print("採集工具已關閉。")

if __name__ == "__main__":
    main()