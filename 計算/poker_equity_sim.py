import pandas as pd
import random
from treys import Card, Evaluator, Deck
from tqdm import tqdm
import os

# 設定參數
SIMULATIONS_PER_HAND = 500000  # 每種起手牌模擬次數
# 註：169種牌型 * 2000次 = 338,000次/每種人數配置
# 若要達到總數百萬次級別，建議設為 5000 或 10000，但跑起來會花不少時間。

PLAYER_COUNTS = [2, 3, 4, 5, 6] # 模擬 2 到 6 人桌

# 建立 169 種起手牌的列表 (例如: 'AA', 'AKs', 'AKo'...)
def get_all_starting_hands():
    ranks = 'AKQJT98765432'
    hands = []
    
    # 對子 (Pairs)
    for r in ranks:
        hands.append(r + r)
        
    # 同花 (Suited) & 不同花 (Offsuit)
    for i in range(len(ranks)):
        for j in range(i + 1, len(ranks)):
            hands.append(ranks[i] + ranks[j] + 's') # Suited
            hands.append(ranks[i] + ranks[j] + 'o') # Offsuit
            
    return hands

# 將字串牌型轉換為 treys 的 Card 物件
def convert_str_to_cards(hand_str):
    # hand_str 範例: 'AA', 'AKs', '72o'
    rank1 = hand_str[0]
    rank2 = hand_str[1]
    is_suited = 's' in hand_str
    is_pair = rank1 == rank2
    
    # 定義花色 (s=spades, h=hearts, d=diamonds, c=clubs)
    # 為了模擬，我們固定 Hero 的花色，這不影響勝率統計
    if is_pair:
        card1 = Card.new(rank1 + 's')
        card2 = Card.new(rank2 + 'h')
    elif is_suited:
        card1 = Card.new(rank1 + 's')
        card2 = Card.new(rank2 + 's')
    else: # offsuit
        card1 = Card.new(rank1 + 's')
        card2 = Card.new(rank2 + 'h')
        
    return [card1, card2]

def run_simulation():
    evaluator = Evaluator()
    starting_hands_list = get_all_starting_hands()
    
    print(f"開始模擬... 每種牌型模擬 {SIMULATIONS_PER_HAND} 次")
    
    for num_players in PLAYER_COUNTS:
        print(f"\n正在模擬 {num_players} 人桌...")
        results = []
        
        # 使用 tqdm 顯示進度條
        for hand_str in tqdm(starting_hands_list):
            wins = 0
            ties = 0
            
            # 取得 Hero 的固定手牌
            hero_hand = convert_str_to_cards(hand_str)
            
            for _ in range(SIMULATIONS_PER_HAND):
                deck = Deck()
                
                # 從牌堆中移除 Hero 的牌 (確保不會發出重複的牌)
                # treys 的 deck 生成時是隨機洗牌過的，但包含所有52張
                # 我們需要手動移除 Hero 拿走的這兩張特定牌
                deck.cards.remove(hero_hand[0])
                deck.cards.remove(hero_hand[1])
                
                # 發牌給對手
                opponents_hands = []
                for _ in range(num_players - 1):
                    opponents_hands.append(deck.draw(2))
                
                # 發公共牌 (5張) - 不考慮棄牌，直接發到 River
                board = deck.draw(5)
                
                # 評估牌力 (treys 分數越低越好, 1 是 Royal Flush)
                hero_score = evaluator.evaluate(board, hero_hand)
                opponent_scores = [evaluator.evaluate(board, opp) for opp in opponents_hands]
                
                best_opponent_score = min(opponent_scores)
                
                if hero_score < best_opponent_score:
                    wins += 1
                elif hero_score == best_opponent_score:
                    ties += 1
            
            # 計算該牌型的統計數據
            win_rate = wins / SIMULATIONS_PER_HAND
            tie_rate = ties / SIMULATIONS_PER_HAND
            equity = win_rate + (tie_rate / 2) # 常見 Equity 算法：勝率 + 平手的一半
            
            results.append({
                'Hand': hand_str,
                'Wins': wins,
                'Ties': ties,
                'Total': SIMULATIONS_PER_HAND,
                'Win_Rate': win_rate,
                'Tie_Rate': tie_rate,
                'Equity': equity
            })
        
        # 轉成 DataFrame 進行分析
        df = pd.DataFrame(results)
        
        # 計算 PR (Percentile Rank)
        # 我們根據 Equity (勝率+平手) 來排名。PR 100 代表最強，0 代表最弱
        df['PR'] = df['Equity'].rank(pct=True) * 100
        
        # 格式化顯示 (百分比)
        df['Win_Rate_%'] = (df['Win_Rate'] * 100).round(2)
        df['Tie_Rate_%'] = (df['Tie_Rate'] * 100).round(2)
        df['PR'] = df['PR'].round(1)
        
        # 排序方便閱讀 (從強到弱)
        df = df.sort_values(by='Equity', ascending=False)
        
        # 選擇最終輸出的欄位
        output_df = df[['Hand', 'Win_Rate_%', 'Tie_Rate_%', 'PR', 'Equity']]
        
        # 存檔
        filename = f'poker_stats_{num_players}_players.csv'
        output_df.to_csv(filename, index=False)
        print(f"存檔完成: {filename}")

if __name__ == '__main__':
    run_simulation()