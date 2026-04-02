# 給 Cursor 的開發指令 — 福貓計算機

請閱讀以下規格並照步驟完整開發「福貓計算機」專案。
**修改任何既有檔案前，請先建立 `.bak` 備份。**
**所有程式碼必須加上繁體中文逐行或逐段註解。**

---

## 專案基本資訊

- **專案路徑**：`C:\Users\User\Desktop\各種好用的PY\超強rules範本請備份使用\福貓計算機\`
- **使用者**：員工（內部人員）
- **目的**：員工選商品、輸入數量，立即計算可賺取的總獎金

---

## 系統架構

```
[ 老大電腦執行 ]
update_data.py
  → 讀取 .env 中的 Cookie
  → 帶 Cookie 登入福貓挖寶網
  → 抓取所有商品（名稱、編碼、售價）
  → 解析商品編碼中的獎金金額
  → 輸出 web/products.json

[ Vercel 免費雲端 / 本地預覽 ]
web/index.html + style.css + main.js
  → 讀取 products.json
  → 員工開啟網址即可使用
  → 支援手機與電腦（RWD）
```

---

## 目錄結構（需建立）

```
福貓計算機/
├── .env                  ← 已存在，請勿修改
├── .gitignore            ← 【新建】
├── debug.bat             ← 【更新】
├── requirements.txt      ← 【新建】
├── update_data.py        ← 【新建】爬蟲主程式
└── web/
    ├── index.html        ← 【新建】
    ├── style.css         ← 【新建】
    ├── main.js           ← 【新建】
    └── products.json     ← 由爬蟲生成，先建立空陣列 []
```

---

## Step 1：建立 Python 虛擬環境

在專案目錄下執行：
```
python -m venv venv
```

建立 `requirements.txt`，內容：
```
requests
python-dotenv
beautifulsoup4
```

安裝套件：
```
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 2：開發 `update_data.py`

### 2.1 .env 格式（請勿修改 .env，僅供參考）
```
FUMAO_COOKIES="使用者的 Cookie 字串"
```

### 2.2 核心邏輯

```python
# 使用 python-dotenv 讀取 .env
# 使用 requests.Session 帶 Cookie 爬取：
# https://reseller.luckycat.life/store/shopping/
# 對每個商品提取：名稱、商品編碼、售價
# 使用以下函式解析獎金：

import re

def parse_bonus(product_code: str) -> int:
    """從商品編碼解析每件獎金金額（新台幣）"""
    # 商品編碼範例：JU00027Y23D001M0219S01
    # 抓取 M 後面到 S01 前面的數字 → 0219 → 219
    match = re.search(r'M(\d+)S01', product_code)
    if match:
        return int(match.group(1))
    return 0
```

### 2.3 輸出格式：`web/products.json`

```json
[
  {
    "name": "Pures Select 南極冰鑽磷蝦油（30粒／盒）",
    "code": "JU00027Y23D001M0219S01",
    "price": 999,
    "bonus": 219
  }
]
```

### 2.4 技術規範
- 使用 Python 3.11+ 語法
- 多頁分頁請求使用 `asyncio.TaskGroup`
- 使用 Type Hint

---

## Step 3：開發前端網頁（`web/` 目錄）

### 3.1 設計規範

| 項目 | 規格 |
|------|------|
| 主題 | 深色（Dark Mode） |
| 字體 | Google Fonts：Inter 或 Noto Sans TC |
| 強調色 | 金色（獎金數字） |
| 字體單位 | **全部用 `rem`，禁止 `px` 字體** |
| RWD 斷點 | 手機 `768px`、平板 `1024px` |
| 手機按鈕 | 高度至少 `44px` |

### 3.2 `index.html` 頁面結構

```
頁面頭部
  └─ 標題：「福貓挖寶 獎金計算機」
  └─ 即時搜尋框

商品列表區（左側或上方）
  └─ 每個商品一張卡片，顯示：
      · 商品名稱
      · 商品編碼（小字灰色）
      · 每件獎金 XXX 元（金色大字）
      · 數量輸入框（min=1，預設=1）
      · 「加入計算」按鈕

結算區（右側或下方）
  └─ 已選商品清單（可個別移除）
  └─ 各項小計（獎金 × 數量）
  └─ 總獎金合計（超大金色字體）
  └─ 「清除全部」按鈕
```

### 3.3 `main.js` 邏輯需求

```javascript
// 1. fetch('products.json') 讀取資料
// 2. 動態渲染商品卡片
// 3. 搜尋框即時篩選（不需送出）
// 4. 「加入計算」→ 加入結算清單，數量可累加
// 5. 總獎金公式：= Σ (bonus × quantity)
// 6. 數字變動時加上平滑動畫
```

---

## Step 4：更新 `debug.bat`

覆蓋現有內容為：

```bat
@echo off
chcp 65001
echo =======================================
echo  福貓計算機 - 除錯模式
echo =======================================
echo.
echo [1] 執行爬蟲更新商品資料 (update_data.py)
echo [2] 啟動本地網頁預覽 (http://localhost:8000)
echo.
set /p choice=請輸入選項 (1 or 2)：

if "%choice%"=="1" (
    cd /d %~dp0
    call venv\Scripts\activate.bat
    python update_data.py
    echo.
    echo 完成！請檢查 web/products.json 是否正確生成。
)
if "%choice%"=="2" (
    cd /d %~dp0\web
    echo 正在啟動本地伺服器...
    python -m http.server 8000
)
pause
```

---

## Step 5：建立 `.gitignore`

```
.env
venv/
__pycache__/
*.pyc
*.bak
web/products.json
```

---

## 驗收標準（完成後請逐一確認）

- [ ] `venv` 虛擬環境建立成功，套件安裝無誤
- [ ] `update_data.py` 帶 Cookie 成功執行，生成正確格式的 `products.json`
- [ ] 獎金解析正確：`M0219S01` → `219`
- [ ] 網頁在手機和電腦排版正常，無字體跑版問題
- [ ] 搜尋功能即時運作
- [ ] 結算區總獎金計算正確
- [ ] `debug.bat` 執行後正常暫停（pause）
- [ ] `.env` 未被包含在任何可公開存取的位置

---

完成後請告知，由 PM 進行驗收測試。
