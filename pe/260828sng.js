// 請求啟用無障礙服務 (Request Accessibility Service)
auto.waitFor();

// 請求螢幕截圖權限 (Request Screen Capture Permissions)
// 參數 false 代表自動偵測目前螢幕方向（直向或橫向）
if (!requestScreenCapture(false)) {
    toastLog("請求截圖權限失敗，請重新執行並給予權限");
    exit();
}

// --- 設定區域 (Configuration Area) ---
// 模板圖片存放路徑 (Template Path)
// 請在手機的 "/sdcard/指令碼/遊戲掛機用/PokerFate/samp/" 目錄下放置您的 a, b, c, c_0, d_0, d_1, e .png 圖片
const TEMPLATE_IMAGE_PATH = "/sdcard/指令碼/遊戲掛機用/PokerFate/samp/";
const THRESHOLD = 0.91;          // 模板匹配相似度閾值 (Threshold)
const TEMPLATE_EXT = ".png";     // 圖片副檔名
const MAX_FAILED_ATTEMPTS = 200; // 偵錯自癒上限次數 (Max Failed Attempts)
const LOOP_DELAY = 100;          // 迴圈間隔延遲時間（微秒，100ms = 0.1s）

// --- 計數器設定 (Counter Settings) ---
const TARGET_E_COUNT = 8;        // 偵測到圖片 e 的目標次數，達到後結束程式

// --- 全域變數定義 (Global Variables) ---
var currentState = "a";          // 初始狀態設為 'd'
var failedAttemptsCounter = 0;   // 偵錯連續失敗計數器
var eCounter = 0;                // 圖片 e 的累計次數
var isRunning = true;            // 腳本運作標記 (Thread Control Flag)

/**
 * 在螢幕上尋找指定模板圖片的位置（採用彩色匹配）。
 * 
 * @param {Image} screen 系統當前擷取的螢幕快照 (Screen Image)
 * @param {string} templateName 模板圖片名稱
 * @returns {Array|null} 返回 [x, y, w, h, similarity] 或 null
 */
function findImageOnScreen(screen, templateName) {
    let templatePath = files.join(TEMPLATE_IMAGE_PATH, templateName);
    if (!files.exists(templatePath)) {
        return null;
    }

    let template = null;
    try {
        // 讀取本地模板圖片 (Read Template Image)
        template = images.read(templatePath);
        if (!template) return null;

        // 執行模板匹配 (Template Matching)
        let matchResult = images.matchTemplate(screen, template, {
            threshold: THRESHOLD,
            max: 1 // 僅尋找相似度最高的一個目標
        });

        // 解析匹配結果 (Parse Matching Result)
        if (matchResult && matchResult.matches && matchResult.matches.length > 0) {
            let bestMatch = matchResult.matches[0];
            return [
                bestMatch.point.x,
                bestMatch.point.y,
                template.getWidth(),
                template.getHeight(),
                bestMatch.similarity
            ];
        }
    } catch (e) {
        console.error("錯誤：無法載入或匹配模板 '" + templatePath + "': " + e);
    } finally {
        // 釋放模板圖片記憶體，防止記憶體溢出 (Recycle Memory)
        if (template) {
            template.recycle();
        }
    }
    return null;
}

/**
 * 模擬點擊指定座標。
 * 
 * @param {number} x 螢幕 X 座標
 * @param {number} y 螢幕 Y 座標
 * @param {number} t 點擊次數 (預設為 1)
 */
function clickAtPosition(x, y, t) {
    t = t || 1;
    for (let i = 0; i < t; i++) {
        click(x, y);
        sleep(100); // 點擊間隔微調
    }
    sleep(100); // 點擊後緩衝延遲
}

/**
 * 從指定起點 Y 座標滑動到終點 Y 座標。
 * 
 * @param {number} startX 起始 X 座標
 * @param {number} startY 起始 Y 座標
 * @param {number} targetY 目標 Y 座標
 * @param {number} duration 滑動持續時間（微秒）
 */
function swipeToY(startX, startY, targetY, duration) {
    duration = duration || 300;
    // 呼叫無障礙滑動 API: swipe(x1, y1, x2, y2, duration)
    swipe(startX, startY, startX, targetY, duration);
    sleep(100); // 滑動後的緩衝延遲
}

/**
 * 自動化控制主執行緒 (Main Thread Loop)
 */
