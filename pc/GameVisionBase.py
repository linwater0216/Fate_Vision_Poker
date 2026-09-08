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
import sys

# --- 啟用 Windows 多螢幕高 DPI 感知 ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) 
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- 基礎路徑設定 (確保路徑以程式碼檔案所在目錄為基準) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 設定區域 ---
EMULATOR_WINDOW_TITLE = "Poker Fate"  
# 截圖存檔路徑 (程式碼目錄下的 manual_samples)
SAVE_PATH = os.path.join(BASE_DIR, "manual_samples") 

TARGET_WIDTH = 1018            
TARGET_HEIGHT = 647               
LOOP_DELAY = 0.1                 

# 確保儲存路徑存在
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

def find_image_on_screen(screen, template_path, threshold=0.91):
    """
    底層工具：在影像中搜尋特定模板。
    """
    if not os.path.exists(template_path):
        return None
    try:
        with open(template_path, 'rb') as f:
            template_data = f.read()
            template = cv2.imdecode(np.frombuffer(template_data, np.uint8), cv2.IMREAD_COLOR)
    except:
        return None

    if template is None:
        return None
    
    w, h = template.shape[1], template.shape[0]
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        return (max_loc[0], max_loc[1], w, h, max_val)
    return None

def init_emulator_window():
    """
    初始化並強制鎖定目標視窗尺寸與位置。
    """
    try:
        windows = gw.getWindowsWithTitle(EMULATOR_WINDOW_TITLE)
        if not windows:
            return None
        hwnd = windows[0]._hWnd
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except:
            pass
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, 
                              win32con.SWP_NOSIZE | win32con.SWP_NOMOVE)
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        # 強制鎖定尺寸
        win32gui.MoveWindow(hwnd, left, top, TARGET_WIDTH, TARGET_HEIGHT, True)
        return hwnd
    except Exception as e:
        print(f"初始化視窗失敗: {e}")
        return None

def get_emulator_screen(hwnd):
    """
    擷取內容區域畫面並回傳座標資訊 (完全比照 260825steam.py 邏輯)。
    """
    try:
        if not win32gui.IsWindow(hwnd):
            return None, 0, 0, 0, 0
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
        width, height = c_right - c_left, c_bottom - c_top
        
        # 尺寸校正
        if (right - left) != TARGET_WIDTH or (bottom - top) != TARGET_HEIGHT:
             win32gui.MoveWindow(hwnd, left, top, TARGET_WIDTH, TARGET_HEIGHT, True)
             left, top, right, bottom = win32gui.GetWindowRect(hwnd)
             c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
             width, height = c_right - c_left, c_bottom - c_top

        # 取得絕對座標
        screen_left, screen_top = win32gui.ClientToScreen(hwnd, (0, 0))
        # 擷取
        screen_pil = ImageGrab.grab(
            bbox=(screen_left, screen_top, screen_left + width, screen_top + height),
            all_screens=True
        )
        img_cv = cv2.cvtColor(np.array(screen_pil), cv2.COLOR_RGB2BGR)
        return img_cv, screen_left, screen_top, width, height
    except Exception as e:
        print(f"獲取畫面失敗: {e}")
        return None, 0, 0, 0, 0

def main():
    print(f"=== 視覺擷取基礎工具已啟動 ===")
    print(f"目標視窗: {EMULATOR_WINDOW_TITLE}")
    print(f"存檔路徑: {SAVE_PATH}")
    print("-" * 35)
    print("[Q] 退出程式")
    print("[S] 擷取當前視窗畫面")

    hwnd = init_emulator_window()
    if not hwnd:
        print(f"錯誤：找不到視窗 '{EMULATOR_WINDOW_TITLE}'")
        return

    try:
        while True:
            # 取得畫面資料 (不顯示，僅用於熱鍵觸發後的儲存)
            screen, offset_x, offset_y, width, height = get_emulator_screen(hwnd)
            
            if screen is None:
                hwnd = init_emulator_window()
                time.sleep(1)
                continue

            # --- 全域熱鍵偵測 (無顯示視窗模式) ---
            
            # Q 鍵退出 (0x51)
            if win32api.GetAsyncKeyState(0x51) & 0x8000:
                print("程序終止。")
                break 
                
            # S 鍵截圖 (0x53)
            if win32api.GetAsyncKeyState(0x53) & 0x8000:
                ts = time.strftime("%Y%m%d_%H%M%S")
                save_file = os.path.join(SAVE_PATH, f"capture_{ts}.png")
                cv2.imwrite(save_file, screen)
                print(f"已儲存手動截圖: {save_file}")
                time.sleep(0.3) # 防止重複觸發

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        pass
    print("視覺工具已關閉。")

if __name__ == "__main__":
    main()