"""福貓挖寶經銷後台商品資料更新：讀 .env Cookie、依 kind1 分類 API 抓清單、再開商品頁補商品編碼、縮圖、方案選項（#prod_plan_select）、寫入 web/products.json。"""

from __future__ import annotations

# asyncio：非同步事件迴圈與 TaskGroup 平行請求
import asyncio
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 經銷站網址（與瀏覽器網址列一致）
BASE_URL = "https://reseller.luckycat.life"
# 輸出 JSON 相對於本檔案的路徑
OUTPUT_REL = "web/products.json"
# 單次 HTTP 請求逾時（秒）
REQUEST_TIMEOUT_SEC = 60
# 並行抓取商品詳情頁時的同時連線上限（避免一次打太猛被站台擋）
DETAIL_FETCH_CONCURRENCY = 12

# 詳情頁內商品相關圖檔（cloudfront editor 路徑）
_THUMB_URL_RE = re.compile(
    r'https://dxpqg5f7jnxq8\.cloudfront\.net/editor/[^"<>\s]+\.(?:jpg|jpeg|png|webp)',
    re.I,
)
# 方案選單內文「平均每盒( 2,270 )」：支援半形／全形括號
_PLAN_AVG_LABEL_RE = re.compile(
    r"\u5e73\u5747[^\(\（]*[\(\（]\s*([\d,]+)\s*[\)\）]",
)


def parse_bonus(product_code: str) -> int:
    """從商品編碼解析每件獎金金額（新台幣）。"""
    # 範例 M0219S01：中段數字 0219 → 219，業務規則為先 ×2 才是每件獎金
    match = re.search(r"M(\d+)S01", product_code)
    if match:
        return int(match.group(1)) * 2
    return 0


def clean_product_name(raw: str) -> str:
    """若名稱含 HTML 標籤則轉成純文字，否則去除首尾空白。"""
    if "<" not in raw:
        return raw.strip()
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def parse_sale_price_ntd(item: dict[str, Any]) -> int:
    """推算售價整數：優先 showprice，空或無效則用 normalprice（對齊前台顯示）。"""
    def to_int(v: Any) -> int | None:
        if v is None:
            return None
        s = str(v).strip().replace(",", "")
        if s in ("", "0", "0.0"):
            return None
        try:
            return int(float(s))
        except ValueError:
            return None

    p_show = to_int(item.get("showprice"))
    if p_show is not None:
        return p_show
    p_norm = to_int(item.get("normalprice"))
    if p_norm is not None:
        return p_norm
    return 0


def normalize_cookie_header(raw: str) -> str:
    """將 FUMAO_COOKIES 轉成 HTTP Cookie 標頭；支援 Netscape 匯出檔或瀏覽器複製字串。"""
    # 去除首尾空白與 .env 常見的引號包覆
    text = raw.strip().strip(chr(34)).strip(chr(39))
    if not text:
        return ""
    # Netscape 格式：檔首註解或含 Tab 欄位之多行文字
    if text.startswith("# Netscape") or (chr(10) in text and chr(9) in text and "Cookie" in text[:200]):
        pairs: list[str] = []
        for line in text.splitlines():
            ls = line.strip()
            if not ls or ls.startswith("#"):
                continue
            parts = ls.split(chr(9))
            if len(parts) >= 7:
                pairs.append(parts[5] + "=" + parts[6])
        return "; ".join(pairs)
    # 已是「名=值; 名=值」形式則直接回傳
    return text


def build_session() -> requests.Session:
    """建立 requests Session，並從環境變數帶入 Cookie 標頭。"""
    load_dotenv()
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        }
    )
    raw = os.getenv("FUMAO_COOKIES", "")
    if raw:
        cookie_header = normalize_cookie_header(raw)
        if cookie_header:
            session.headers["Cookie"] = cookie_header
    return session


