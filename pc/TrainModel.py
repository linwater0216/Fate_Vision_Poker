from ultralytics import YOLO
import os

# --- 基礎路徑設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(BASE_DIR, "poker.yaml")

def run_train():
    # 使用 YOLOv11 Nano 版本，速度最快
    model = YOLO("yolo11n.pt")

    # 開始訓練
    model.train(
        data=YAML_PATH,
        epochs=50,       # 既然是重複圖片，50 輪絕對足夠收斂
        imgsz=160,       # 設定訓練解析度為 160
        batch=64,        # RTX 3060/5060 跑 160 尺寸可設很大
        device=0,        # 指定 GPU
        workers=4,       # 多執行緒讀取數據
        name="poker_v11_fixed"
    )

if __name__ == "__main__":
    run_train()