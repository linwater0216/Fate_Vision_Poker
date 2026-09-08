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
import pandas as pd
from collections import deque
from ultralytics import YOLO
from paddleocr import PaddleOCR

# --- 啟用 Windows 多螢幕高 DPI 感知 ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    pass

# --- 基礎路徑與檔案設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 修正路徑至 ../計算7%
EQUITY_DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "計算7%"))
SAMP_PATH = os.path.join(BASE_DIR, "samp")
MODEL_PATH = os.path.join(BASE_DIR, "best.pt")

EMULATOR_WINDOW_TITLE = "Poker Fate"
TARGET_WIDTH, TARGET_HEIGHT = 1000, 600

# --- 數據管理類別 ---
class EquityManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.cache = {}

    def get_closest_vpip(self, vpip):
        """將 VPIP 映射到 5 級距的檔案"""
        levels = list(range(20, 101, 5))
        return min(levels, key=lambda x: abs(x - vpip))

    def format_hand_str(self, cards):
        """將 YOLO 辨識結果 ['As', '3c'] 轉換為 'A3o' """
        if len(cards) != 2: return None
        rank_val = {'A':14,'K':13,'Q':12,'J':11,'T':10,'9':9,'8':8,'7':7,'6':6,'5':5,'4':4,'3':3,'2':2}
        r1, s1 = cards[0][0], cards[0][1]
        r2, s2 = cards[1][0], cards[1][1]
        if rank_val[r1] < rank_val[r2]:
            r1, s1, r2, s2 = r2, s2, r1, s1
        if r1 == r2: return f"{r1}{r2}"
        suffix = 's' if s1 == s2 else 'o'
        return f"{r1}{r2}{suffix}"

    def get_data_from_csv(self, cards, num_allin_opponents, avg_opp_vpip):
        """從 CSV 獲取預算好抽水的數據"""
        hand_key = self.format_hand_str(cards)
        total_p = num_allin_opponents + 1
        v_level = self.get_closest_vpip(avg_opp_vpip)
        filename = f"stats_{total_p}p_vpip_{v_level}.csv"
        path = os.path.join(self.data_dir, filename)
        
        key = (total_p, v_level)
        if key not in self.cache:
            if os.path.exists(path):
                self.cache[key] = pd.read_csv(path).set_index('Hand')
            else: return None
            
        df = self.cache[key]
        if hand_key in df.index:
            return df.loc[hand_key]
        return None

# --- 初始化 ---
eq_mgr = EquityManager(EQUITY_DATA_DIR)
ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
model = YOLO(MODEL_PATH)

# --- 座標與點位定義 ---
ROI_PLAYERS = {"下家": (756, 188, 141, 152), "對家": (428, 19, 141, 152), "上家": (108, 188, 141, 152)}
# 空位顏色判定閾值 (需搭配 Analyzer 獲取數值)
EMPTY_BLUE_HSV_RANGE = ([100, 50, 50], [130, 255, 255]) 
ALLIN_SEARCH_AREAS = {"下家": (662, 266, 80, 15), "對家": (459, 206, 80, 15), "上家": (259, 266, 80, 15)}
VPIP_OCR_ROI = (688, 380, 90, 28)

player_db = {
    "下家": {"vpip": 65, "trust": 0, "exists": False},
    "對家": {"vpip": 65, "trust": 0, "exists": False},
    "上家": {"vpip": 65, "trust": 0, "exists": False}
}

