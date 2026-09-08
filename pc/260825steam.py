import numpy as np
import cv2
import time
import pyautogui
import pygetwindow as gw
import win32gui
import win32con
import win32api  # 用於全域偵測鍵盤事件 (Global Key State Detection)
from PIL import ImageGrab  # 用於跨螢幕、多螢幕及負座標之精準擷圖 (Multi-Monitor Capture)
import ctypes    # 用於宣告高 DPI 感知，避免跨螢幕縮放率不同導致座標偏移 (DPI Awareness)
import os
import sys       # 用於結束程式

# --- 啟用 Windows 多螢幕高 DPI 感知 (Enable Per-Monitor DPI Awareness) ---
# 確保視窗跨越不同縮放倍率時，座標與擷圖不發生偏移
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 2 代表 PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- 設定區域 (Configuration Area) ---
EMULATOR_WINDOW_TITLE = "Poker Fate"  

TEMPLATE_IMAGE_PATH = "./pc/samp"    # 模板圖片路徑 (包含 a, b, c, c_0, d_0, d_1, e .png)
SAVE_PATH = "./samp1"            # 按下 's' 儲存截圖的路徑
THRESHOLD = 0.91                 # 模板匹配閾值

# 固定視窗尺寸 (根據您提供的 260825steam.py 設定)
TARGET_WIDTH = 1018            
TARGET_HEIGHT = 647               

TEMPLATE_EXT = ".png"
MAX_FAILED_ATTEMPTS = 200         # 偵錯自癒上限
LOOP_DELAY = 0.1                 # 迴圈間隔

# --- 計數器設定 ---
TARGET_E_COUNT = 9               # 設定偵測到圖片 e 的目標次數，達到後結束程式

# 確保儲存路徑存在
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

def find_image_on_screen(screen, template_name):
    """
    在目標畫面上尋找模板圖片位置（彩色匹配）。
    
    :param screen: 擷取到的影像陣列。
    :param template_name: 模板檔案名稱。
    :return: (x, y, w, h, max_val) 或 None。
    """
    template_path = os.path.join(TEMPLATE_IMAGE_PATH, template_name)
    if not os.path.exists(template_path):
        return None

    try:
        with open(template_path, 'rb') as f:
            template_data = f.read()
            template = cv2.imdecode(np.frombuffer(template_data, np.uint8), cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"錯誤：無法載入模板 '{template_path}': {e}")
        return None

    if template is None:
        return None
    
    w, h = template.shape[1], template.shape[0]
    # 執行模板匹配
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= THRESHOLD:
        return (max_loc[0], max_loc[1], w, h, max_val)
    return None

def click_at_position(x, y, t=1):
    """
    在螢幕絕對座標 (x, y) 進行點擊。
    """
    pyautogui.moveTo(x, y)
    pyautogui.click(x, y, clicks=t)
    time.sleep(0.1)

def swipe_to_y(start_x, start_y, target_y, duration=0.5):
    """
    從起始位置滑動到指定的螢幕絕對 Y 座標。
    """
    pyautogui.moveTo(start_x, start_y)
    pyautogui.dragTo(start_x, target_y, duration=duration, button='left')
    time.sleep(0.1)

