import cv2
import numpy as np
from ultralytics import YOLO
import os
import torch
import warnings

# --- 1. 環境變數優化 (針對 RTX 5060 Blackwell 架構) ---
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["CUDA_MODULE_LOADING"] = "LAZY"

# --- 2. 基礎路徑設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "best.pt")
TEST_IMAGE_PATH = os.path.join(BASE_DIR, "manual_samples", "capture_20260906_011756.png")

# --- 3. 灰底填充函式 ---
def pad_to_64x64(img, bg_color=114):
    """
    將原始小圖 (30x46) 放置於 64x64 灰底畫布中心。
    """
    if img is None or img.size == 0:
        return np.full((64, 64, 3), bg_color, dtype=np.uint8)
        
    h, w = img.shape[:2]
    canvas = np.full((64, 64, 3), bg_color, dtype=np.uint8)
    
    y_offset = (64 - h) // 2
    x_offset = (64 - w) // 2
    
    canvas[y_offset : y_offset+h, x_offset : x_offset+w] = img
    return canvas

# --- 4. 手牌格式化邏輯 (修正大小寫 Bug) ---
def format_poker_hand(detected_cards):
    """
    detected_cards: 辨識出的兩張牌名稱清單, 如 ['9c', 'th']
    """
    if len(detected_cards) != 2:
        return f"偵測張數錯誤: {len(detected_cards)}"
    
    # 標準德州撲克點數權重 (大寫)
    rank_order = "AKQJT98765432"
    
    # 取得原始字串
    c1, c2 = detected_cards[0], detected_cards[1]
    
    # 提取點數並轉為大寫進行比較 (解決 t vs T 的問題)
    r1_raw, s1 = c1[0].upper(), c1[1]
    r2_raw, s2 = c2[0].upper(), c2[1]
    
    # 邏輯排序：確保點數大的牌排在前面
    if rank_order.index(r1_raw) > rank_order.index(r2_raw):
        r1, s1, r2, s2 = r2_raw, s2, r1_raw, s1
    else:
        r1, s1, r2, s2 = r1_raw, s1, r2_raw, s2
    
    # 輸出組合
    if r1 == r2:
        return f"{r1}{r2}"    # 對子 (如 TT, 99)
    elif s1 == s2:
        return f"{r1}{r2}s"   # 同花 (如 T9s)
    else:
        return f"{r1}{r2}o"   # 雜色 (如 T9o)

def cv2_imread_unicode(path):
    try:
        return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    except:
        return None

# --- 5. 主測試程序 ---
def run_preprocessed_test():
    print(">>> 啟動 YOLO 灰底填充測試程序 (修正大小寫版)...")

    if not os.path.exists(MODEL_PATH):
        print(f"錯誤：找不到模型 -> {MODEL_PATH}")
        return
    model = YOLO(MODEL_PATH).to('cuda')

    full_img = cv2_imread_unicode(TEST_IMAGE_PATH)
    if full_img is None:
        print("錯誤：無法讀取測試大圖")
        return

    # 5.1 精確裁切
    # 第一張 X=547, Y=405 / 第二張 X=586, Y=401 (寬30, 高46)
    card1_raw = full_img[405:405+46, 547:547+30]
    card2_raw = full_img[401:401+46, 586:586+30]

    # 5.2 灰底填充
    card1_ready = pad_to_64x64(card1_raw)
    card2_ready = pad_to_64x64(card2_raw)

    # 5.3 執行辨識
    input_batch = [card1_ready, card2_ready]
    results = model.predict(source=input_batch, conf=0.5, device=0, imgsz=64, verbose=False)

    detected_names = []
    for i, res in enumerate(results):
        if len(res.boxes) > 0:
            cls_id = int(res.boxes.cls[0])
            name = model.names[cls_id]
            detected_names.append(name)
            print(f"卡片 {i+1} 辨識成功: {name}")
        else:
            print(f"卡片 {i+1} 辨識失敗")

    # 5.4 格式化輸出
    if len(detected_names) == 2:
        try:
            final_csv_key = format_poker_hand(detected_names)
            print("\n" + "="*30)
            print(f"辨識結果: {detected_names[0]} + {detected_names[1]}")
            print(f"最終查表標籤: {final_csv_key}")
            print("="*30)
        except Exception as e:
            print(f"格式化過程出錯: {e}")

    # 5.5 預覽
    combined = np.hstack((card1_ready, card2_ready))
    cv2.imshow("Corrected Input", cv2.resize(combined, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_preprocessed_test()