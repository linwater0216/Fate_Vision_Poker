import pandas as pd
import random
import os
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from treys import Card, Evaluator, Deck
from tqdm import tqdm

# ==========================================
# 基礎路徑設定 (確保以程式碼檔案所在目錄為基準)
# ==========================================
# 取得目前程式碼檔案 (.py) 的絕對路徑目錄
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 參數設定
# ==========================================
ITERATIONS = 500000  # 每種手牌對抗特定範圍的模擬次數 (建議 5000 次以平衡精度與時間)
PLAYER_COUNTS = [2, 3, 4]  # 模擬 2, 3, 4 人桌
# VPIP 範圍從 20 到 100，間距 5 (20, 25, 30, ... 100)
VPIP_LEVELS = list(range(20, 101, 5)) 
RAKE = 0.07  # 抽水 7%

# 修正後的資料夾路徑：確保在程式碼同目錄下建立 7% 資料夾
OUTPUT_DIR = os.path.join(BASE_DIR, "7%")

# 如果輸出目錄不存在則建立
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ==========================================
# 手牌等級與組合邏輯 (用於精確模擬 VPIP 範圍)
# ==========================================

def get_hand_rankings_list():
    """
    根據標準強度排列 169 種起手牌。
    用於後續篩選對手的 VPIP 範圍。
    """
    ranks = 'AKQJT98765432'
    standard_order = [
        'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', 'AKs', '77', 'AQs', 'AJs', 'AKo', 'ATs', 'AQo', 'AJo', 'KQs', 
        '66', 'A9s', 'ATo', 'KJs', 'A8s', 'KTs', 'KQo', 'A7s', 'A9o', 'KJo', 'QJs', '55', 'K9s', 'A5s', 'A6s', 
        'A8o', 'KTo', 'QTs', 'A4s', 'A7o', 'K8s', 'A3s', 'QJo', 'K9o', 'A5o', 'A6o', 'Q9s', 'K7s', 'JTs', 'A2s', 
        'QTo', '44', 'K6s', 'A4o', 'K8o', 'Q8s', 'A3o', 'K5s', 'J9s', 'Q9o', 'JTo', 'K7o', 'A2o', 'K4s', 'Q7s', 
        'K6o', 'J8s', 'K3s', 'T9s', '33', 'Q6s', 'Q8o', 'K5o', 'K2s', 'J9o', 'Q5s', 'T8s', 'K4o', 'J7s', 'Q4s', 
        'Q7o', 'T9o', 'J8o', 'K3o', 'Q6o', 'Q3s', '98s', 'J6s', 'K2o', 'T7s', '22', 'Q2s', 'J5s', 'Q5o', 'T8o', 
        'J7o', '97s', 'J4s', 'Q4o', 'T6s', 'J3s', 'Q3o', '98o', '87s', 'T7o', 'J6o', '96s', 'J2s', 'Q2o', 'T5s', 
        'J5o', 'T4s', '97o', '86s', 'J4o', 'T6o', '95s', 'T3s', 'J3o', '76s', '87o', 'T2s', '85s', '96o', 'T5o', 
        'J2o', '94s', '75s', 'T4o', '93s', '86o', '65s', '84s', '95o', 'T3o', '76o', '92s', '74s', 'T2o', '64s', 
        '54s', '85o', '83s', '94o', '75o', '82s', '73s', '93o', '65o', '53s', '63s', '84o', '92o', '43s', '74o', 
        '72s', '54o', '64o', '52s', '62s', '83o', '42s', '82o', '73o', '53o', '63o', '32s', '43o', '72o', '52o', 
        '62o', '42o', '32o'
    ]
    return standard_order

def hand_to_treys(hand_str):
    """將 'AKs' 等字串轉為 Card 物件"""
    r1, r2 = hand_str[0], hand_str[1]
    if 's' in hand_str:
        return [Card.new(r1 + 's'), Card.new(r2 + 's')]
    elif 'o' in hand_str or r1 != r2:
        return [Card.new(r1 + 's'), Card.new(r2 + 'h')]
    else: # Pairs
        return [Card.new(r1 + 's'), Card.new(r2 + 'h')]

# ==========================================
# 核心模擬函數
# ==========================================

