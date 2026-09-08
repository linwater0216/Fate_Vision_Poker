import cv2
import numpy as np
import os

# 座標與範圍
ROI_PLAYERS = {"下家": (756, 188, 141, 152), "對家": (428, 19, 141, 152), "上家": (108, 188, 141, 152)}

def analyze_player_colors(image_path):
    if not os.path.exists(image_path):
        print("找不到圖片。")
        return

    img = cv2.imread(image_path)
    for pos, (x, y, w, h) in ROI_PLAYERS.items():
        roi = img[y:y+h, x:x+w]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        avg_h = np.mean(hsv[:,:,0])
        avg_s = np.mean(hsv[:,:,1])
        avg_v = np.mean(hsv[:,:,2])
        print(f"[{pos}] 平均 HSV: H={avg_h:.1f}, S={avg_s:.1f}, V={avg_v:.1f}")
        cv2.imshow(pos, roi)
    
    print("按下任意鍵結束...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # 請替換為您 manual_samples 資料夾中的一張「空位」圖片
    analyze_player_colors("pc/manual_samples/capture_20260906_012204.png")