def fetch_shopping_html(session: requests.Session) -> str:
    """抓取「挖寶首頁」HTML，用來解析 kind1 類別清單。

    重要原因：
    - 前端在首頁 HTML 內就有 `<div class='kind1' kind='31'>` 這種節點
    - 因此我們不用猜 API，就能拿到「有哪些 kind1 類別 id」並逐類抓取
    """
    url = f"{BASE_URL}/store/shopping/"
    r = session.get(url, timeout=REQUEST_TIMEOUT_SEC)
    r.raise_for_status()
    return r.text


def extract_kind1_ids_from_shopping_html(html: str) -> list[int]:
    """從首頁 HTML 解析出所有 kind1 類別 id（整數、去重、排序）。"""
    soup = BeautifulSoup(html, "html.parser")
    ids: set[int] = set()

    # 前端選單節點長這樣：<div class='kind1' kind='31'>...</div>
    for node in soup.select("div.kind1[kind]"):
        raw = (node.get("kind") or "").strip()
        if raw.isdigit():
            ids.add(int(raw))

    return sorted(ids)


def extract_kind1_labels_from_shopping_html(html: str) -> dict[int, str]:
    """從挖寶首頁 HTML 解析 kind1 類別 id → 顯示名稱（與官網左側選單一致，如 挖3C、挖好康）。"""
    soup = BeautifulSoup(html, "html.parser")
    labels: dict[int, str] = {}
    for node in soup.select("div.kind1[kind]"):
        raw = (node.get("kind") or "").strip()
        if not raw.isdigit():
            continue
        kid = int(raw)
        span = node.select_one("span.kind1_name")
        text = span.get_text(strip=True) if span else ""
        if text:
            labels[kid] = text
    return labels


def fetch_kind1_page_json(session: requests.Session, kind1_id: int, page: int) -> list[Any]:
    """抓取單一 kind1 類別的某一頁 JSON。

    這是你剛剛在 Network 找到的「真正商品清單」API 形式：
    - /store/shopping/prod_sort_api/kind1/{kind1_id}/{page}
    範例：
    - https://reseller.luckycat.life/store/shopping/prod_sort_api/kind1/31/1
    """
    url = f"{BASE_URL}/store/shopping/prod_sort_api/kind1/{kind1_id}/{page}"
    r = session.get(url, timeout=REQUEST_TIMEOUT_SEC)
    r.raise_for_status()
    return r.json()


def _comma_money_int(v: Any) -> int:
    """將 '27,000'、27000 或 0 轉成 int（無效則 0）。"""
    if v is None:
        return 0
    s = str(v).strip().replace(",", "")
    if not s:
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def extract_plans_from_detail_html(html: str) -> list[dict[str, Any]]:
    """從詳情頁 `select#prod_plan_select` 解析各方案（與官網「方案」下拉一致）。

    每個 option 帶 qty（件／盒數）、total／showprice（該方案總價）、選項文字內之「平均…(…)」為均價。
    """
    soup = BeautifulSoup(html, "html.parser")
    sel = soup.select_one("select#prod_plan_select")
    if not sel:
        return []
    out: list[dict[str, Any]] = []
    for opt in sel.find_all("option"):
        val = str(opt.get("value", "")).strip()
        if val in ("", "0"):
            continue
        qty_s = str(opt.get("qty", "0")).strip()
        if not qty_s or qty_s == "0":
            continue
        try:
            qty = int(qty_s)
        except ValueError:
            continue
        if qty <= 0:
            continue
        total = _comma_money_int(opt.get("total"))
        if total <= 0:
            total = _comma_money_int(opt.get("showprice"))
        text = opt.get_text(" ", strip=True) or ""
        avg = 0
        m = _PLAN_AVG_LABEL_RE.search(text)
        if m:
            avg = _comma_money_int(m.group(1))
        if avg <= 0 and qty > 0 and total > 0:
            avg = max(1, round(total / qty))
        out.append(
            {
                "qty": qty,
                "total": total,
                "avg": avg,
                "label": text,
            }
        )
    out.sort(key=lambda row: row["qty"])
    return out