def init_emulator_window():
    """
    初始化並調整目標視窗大小。
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
        # 強制鎖定視窗尺寸
        win32gui.MoveWindow(hwnd, left, top, TARGET_WIDTH, TARGET_HEIGHT, True)
        return hwnd
    except Exception as e:
        print(f"初始化視窗失敗: {e}")
        return None

def get_emulator_screen(hwnd):
    """
    擷取內容區域畫面並回傳座標資訊。
    """
    try:
        if not win32gui.IsWindow(hwnd):
            return None, 0, 0, 0, 0
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
        width, height = c_right - c_left, c_bottom - c_top
        
        # 尺寸校正鎖定
        if (right - left) != TARGET_WIDTH or (bottom - top) != TARGET_HEIGHT:
             win32gui.MoveWindow(hwnd, left, top, TARGET_WIDTH, TARGET_HEIGHT, True)
             left, top, right, bottom = win32gui.GetWindowRect(hwnd)
             c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
             width, height = c_right - c_left, c_bottom - c_top

        # 取得內容區域左上角的絕對座標
        screen_left, screen_top = win32gui.ClientToScreen(hwnd, (0, 0))
        # 擷取畫面
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
    hwnd = init_emulator_window()
    if not hwnd:
        print(f"找不到視窗 '{EMULATOR_WINDOW_TITLE}'")
        return

    # 初始狀態與計數器
    current_state = 'a'
    failed_attempts_counter = 0
    e_counter = 0

    print(f"Poker Fate 腳本啟動。目標 e 次數: {TARGET_E_COUNT}")
    print("[Q] 退出程式, [S] 手動截圖")

    try:
        while True:
            screen, offset_x, offset_y, width, height = get_emulator_screen(hwnd)
            
            if screen is None:
                print("等待視窗重新連線...")
                hwnd = init_emulator_window()
                time.sleep(1)
                continue

            # --- 全域熱鍵偵測 ---
            if win32api.GetAsyncKeyState(0x51) & 0x8000: # Q 鍵退出
                print("接收到退出指令。")
                break 
            if win32api.GetAsyncKeyState(0x53) & 0x8000: # S 鍵截圖
                ts = time.strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(os.path.join(SAVE_PATH, f"cap_{ts}.png"), screen)
                print(f"已儲存手動截圖")
                time.sleep(0.1)

            # --- 偵錯自癒邏輯 ---
            if failed_attempts_counter >= MAX_FAILED_ATTEMPTS:
                print(f"[自癒] 連續失敗，啟動全掃描...")
                potential_states = ['a', 'b', 'c', 'd_0', 'd_1', 'e']
                for ps in potential_states:
                    if find_image_on_screen(screen, f"{ps}{TEMPLATE_EXT}"):
                        current_state = 'd' if ps == 'd_0' else ps
                        print(f"[自癒] 成功，切換至狀態: {current_state}")
                        failed_attempts_counter = 0
                        break
                if failed_attempts_counter != 0:
                    failed_attempts_counter = 0 # 重置避免卡死

            matched_this_loop = False

            # --- 狀態機邏輯 ---
            
            # 狀態 a: 尋找 a.png
            if current_state == 'a':
                res = find_image_on_screen(screen, f"a{TEMPLATE_EXT}")
                if res:
                    click_at_position(offset_x + res[0] + res[2]/2, offset_y + res[1] + res[3]/2)
                    current_state = 'b'
                    print(">>> 狀態切換: b")
                    matched_this_loop = True

            # 狀態 b: 尋找 b.png
            elif current_state == 'b':
                res = find_image_on_screen(screen, f"b{TEMPLATE_EXT}")
                if res:
                    click_at_position(offset_x + res[0] + res[2]/2, offset_y + res[1] + res[3]/2)
                    current_state = 'c'
                    print(">>> 狀態切換: c")
                    matched_this_loop = True

            # 狀態 c: 尋找 c_0.png 且 c.png
            elif current_state == 'c':
                res_c0 = find_image_on_screen(screen, f"c_0{TEMPLATE_EXT}")
                res_c = find_image_on_screen(screen, f"c{TEMPLATE_EXT}")
                if res_c0 and res_c:
                    click_at_position(offset_x + res_c[0] + res_c[2]/2, offset_y + res_c[1] + res_c[3]/2)
                    print(">>> 狀態 c 觸發，等待 5 秒...")
                    time.sleep(5)
                    current_state = 'd'
                    print(">>> 狀態切換: d")
                    matched_this_loop = True

            # 狀態 d: 優先偵測圖片 e，再執行 d_0 邏輯
            elif current_state == 'd':
                # 1. 額外偵測圖片 e
                res_e = find_image_on_screen(screen, f"e{TEMPLATE_EXT}")
                if res_e:
                    e_counter += 1
                    print(f"!!! 偵測到圖片 e (目前計數: {e_counter}/{TARGET_E_COUNT})")
                    
                    if e_counter >= TARGET_E_COUNT:
                        print("====================")
                        print("      完成          ")
                        print("====================")
                        sys.exit() # 結束整個程式碼

                    # 點擊 e.png 中心並等待 10 秒，之後回到狀態 d (保持現狀)
                    click_at_position(offset_x + res_e[0] + res_e[2]/2, offset_y + res_e[1] + res_e[3]/2)
                    print(">>> 點擊 e.png，等待 10 秒...")
                    time.sleep(10)
                    matched_this_loop = True
                
                # 2. 若沒偵測到 e 或執行完 e 之後的下一次循環，偵測 d_0
                else:
                    res_d0 = find_image_on_screen(screen, f"d_0{TEMPLATE_EXT}")
                    if res_d0:
                        # 公式點擊：(左上_x + 長 * 900/1000, 左上_y + 寬 * 560/600)
                        target_x = offset_x + width * 900 / 1000
                        target_y = offset_y + height * 560 / 600
                        click_at_position(target_x, target_y)
                        current_state = 'd_1'
                        print(">>> 狀態切換: d_1")
                        matched_this_loop = True
                    else:
                        current_state = 'd'
                        print(">>> 狀態切換: d")

            # 狀態 d_1: 尋找 d_1.png
            elif current_state == 'd_1':
                res = find_image_on_screen(screen, f"d_1{TEMPLATE_EXT}")
                if res:
                    # 1. 點擊 d_1.png 中心
                    start_x = offset_x + res[0] + res[2]/2
                    start_y = offset_y + res[1] + res[3]/2
                    click_at_position(start_x, start_y)
                    
                    # 2. 往上滑動至絕對螢幕座標 y=226
                    print(">>> 執行滑動動作至 y=226")
                    swipe_to_y(start_x, start_y, offset_y + 228)
                    
                    # 3. 再次執行公式點擊
                    target_x = offset_x + width * 900 / 1000
                    target_y = offset_y + height * 560 / 600
                    click_at_position(target_x, target_y)
                    
                    print(">>> 狀態 d_1 完成，等待 5 秒回到狀態 d")
                    time.sleep(5)
                    current_state = 'd'
                    matched_this_loop = True
                else:
                    current_state = 'd'
                    matched_this_loop = True

            # 更新失敗計數器
            failed_attempts_counter = 0 if matched_this_loop else failed_attempts_counter + 1
            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\n程式手動終止。")
    except SystemExit:
        print("\n任務達成，程式安全退出。")

if __name__ == "__main__":
    main()