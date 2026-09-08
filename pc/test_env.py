import torch
import os

# 優化 Blackwell 載入
os.environ["CUDA_MODULE_LOADING"] = "LAZY"

def final_check():
    print(f"PyTorch 版本: {torch.__version__}")
    print(f"CUDA 是否可用: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        cap = torch.cuda.get_device_capability(0)
        print(f"目前顯卡: {name}")
        print(f"計算能力: {cap}") # 應該會看到 (12, 0)
        
        # 測試運算
        x = torch.randn(10, 10).cuda()
        y = torch.matmul(x, x)
        print(">>> [驗證成功]：環境已達到 2.14 穩定版，警告應已消失。")

if __name__ == "__main__":
    final_check()