def simulate_aof_task(args):
    """
    執行單一手牌對抗特定 VPIP 範圍的模擬。
    """
    hero_hand_str, opp_vpip, num_players, iterations, hand_rankings = args
    evaluator = Evaluator()
    hero_cards = hand_to_treys(hero_hand_str)
    
    vpip_count = max(1, int(len(hand_rankings) * (opp_vpip / 100)))
    allowed_hand_types = hand_rankings[:vpip_count]
    
    wins = 0
    ties = 0
    
    for _ in range(iterations):
        deck = Deck()
        for c in hero_cards:
            deck.cards.remove(c)
            
        opponents_hands = []
        for _ in range(num_players - 1):
            valid_hand = False
            while not valid_hand:
                try:
                    cards = random.sample(deck.cards, 2)
                    r1 = Card.get_rank_int(cards[0])
                    r2 = Card.get_rank_int(cards[1])
                    s1 = Card.get_suit_int(cards[0])
                    s2 = Card.get_suit_int(cards[1])
                    
                    rank_map = {12:'A', 11:'K', 10:'Q', 9:'J', 8:'T', 7:'9', 6:'8', 5:'7', 4:'6', 3:'5', 2:'4', 1:'3', 0:'2'}
                    char1, char2 = rank_map[r1], rank_map[r2]
                    
                    ranks_str = 'AKQJT98765432'
                    if ranks_str.index(char1) > ranks_str.index(char2):
                        char1, char2 = char2, char1
                    
                    if char1 == char2:
                        type_str = char1 + char2
                    elif s1 == s2:
                        type_str = char1 + char2 + 's'
                    else:
                        type_str = char1 + char2 + 'o'
                    
                    if type_str in allowed_hand_types:
                        for c in cards: deck.cards.remove(c)
                        opponents_hands.append(cards)
                        valid_hand = True
                except ValueError:
                    break
                    
        board = deck.draw(5)
        hero_score = evaluator.evaluate(board, hero_cards)
        opp_scores = [evaluator.evaluate(board, h) for h in opponents_hands]
        
        if not opp_scores: continue
        
        best_opp = min(opp_scores)
        if hero_score < best_opp:
            wins += 1
        elif hero_score == best_opp:
            ties += 1
            
    equity = (wins + (ties / 2)) / iterations
    rake_adj_equity = equity * (1 - RAKE)
    
    return {
        'Hand': hero_hand_str,
        'Equity': equity,
        'Rake_Adj_Equity': rake_adj_equity,
        'VPIP': opp_vpip
    }

# ==========================================
# 主程式執行 (支援多核心與 10% 預留)
# ==========================================

def main():
    # 多核心設定：保留 10% 核心給系統其他程式
    total_cores = multiprocessing.cpu_count()
    use_cores = max(1, int(total_cores * 0.9))
    print(f"程式目錄: {BASE_DIR}")
    print(f"系統核心總數: {total_cores}, 投入計算核心數: {use_cores}")
    
    hand_rankings = get_hand_rankings_list()
    
    for num_p in PLAYER_COUNTS:
        for vpip in VPIP_LEVELS:
            output_filename = f"stats_{num_p}p_vpip_{vpip}.csv"
            # 使用絕對路徑結合 BASE_DIR 與 OUTPUT_DIR
            save_path = os.path.join(OUTPUT_DIR, output_filename)
            
            if os.path.exists(save_path):
                print(f"檔案已存在，跳過: {output_filename}")
                continue
                
            print(f"\n[開始計算] {num_p}人桌 | 對手 VPIP: {vpip}%")
            
            tasks = [(h, vpip, num_p, ITERATIONS, hand_rankings) for h in hand_rankings]
            
            results = []
            with ProcessPoolExecutor(max_workers=use_cores) as executor:
                results = list(tqdm(executor.map(simulate_aof_task, tasks), total=len(tasks), desc="進度"))
            
            df = pd.DataFrame(results)
            df['PR'] = df['Equity'].rank(pct=True) * 100
            df = df.sort_values(by='Equity', ascending=False)
            
            # 存檔至絕對路徑
            df.to_csv(save_path, index=False)
            print(f"完成存檔: {save_path}")

if __name__ == '__main__':
    main()