function main() {
    // 取得手機螢幕實際寬度與高度 (Get Screen Dimensions)
    let width = device.width;
    let height = device.height;
    
    // 手機為全螢幕操作，故偏移座標皆為 0 (Offset for Absolute Screen Coordinates)
    let offsetX = 0;
    let offsetY = 0;

    log("Poker Fate 手機版自動化腳本啟動。目標 e 次數: " + TARGET_E_COUNT);

    while (isRunning) {
        // 1. 取得當前手機螢幕快照 (Capture Screen)
        let screen = captureScreen();
        if (!screen) {
            log("等待獲取螢幕畫面中...");
            sleep(1000);
            continue;
        }

        // 2. 偵錯自癒邏輯 (State Self-Healing Logic)
        if (failedAttemptsCounter >= MAX_FAILED_ATTEMPTS) {
            log("[自癒] 連續失敗，啟動全掃描...");
            let potentialStates = ['a', 'b', 'c', 'd_0', 'd_1', 'e'];
            for (let i = 0; i < potentialStates.length; i++) {
                let ps = potentialStates[i];
                if (findImageOnScreen(screen, ps + TEMPLATE_EXT)) {
                    currentState = (ps === 'd_0') ? 'd' : ps;
                    log("[自癒] 成功，切換至狀態: " + currentState);
                    failedAttemptsCounter = 0;
                    break;
                }
            }
            if (failedAttemptsCounter !== 0) {
                failedAttemptsCounter = 0; // 重置計數器避免卡死
            }
        }

        let matchedThisLoop = false;

        // 3. 狀態機邏輯 (State Machine Logic)
        
        // 狀態 a: 尋找 a.png
        if (currentState === 'a') {
            let res = findImageOnScreen(screen, "a" + TEMPLATE_EXT);
            if (res) {
                clickAtPosition(offsetX + res[0] + res[2]/2, offsetY + res[1] + res[3]/2);
                currentState = 'b';
                log(">>> 狀態切換: b");
                matchedThisLoop = true;
            }
        }

        // 狀態 b: 尋找 b.png
        else if (currentState === 'b') {
            let res = findImageOnScreen(screen, "b" + TEMPLATE_EXT);
            if (res) {
                clickAtPosition(offsetX + res[0] + res[2]/2, offsetY + res[1] + res[3]/2);
                currentState = 'c';
                log(">>> 狀態切換: c");
                matchedThisLoop = true;
            }
        }

        // 狀態 c: 尋找 c_0.png 且 c.png
        else if (currentState === 'c') {
            let resC0 = findImageOnScreen(screen, "c_0" + TEMPLATE_EXT);
            let resC = findImageOnScreen(screen, "c" + TEMPLATE_EXT);
            if (resC0 && resC) {
                clickAtPosition(offsetX + resC[0] + resC[2]/2, offsetY + resC[1] + resC[3]/2);
                log(">>> 狀態 c 觸發，等待 5 秒...");
                sleep(5000);
                currentState = 'd';
                log(">>> 狀態切換: d");
                matchedThisLoop = true;
            }
        }

        // 狀態 d: 優先偵測圖片 e，再執行 d_0 邏輯
        else if (currentState === 'd') {
            // 1) 優先偵測圖片 e
            let resE = findImageOnScreen(screen, "e" + TEMPLATE_EXT);
            if (resE) {
                eCounter++;
                log("!!! 偵測到圖片 e (目前計數: " + eCounter + "/" + TARGET_E_COUNT + ")");

                if (eCounter >= TARGET_E_COUNT) {
                    log("====================");
                    log("      任務完成       ");
                    log("====================");
                    toastLog("達成目標次數，腳本安全結束");
                    exit(); // 結束整個指令碼
                }

                // 點擊 e.png 中心並等待 10 秒
                clickAtPosition(offsetX + resE[0] + resE[2]/2, offsetY + resE[1] + resE[3]/2);
                log(">>> 點擊 e.png，等待 10 秒...");
                sleep(10000);
                matchedThisLoop = true;
            } 
            // 2) 若沒偵測到 e 或執行完 e 之後的下一次循環，偵測 d_0
            else {
                let resD0 = findImageOnScreen(screen, "d_0" + TEMPLATE_EXT);
                if (resD0) {
                    // 公式點擊：(左上_x + 長 * 900/1000, 左上_y + 寬 * 560/600)
                    let targetX = offsetX + width * 900 / 1000;
                    let targetY = offsetY + height * 560 / 600;
                    clickAtPosition(targetX, targetY);
                    currentState = 'd_1';
                    log(">>> 狀態切換: d_1");
                    matchedThisLoop = true;
                } else {
                    currentState = 'd';
                    // 不重置狀態，保持在 d
                }
            }
        }

        // 狀態 d_1: 尋找 d_1.png
        else if (currentState === 'd_1') {
            let res = findImageOnScreen(screen, "d_1" + TEMPLATE_EXT);
            if (res) {
                // 1. 點擊 d_1.png 中心
                let startX = offsetX + res[0] + res[2]/2;
                let startY = offsetY + res[1] + res[3]/2;
                clickAtPosition(startX, startY);
                
                // 2. 往上滑動至絕對螢幕座標 y=230 (手機端對齊 offsetY + 230)
                log(">>> 執行滑動動作至 y=" + (offsetY + 230));
                swipeToY(startX, startY, offsetY + 230, 300);
                
                // 3. 再次執行公式點擊
                let targetX = offsetX + width * 900 / 1000;
                let targetY = offsetY + height * 560 / 600;
                clickAtPosition(targetX, targetY);
                
                log(">>> 狀態 d_1 完成，等待 5 秒回到狀態 d");
                sleep(5000);
                currentState = 'd';
                matchedThisLoop = true;
            } else {
                currentState = 'd';
                matchedThisLoop = true;
            }
        }

        // 5. 更新失敗計數器
        failedAttemptsCounter = matchedThisLoop ? 0 : failedAttemptsCounter + 1;

        sleep(LOOP_DELAY);
    }
}

// --- 5. 啟動腳本執行緒 (Start Worker Thread) ---
// 自動化迴圈必須放在背景執行緒中執行，避免阻塞主執行緒
threads.start(function() {
    try {
        main();
    } catch (err) {
        console.error("執行緒拋出未預期錯誤: " + err);
    }
});

// 保持主程式不退出 (Keep script alive for event loops)
setInterval(function() {}, 1000);