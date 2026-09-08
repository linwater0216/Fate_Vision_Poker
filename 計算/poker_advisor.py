import pandas as pd
import os

class PokerAdvisorPro:
    def __init__(self):
        self.cache = {}
        
        # 定義不同人數桌的標準位置名稱
        # 順序：從槍口(或是最先行動者) 到 大盲
        self.POSITIONS_MAP = {
            2: ['SB (BTN)', 'BB'],
            3: ['BTN', 'SB', 'BB'],
            4: ['CO', 'BTN', 'SB', 'BB'],
            5: ['MP', 'CO', 'BTN', 'SB', 'BB'], # 5人通常略過 UTG
            6: ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        }

        # 定義 RFI (率先加注) 的 PR 閥值
        # 意思：你的牌力 PR 必須高於這個數值才建議 Open
        # 數值參考一般 GTO 頻率轉換而來
        self.RFI_THRESHOLDS = {
            'UTG': 83.0,      # 6人桌最緊
            'MP':  72.0,      # 6人桌次緊 / 5人桌最緊
            'CO':  55.0,      # 關煞位，開始變鬆
            'BTN': 40.0,      # 按鈕位，主要偷盲位置，很鬆
            'SB (BTN)': 45.0, # 2人桌的 Dealer，很鬆
            'SB':  50.0,      # 正常小盲 RFI (若前方都棄牌)，需考慮 BB 防守
            'BB':  None       # 大盲無法 RFI，只能 Check 或防守
        }

    def load_data(self, num_players):
        filename = f'poker_stats_{num_players}_players.csv'
        if num_players in self.cache:
            return self.cache[num_players]
        
        if not os.path.exists(filename):
            print(f"錯誤: 找不到 {filename}，請先執行模擬程式。")
            return None
            
        df = pd.read_csv(filename)
        df.set_index('Hand', inplace=True)
        self.cache[num_players] = df
        return df

    def parse_input_hand(self, raw_input):
        """解析手牌 (與上一版相同)"""
        raw = raw_input.strip()
        if len(raw) == 4: # AhKh
            r1, s1, r2, s2 = raw[0].upper(), raw[1].lower(), raw[2].upper(), raw[3].lower()
            ranks_order = 'AKQJT98765432'
            if ranks_order.index(r1) > ranks_order.index(r2):
                r1, r2 = r2, r1
                s1, s2 = s2, s1
            return (r1 + r2) if r1 == r2 else (r1 + r2 + ('s' if s1 == s2 else 'o'))
            
        formatted = raw.upper()
        if len(formatted) == 2: return formatted if formatted[0] == formatted[1] else formatted + 'o'
        if len(formatted) == 3: return formatted[:2] + formatted[2].lower()
        return None

    def get_advice(self, num_players, hand_str, position_idx):
        """
        position_idx: 該桌位置列表的索引 (0, 1, 2...)
        """
        df = self.load_data(num_players)
        if df is None: return

        hand_key = self.parse_input_hand(hand_str)
        if hand_key not in df.index:
            print(f"無法識別: {hand_str}")
            return

        stats = df.loc[hand_key]
        pr = stats['PR']
        equity = stats['Equity']
        
        # 取得位置名稱
        pos_list = self.POSITIONS_MAP[num_players]
        pos_name = pos_list[position_idx]
        
        print(f"\n======== 分析報告 ({num_players}人桌) ========")
        print(f"手牌: {hand_key} | 位置: {pos_name}")
        print(f"PR值: {pr} (贏過 {pr}% 的起手牌)")
        print(f"Equity: {equity:.4f}")
        print("-" * 35)

        # --- 策略核心邏輯 ---
        
        # 特殊處理：大盲 (BB)
        if 'BB' in pos_name:
            print(f"建議: 防守 (Defend) 或 過牌 (Check)")
            print(f"理由: 你在大盲位。若無人加注，你免費看牌。若有人加注，依賠率防守。")
            if pr > 75: print("(註：若是強牌如 JJ+, AK，遭遇加注應考慮 3-Bet)")
            return

        # 取得該位置的建議 PR 門檻
        threshold = self.RFI_THRESHOLDS.get(pos_name.split(' ')[0], 60) # 預設 60
        
        # 2人桌(Heads Up) 特殊調整
        if num_players == 2 and 'SB' in pos_name:
            threshold = 45 # 單挑時 SB 範圍很廣

        # 判斷行動
        if pr >= 96:
            action = "強力加注 (Raise / 4-Bet)"
            strength = "頂級強牌 (Premium)"
        elif pr >= threshold + 10:
            action = "加注 (Open Raise)"
            strength = "強牌 (Strong)"
        elif pr >= threshold:
            action = "加注 (Open Raise) / 混合策略"
            strength = "邊緣可玩 (Playable)"
        else:
            action = "棄牌 (Fold)"
            strength = "低於該位置標準"

        print(f"建議行動: {action}")
        print(f"牌力評價: {strength}")
        print(f"該位置建議 RFI 基準 PR: > {threshold}")

        # 額外提示
        if action == "棄牌 (Fold)" and pr >= 40 and pos_name in ['BTN', 'SB']:
            print("提示: 雖然建議棄牌，但在按鈕位若對手很緊，這手牌偶爾可以用來偷盲。")

# --- 主程式 ---
if __name__ == "__main__":
    advisor = PokerAdvisorPro()
    
    print("=== 專業德州撲克入池建議 (V2) ===")
    
    while True:
        try:
            # 1. 輸入人數
            np = int(input("\n請輸入玩家人數 (2-6): "))
            if np not in advisor.POSITIONS_MAP:
                print("只支援 2-6 人。")
                continue

            # 2. 顯示並選擇位置
            positions = advisor.POSITIONS_MAP[np]
            print(f"請選擇你的位置 (輸入 0-{len(positions)-1}):")
            for idx, name in enumerate(positions):
                print(f"  {idx}. {name}")
            
            p_idx = int(input("位置編號: "))
            if p_idx < 0 or p_idx >= len(positions):
                print("無效的位置編號。")
                continue

            # 3. 輸入手牌
            hand = input("請輸入手牌 (例如 AKs, 77, Th9h): ")
            
            # 4. 分析
            advisor.get_advice(np, hand, p_idx)

        except ValueError:
            print("輸入錯誤，請輸入數字。")
        except KeyboardInterrupt:
            print("\n程式結束。")
            break