def find_kind1_meta_block(api_payload: list[Any]) -> dict[str, Any] | None:
    """從 kind1 列表 API 回傳中找出帶有 prod 陣列的區塊（count/limit 用於分頁）。"""
    for block in api_payload:
        if isinstance(block, dict) and isinstance(block.get("prod"), list):
            return block
    return None


def extract_prod_rows(api_payload: list[Any]) -> list[dict[str, Any]]:
    """將 API 回傳的每一區塊內 prod 陣列展開成扁平商品列表。"""
    rows: list[dict[str, Any]] = []
    for block in api_payload:
        if not isinstance(block, dict):
            continue
        prod_list = block.get("prod")
        if not isinstance(prod_list, list):
            continue
        for one in prod_list:
            if isinstance(one, dict):
                rows.append(one)
    return rows


def fetch_prod_detail_fields(session: requests.Session, prod_no: str) -> dict[str, Any]:
    """從商品詳情頁解析商品編碼、縮圖、方案清單。

    編碼：#prod_id 區塊「商品編碼：」後英數字串。
    縮圖：cloudfront.net/editor/…（優先路徑含商品編號）。
    方案：select#prod_plan_select 內有效 option（跳過請選擇 qty=0）。
    失敗時 code／image 為空字串、plans 為 []。
    """
    prod_no = (prod_no or "").strip()
    empty: dict[str, Any] = {"code": "", "image": "", "plans": []}
    if not prod_no:
        return empty
    url = f"{BASE_URL}/store/shopping/prod/{prod_no}"
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT_SEC)
        r.raise_for_status()
    except requests.RequestException:
        return empty
    text = r.text
    match = re.search(
        r"\u5546\u54c1\u7de8\u78bc\s*[:：]\s*([A-Za-z0-9]+)",
        text,
    )
    code = match.group(1).strip() if match else ""
    hits = _THUMB_URL_RE.findall(text)
    image = ""
    if hits:
        for h in hits:
            if prod_no in h:
                image = h
                break
        if not image:
            image = hits[0]
    plans = extract_plans_from_detail_html(text)
    return {"code": code, "image": image, "plans": plans}


def rows_to_intermediate_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """依 API 的 prodid（商品編號）去重，先產生待補「商品編碼」的中繼結構。"""
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in rows:
        prod_no = str(item.get("prodid", "")).strip()
        if not prod_no or prod_no in seen:
            continue
        seen.add(prod_no)
        cat = str(item.get("_kind1_name", "")).strip()
        output.append(
            {
                "name": clean_product_name(str(item.get("prodname", ""))),
                # prod_no：對應網址 /store/shopping/prod/{prod_no}，即畫面上的「商品編號」
                "prod_no": prod_no,
                "price": parse_sale_price_ntd(item),
                # 與官網 kind1 名稱一致（同頁 HTML span.kind1_name）
                "category": cat or "未分類",
            }
        )
    return output


