import os
import shutil
import cv2
import numpy as np

# --- 基礎路徑設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_1 = os.path.join(BASE_DIR, "1") # 第一張牌資料夾
DIR_2 = os.path.join(BASE_DIR, "2") # 第二張牌資料夾

# YOLO 格式路徑
TRAIN_IMG = os.path.join(BASE_DIR, "dataset/images/train")
TRAIN_LBL = os.path.join(BASE_DIR, "dataset/labels/train")

# 定義 52 個手牌類別 (順序必須固定)
CARD_CLASSES = [
    '2c','2d','2h','2s','3c','3d','3h','3s','4c','4d','4h','4s','5c','5d','5h','5s',
    '6c','6d','6h','6s','7c','7d','7h','7s','8c','8d','8h','8s','9c','9d','9h','9s',
    'tc','td','th','ts','jc','jd','jh','js','qc','qd','qh','qs','kc','kd','kh','ks',
    'ac','ad','ah','as'
]
CLASS_MAP = {name: i for i, name in enumerate(CARD_CLASSES)}

# --- 座標邏輯 (基於 1000x600 視窗) ---
# 假設我們預處理時會裁切視窗中 X=530, Y=390 開始的 160x160 區域
CROP_X, C_Y = 530, 390 

def build_dataset(copy_count=100):
    """
    將 52 組手牌圖合成並複製多份生成資料集。
    copy_count: 每組手牌重複生成的張數
    """
    for d in [TRAIN_IMG, TRAIN_LBL]:
        if not os.path.exists(d): os.makedirs(d)

    # 取得資料夾 1 中的所有手牌檔名
    card_names = [f.replace('.png', '') for f in os.listdir(DIR_1) if f.endswith('.png')]

    print(f"開始生成資料集，每張牌重複 {copy_count} 次...")

    for name in card_names:
        if name not in CLASS_MAP: continue
        
        class_id = CLASS_MAP[name]
        
        # 讀取兩張原始手牌小圖 (30x46)
        img1 = cv2.imread(os.path.join(DIR_1, f"{name}.png"))
        img2 = cv2.imread(os.path.join(DIR_2, f"{name}.png"))

        # 建立一個 160x160 的底色 (模擬背景)
        canvas = np.zeros((160, 160, 3), dtype=np.uint8)
        canvas[:, :] = (40, 40, 40) # 暗灰色背景

        # 將手牌貼到畫布上 (計算相對位移)
        # 第一張牌座標 547, 405 -> 相對於裁切區 17, 15
        canvas[15:15+46, 17:17+30] = img1
        # 第二張牌座標 586, 401 -> 相對於裁切區 56, 11
        canvas[11:11+46, 56:56+30] = img2

        # 計算 YOLO 標籤 (正規化中心點 x, y, w, h)
        # 手牌1 中心點: (17+15)/160, (15+23)/160
        # 手牌2 中心點: (56+15)/160, (11+23)/160
        label_data = [
            f"{class_id} {32/160:.6f} {38/160:.6f} {30/160:.6f} {46/160:.6f}",
            f"{class_id} {71/160:.6f} {34/160:.6f} {30/160:.6f} {46/160:.6f}"
        ]

        # 複製並儲存
        for i in range(copy_count):
            file_name = f"{name}_{i:03d}"
            cv2.imwrite(os.path.join(TRAIN_IMG, f"{file_name}.jpg"), canvas)
            with open(os.path.join(TRAIN_LBL, f"{file_name}.txt"), "w") as f:
                f.write("\n".join(label_data))

    print(f"資料集建立完成：共 {len(card_names) * copy_count} 張訓練圖。")

if __name__ == "__main__":
    build_dataset(100) # 產生 5200 張圖