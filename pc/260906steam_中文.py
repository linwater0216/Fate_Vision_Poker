import numpy as np
import cv2
import time
import pyautogui
import pygetwindow as gw
import win32gui
import win32con
import win32api  # 用於全域偵測鍵盤事件
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

# --- 設定區域 (Configuration Area) ---
EMULATOR_WINDOW_TITLE = "Poker Fate"  

TEMPLATE_IMAGE_PATH = "./pc/samp"    # 模板圖片路徑
SAVE_PATH = "./samp1"            # 按下 's' 儲存截圖的路徑
THRESHOLD = 0.91                 # 模板匹配閾值

# 固定視窗尺寸
TARGET_WIDTH = 1018            
TARGET_HEIGHT = 647               

TEMPLATE_EXT = ".png"
MAX_FAILED_ATTEMPTS = 200         # 偵錯自癒上限
LOOP_DELAY = 0.1                 # 迴圈間隔

# --- 計數器設定 ---
TARGET_E_COUNT = 6               # 設定偵測到「報名下一場」圖片的目標次數

# 確保儲存路徑存在
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

def find_image_on_screen(screen, template_name):
    """
    在目標畫面上尋找模板圖片位置。
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
        
        if (right - left) != TARGET_WIDTH or (bottom - top) != TARGET_HEIGHT:
             win32gui.MoveWindow(hwnd, left, top, TARGET_WIDTH, TARGET_HEIGHT, True)
             left, top, right, bottom = win32gui.GetWindowRect(hwnd)
             c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
             width, height = c_right - c_left, c_bottom - c_top

        screen_left, screen_top = win32gui.ClientToScreen(hwnd, (0, 0))
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
    current_state = '主頁'
    failed_attempts_counter = 0
    e_counter = 0

    print(f"Poker Fate 腳本啟動。目標報名下一場次數: {TARGET_E_COUNT}")
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
                # 對應原本的 ['a', 'b', 'c', 'd_0', 'd_1', 'e']
                potential_imgs = ['賽事', '免費賽', '立即報名', '棄牌', '籌碼拉條', '報名下一場']
                for pi in potential_imgs:
                    if find_image_on_screen(screen, f"{pi}{TEMPLATE_EXT}"):
                        if pi == '賽事': current_state = '主頁'
                        elif pi == '免費賽': current_state = '所有sng'
                        elif pi == '立即報名': current_state = '免費sng報名'
                        elif pi == '棄牌': current_state = '找尋棄牌按鈕準備加注'
                        elif pi == '籌碼拉條': current_state = 'all_in'
                        elif pi == '報名下一場': current_state = '找尋棄牌按鈕準備加注'
                        
                        print(f"[自癒] 成功，切換至狀態: {current_state}")
                        failed_attempts_counter = 0
                        break
                if failed_attempts_counter != 0:
                    failed_attempts_counter = 0 

            matched_this_loop = False

            # --- 狀態機邏輯 ---
            
            # 狀態：主頁 (原 a)
            if current_state == '主頁':
                res = find_image_on_screen(screen, f"賽事{TEMPLATE_EXT}")
                if res:
                    click_at_position(offset_x + res[0] + res[2]/2, offset_y + res[1] + res[3]/2)
                    current_state = '所有sng'
                    print(">>> 狀態切換: 所有sng")
                    matched_this_loop = True

            # 狀態：所有sng (原 b)
            elif current_state == '所有sng':
                res = find_image_on_screen(screen, f"免費賽{TEMPLATE_EXT}")
                if res:
                    click_at_position(offset_x + res[0] + res[2]/2, offset_y + res[1] + res[3]/2)
                    current_state = '免費sng報名'
                    print(">>> 狀態切換: 免費sng報名")
                    matched_this_loop = True

            # 狀態：免費sng報名 (原 c)
            elif current_state == '免費sng報名':
                res_c0 = find_image_on_screen(screen, f"確認為免費賽{TEMPLATE_EXT}")
                res_c = find_image_on_screen(screen, f"立即報名{TEMPLATE_EXT}")
                if res_c0 and res_c:
                    click_at_position(offset_x + res_c[0] + res_c[2]/2, offset_y + res_c[1] + res_c[3]/2)
                    print(">>> 報名觸發，等待 5 秒...")
                    time.sleep(5)
                    current_state = '找尋棄牌按鈕準備加注'
                    print(">>> 狀態切換: 找尋棄牌按鈕準備加注")
                    matched_this_loop = True

            # 狀態：找尋棄牌按鈕準備加注 (原 d)
            elif current_state == '找尋棄牌按鈕準備加注':
                # 1. 偵測圖片：報名下一場 (原 e)
                res_e = find_image_on_screen(screen, f"報名下一場{TEMPLATE_EXT}")
                if res_e:
                    e_counter += 1
                    print(f"!!! 偵測到報名下一場 (目前計數: {e_counter}/{TARGET_E_COUNT})")
                    
                    if e_counter >= TARGET_E_COUNT:
                        print("====================")
                        print("      完成          ")
                        print("====================")
                        sys.exit() 

                    click_at_position(offset_x + res_e[0] + res_e[2]/2, offset_y + res_e[1] + res_e[3]/2)
                    print(">>> 點擊報名下一場，等待 10 秒...")
                    time.sleep(10)
                    matched_this_loop = True
                
                # 2. 偵測圖片：棄牌 (原 d_0)
                else:
                    res_d0 = find_image_on_screen(screen, f"棄牌{TEMPLATE_EXT}")
                    if res_d0:
                        target_x = offset_x + width * 900 / 1000
                        target_y = offset_y + height * 560 / 600
                        click_at_position(target_x, target_y)
                        current_state = 'all_in'
                        print(">>> 狀態切換: all_in")
                        matched_this_loop = True
                    else:
                        current_state = '找尋棄牌按鈕準備加注'

            # 狀態：all_in (原 d_1)
            elif current_state == 'all_in':
                res = find_image_on_screen(screen, f"籌碼拉條{TEMPLATE_EXT}")
                if res:
                    # 1. 點擊圖片中心
                    start_x = offset_x + res[0] + res[2]/2
                    start_y = offset_y + res[1] + res[3]/2
                    click_at_position(start_x, start_y)
                    
                    # 2. 往上滑動動作
                    print(">>> 執行滑動動作至 y=228")
                    swipe_to_y(start_x, start_y, offset_y + 280)
                    
                    # 3. 公式點擊
                    target_x = offset_x + width * 900 / 1000
                    target_y = offset_y + height * 560 / 600
                    click_at_position(target_x, target_y)
                    
                    print(">>> all_in 完成，等待 5 秒回到找尋狀態")
                    time.sleep(5)
                    current_state = '找尋棄牌按鈕準備加注'
                    matched_this_loop = True
                else:
                    current_state = '找尋棄牌按鈕準備加注'
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