async def enrich_items_with_long_codes(
    session: requests.Session, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """並行開啟每個商品詳情頁，補上商品編碼與縮圖後輸出完整欄位。"""
    sem = asyncio.Semaphore(DETAIL_FETCH_CONCURRENCY)

    async def worker(idx: int, it: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        prod_no = str(it["prod_no"]).strip()
        async with sem:
            fields = await asyncio.to_thread(fetch_prod_detail_fields, session, prod_no)
        # 詳情頁失敗時退回 prod_no，bonus 可能為 0（仍保留可搜尋的主鍵）
        long_code = str(fields.get("code") or "").strip()
        code = long_code or prod_no
        cat = str(it.get("category", "")).strip() or "未分類"
        image_url = str(fields.get("image") or "").strip()
        plans = fields.get("plans")
        if not isinstance(plans, list):
            plans = []
        return idx, {
            "name": it["name"],
            "code": code,
            "price": it["price"],
            "bonus": parse_bonus(code),
            "category": cat,
            "image": image_url,
            "plans": plans,
        }

    pairs = await asyncio.gather(*(worker(i, it) for i, it in enumerate(items)))
    pairs.sort(key=lambda p: p[0])
    return [p[1] for p in pairs]


def resolve_output_path() -> Path:
    """回傳 web/products.json 的絕對路徑。"""
    return Path(__file__).resolve().parent / OUTPUT_REL


async def fetch_extra_kind1_pages(
    session: requests.Session, kind1_id: int, from_page: int, to_page: int
) -> list[list[Any]]:
    """使用 asyncio.TaskGroup 平行抓取 kind1 類別的多個分頁。"""
    if from_page > to_page:
        return []
    page_to_payload: dict[int, list[Any]] = {}

    async def one_page(page_num: int) -> None:
        # 在執行緒中執行同步 requests，避免阻塞事件迴圈
        payload = await asyncio.to_thread(fetch_kind1_page_json, session, kind1_id, page_num)
        page_to_payload[page_num] = payload

    async with asyncio.TaskGroup() as group:
        for p in range(from_page, to_page + 1):
            group.create_task(one_page(p))

    ordered: list[list[Any]] = []
    for p in range(from_page, to_page + 1):
        ordered.append(page_to_payload[p])
    return ordered


async def async_main() -> list[dict[str, Any]]:
    """逐 kind1 類別抓取商品並合併去重（B：依分類逐類抓）。"""
    session = build_session()

    # 1) 先從首頁 HTML 取得 kind1 類別 id 清單
    shopping_html = await asyncio.to_thread(fetch_shopping_html, session)
    kind1_ids = extract_kind1_ids_from_shopping_html(shopping_html)
    if not kind1_ids:
        return []

    kind_labels = extract_kind1_labels_from_shopping_html(shopping_html)
    all_rows: list[dict[str, Any]] = []

    def tag_rows_with_kind(rows: list[dict[str, Any]], kid: int, label: str) -> None:
        for row in rows:
            row["_kind1_id"] = kid
            row["_kind1_name"] = label

    # 2) 逐類別抓第 1 頁，取得 count/limit 以計算該類別的總頁數
    for kind1_id in kind1_ids:
        kind1_label = kind_labels.get(kind1_id, "").strip() or f"類別 {kind1_id}"
        first_payload = await asyncio.to_thread(fetch_kind1_page_json, session, kind1_id, 1)
        if not first_payload:
            continue
        meta_block = find_kind1_meta_block(first_payload)
        if not meta_block:
            continue

        # 這個 API 的 count/limit 可能是字串，因此統一用 str → int
        total_count = int(str(meta_block.get("count", "0")))
        per_page = int(meta_block.get("limit", 20))
        if per_page <= 0:
            per_page = 20
        total_pages = max(1, math.ceil(total_count / per_page))

        # 先吃第 1 頁的商品（標記所屬 kind1，供輸出 category）
        page_rows = extract_prod_rows(first_payload)
        tag_rows_with_kind(page_rows, kind1_id, kind1_label)
        all_rows.extend(page_rows)

        # 其餘分頁用 TaskGroup 平行抓（同一類別內）
        if total_pages >= 2:
            for payload in await fetch_extra_kind1_pages(session, kind1_id, 2, total_pages):
                extra = extract_prod_rows(payload)
                tag_rows_with_kind(extra, kind1_id, kind1_label)
                all_rows.extend(extra)

    # 3) 全部類別抓完後先去重，再逐筆開商品頁補「商品編碼」
    intermediate = rows_to_intermediate_items(all_rows)
    if not intermediate:
        return []
    return await enrich_items_with_long_codes(session, intermediate)


def main() -> None:
    """程式進入點：執行非同步流程並寫入 UTF-8 JSON。"""
    items = asyncio.run(async_main())
    out_path = resolve_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已寫入 {len(items)} 筆商品 → {out_path}")


if __name__ == "__main__":
    main()