def cv2_imread_unicode(path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

def get_emulator_screen(hwnd):
    """採用與 260825steam.py 一致的擷圖邏輯，確保座標無偏移"""
    try:
        if not win32gui.IsWindow(hwnd): return None, 0, 0, 0, 0
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        c_left, c_top, c_right, c_bottom = win32gui.GetClientRect(hwnd)
        width, height = c_right - c_left, c_bottom - c_top
        
        # 尺寸校正
        if (right - left) != 1000 or (bottom - top) != 600:
             win32gui.MoveWindow(hwnd, left, top, 1000, 600, True)
             left, top, right, bottom = win32gui.GetWindowRect(hwnd)
             width, height = c_right - c_left, c_bottom - c_top

        screen_left, screen_top = win32gui.ClientToScreen(hwnd, (0, 0))
        screen_pil = ImageGrab.grab(bbox=(screen_left, screen_top, screen_left + width, screen_top + height), all_screens=True)
        img_cv = cv2.cvtColor(np.array(screen_pil), cv2.COLOR_RGB2BGR)
        return img_cv, screen_left, screen_top, width, height
    except: return None, 0, 0, 0, 0

def find_img(screen, name, threshold=0.9):
    path = os.path.join(SAMP_PATH, f"{name}.png")
    template = cv2_imread_unicode(path)
    if template is None: return None
    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    return (max_loc[0], max_loc[1], template.shape[1], template.shape[0]) if max_val >= threshold else None

def run_decision(screen, off_x, off_y):
    # 1. YOLO 辨識手牌 (裁切 530,390 寬高160x160)
    hand_crop = screen[390:390+160, 530:530+160]
    results = model.predict(hand_crop, conf=0.75, verbose=False)
    cards = []
    for r in results:
        for box in r.boxes:
            cards.append((model.names[int(box.cls[0])], box.xywh[0][0].item()))
    if len(cards) < 2: return

    cards.sort(key=lambda x: x[1])
    hand_formatted = eq_mgr.format_hand_str(cards)

    # 2. 誰已經 ALLIN
    allin_vpip = []
    for pos, (ax, ay, aw, ah) in ALLIN_SEARCH_AREAS.items():
        if find_img(screen[ay:ay+ah, ax:ax+aw], "ALL_IN", threshold=0.8):
            allin_vpip.append(player_db[pos]["vpip"])

    # 3. 根據 CSV 做決策
    avg_v = sum(allin_vpip)/len(allin_vpip) if allin_vpip else 65
    csv_data = eq_mgr.get_data_from_csv(cards, len(allin_vpip), avg_v)
    
    if csv_data is not None:
        adj_equity = csv_data['Rake_Adj_Equity']
        # 門檻邏輯：因為 CSV 已算好抽水，理論上 Adj_Equity > (投入/總池) 即可
        # 10BB AOF 簡化門檻：0.46
        print(f">>> 決策分析: 手牌={hand_formatted}, 對手數={len(allin_vpip)}, Adj_Equity={adj_equity:.4f}")
        
        if adj_equity > 0.465:
            print("!!! 執行 ALL-IN !!!")
            allin_btn = find_img(screen, "ALL_IN")
            if allin_btn:
                pyautogui.click(off_x + allin_btn[0] + allin_btn[2]//2, off_y + allin_btn[1] + allin_btn[3]//2)
        else:
            print("--- 執行棄牌 ---")
            # 棄牌點擊由 main 函式後續處理

def main():
    hwnd = None
    windows = gw.getWindowsWithTitle(EMULATOR_WINDOW_TITLE)
    if windows: hwnd = windows[0]._hWnd
    
    current_state = "主頁"
    
    while True:
        if win32api.GetAsyncKeyState(0x51) & 0x8000: break # Q 退出
        
        screen, off_x, off_y, width, height = get_emulator_screen(hwnd)
        if screen is None: continue

        # 優先權：棄牌按鈕決策
        fold_res = find_img(screen, "棄牌")
        if fold_res:
            time.sleep(0.4) # 等待翻牌
            fresh_screen, _, _, _, _ = get_emulator_screen(hwnd)
            run_decision(fresh_screen, off_x, off_y)
            pyautogui.click(off_x + fold_res[0] + fold_res[2]//2, off_y + fold_res[1] + fold_res[3]//2)
            time.sleep(1.5)
            continue

        # 導航與偵查
        if current_state == "主頁":
            res = find_img(screen, "玩法合集")
            if res:
                pyautogui.click(off_x + res[0] + res[2]//2, off_y + res[1] + res[3]//2)
                current_state = "奧瑪哈或AOF"
        
        elif current_state == "奧瑪哈或AOF":
            res = find_img(screen, "AOF")
            if res:
                pyautogui.click(off_x + res[0] + res[2]//2, off_y + res[1] + res[3]//2)
                current_state = "AOF選桌"

        elif current_state == "AOF選桌":
            if find_img(screen, "AOF確認"):
                res_t = find_img(screen, "AOF綠桌")
                if res_t:
                    pyautogui.click(off_x + res_t[0] + res_t[2]//2, off_y + res_t[1] + res_t[3]//2)
                    current_state = "AOF遊戲"
                else:
                    pyautogui.moveTo(off_x + 500, off_y + 300)
                    pyautogui.dragTo(off_x + 800, off_y + 300, duration=0.5, button='left')
                    time.sleep(1.2)

        elif current_state == "AOF遊戲":
            # 玩家存在判定：顏色 + 名字不為空 (雙重判定)
            for pos, (rx, ry, rw, rh) in ROI_PLAYERS.items():
                roi = screen[ry:ry+rh, rx:rx+rw]
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, np.array(EMPTY_BLUE_HSV_RANGE[0]), np.array(EMPTY_BLUE_HSV_RANGE[1]))
                player_db[pos]["exists"] = (np.sum(mask > 0) / (rw * rh)) < 0.85

            # 偵查信任度為 0 的玩家
            for pos, data in player_db.items():
                if data["exists"] and data["trust"] == 0:
                    x, y, w, h = ROI_PLAYERS[pos]
                    pyautogui.click(off_x + x + w//2, off_y + y + h//2)
                    time.sleep(1.2)
                    recon_screen, _, _, _, _ = get_emulator_screen(hwnd)
                    # OCR
                    vx, vy, vw, vh = VPIP_OCR_ROI
                    v_crop = recon_screen[vy:vy+vh, vx:vx+vw]
                    ocr_res = ocr.ocr(v_crop, cls=True)
                    try:
                        v_val = "".join(filter(str.isdigit, ocr_res[0][0][1][0]))
                        if v_val:
                            player_db[pos]["vpip"] = int(v_val)
                            player_db[pos]["trust"] = 100
                            print(f"[{pos}] VPIP 更新為: {v_val}%")
                    except: pass
                    exit_btn = find_img(recon_screen, "退出玩家資訊")
                    if exit_btn: pyautogui.click(off_x + exit_btn[0] + exit_btn[2]//2, off_y + exit_btn[1] + exit_btn[3]//2)
                    break
        time.sleep(0.1)

if __name__ == "__main__":
    main()