# -*- coding: utf-8 -*-
"""Write web/* under the folder that contains update_data.py (search from Desktop)."""
from pathlib import Path


def find_proj() -> Path:
    desk = Path.home() / "Desktop"
    for f in desk.rglob("update_data.py"):
        return f.parent
    raise FileNotFoundError("update_data.py not under Desktop")


def main() -> None:
    proj = find_proj()
    web = proj / "web"
    web.mkdir(parents=True, exist_ok=True)
    (web / "index.html").write_text(_INDEX, encoding="utf-8")
    (web / "style.css").write_text(_CSS, encoding="utf-8")
    (web / "main.js").write_text(_JS, encoding="utf-8")
    pj = web / "products.json"
    if not pj.exists():
        pj.write_text("[]\n", encoding="utf-8")
    # 複製本安裝腳本到專案根，方便日後重建前端檔案
    import shutil

    src = Path(__file__).resolve()
    dst = proj / "run_fumao_web.py"
    if src != dst:
        shutil.copy2(src, dst)
    print("OK", web)


_INDEX = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>福貓挖寶 獎金計算機</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="style.css" />
</head>
<body>
<header class="page-header">
<h1 class="page-title">福貓挖寶 獎金計算機</h1>
<label class="search-wrap">
<span class="visually-hidden">搜尋商品</span>
<input type="search" id="search-input" class="search-input" placeholder="即時搜尋商品名稱或編碼" autocomplete="off" />
</label>
</header>
<div class="layout">
<section class="panel products-panel">
<h2 class="panel-title">商品列表</h2>
<div id="product-list" class="product-list"></div>
<p id="products-empty" class="empty-hint" hidden>找不到符合條件的商品。</p>
</section>
<aside class="panel checkout-panel">
<h2 class="panel-title">結算</h2>
<ul id="cart-list" class="cart-list"></ul>
<p id="cart-empty" class="empty-hint">尚未加入任何商品。</p>
<div class="subtotal-block">
<div id="line-items" class="line-items"></div>
<div class="total-row">
<span class="total-label">總獎金合計</span>
<span id="total-bonus" class="total-bonus" aria-live="polite">0</span>
<span class="total-unit">元</span>
</div>
</div>
<button type="button" id="clear-all" class="btn btn-secondary">清除全部</button>
</aside>
</div>
<script src="main.js" defer></script>
</body>
</html>
"""

_CSS = """/* 深色主題；字體大小使用 rem */
:root {
  --bg: #0f1419;
  --bg-elevated: #1a222d;
  --border: #2d3748;
  --text: #e8eaed;
  --text-muted: #8b949e;
  --accent-gold: #e8c547;
  --accent-gold-dim: #b89b2e;
  --danger: #f56565;
  --font-sans: "Inter", "Noto Sans TC", system-ui, sans-serif;
  --transition-numbers: 0.35s ease-out;
}
*, *::before, *::after { box-sizing: border-box; }
html { font-size: 100%; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: var(--font-sans);
  font-size: 1rem;
  line-height: 1.5;
  color: var(--text);
  background: radial-gradient(ellipse at top, #1a2433 0%, var(--bg) 55%);
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.page-header { max-width: 72rem; margin: 0 auto; padding: 1.5rem 1rem 1rem; }
.page-title { margin: 0 0 1rem; font-size: 1.75rem; font-weight: 700; letter-spacing: 0.02em; }
.search-wrap { display: block; }
.search-input {
  width: 100%;
  max-width: 36rem;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  font-family: inherit;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
}
.search-input::placeholder { color: var(--text-muted); }
.search-input:focus { outline: 2px solid var(--accent-gold); outline-offset: 2px; }
.layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.25rem;
  max-width: 72rem;
  margin: 0 auto;
  padding: 0 1rem 2rem;
}
@media (min-width: 1024px) {
  .layout { grid-template-columns: 1fr 22rem; align-items: start; }
}
.panel {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1rem;
}
.panel-title { margin: 0 0 1rem; font-size: 1.125rem; font-weight: 600; }
.product-list { display: flex; flex-direction: column; gap: 0.75rem; }
.product-card {
  display: grid;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
}
.product-name { margin: 0; font-size: 1rem; font-weight: 500; }
.product-code { margin: 0; font-size: 0.8125rem; color: var(--text-muted); word-break: break-all; }
.bonus-line { margin: 0; font-size: 1.25rem; font-weight: 700; color: var(--accent-gold); }
.bonus-line .currency { font-size: 0.875rem; font-weight: 500; color: var(--accent-gold-dim); }
.card-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
.qty-input {
  width: 5rem;
  min-height: 2.75rem;
  padding: 0.35rem 0.5rem;
  font-size: 1rem;
  font-family: inherit;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 0.35rem;
}
.btn {
  min-height: 2.75rem;
  padding: 0.5rem 1rem;
  font-size: 1rem;
  font-family: inherit;
  font-weight: 600;
  border: none;
  border-radius: 0.35rem;
  cursor: pointer;
}
.btn-primary {
  color: #1a1508;
  background: linear-gradient(180deg, #f0d875, var(--accent-gold));
}
.btn-primary:hover { filter: brightness(1.05); }
.btn-secondary {
  width: 100%;
  margin-top: 0.75rem;
  color: var(--text);
  background: transparent;
  border: 1px solid var(--border);
}
.btn-secondary:hover { border-color: var(--accent-gold); color: var(--accent-gold); }
.empty-hint { margin: 0.5rem 0 0; font-size: 0.9375rem; color: var(--text-muted); }
.cart-list { list-style: none; margin: 0 0 1rem; padding: 0; }
.cart-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.35rem 0.75rem;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.9375rem;
}
.cart-item-name { grid-column: 1 / -1; font-weight: 500; }
.cart-meta { color: var(--text-muted); font-size: 0.8125rem; }
.cart-sub { text-align: right; color: var(--accent-gold); font-weight: 600; }
.btn-remove {
  grid-column: 1 / -1;
  justify-self: start;
  min-height: 2.75rem;
  padding: 0.25rem 0.65rem;
  font-size: 0.875rem;
  color: var(--danger);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  border-radius: 0.25rem;
}
.btn-remove:hover { border-color: var(--danger); }
.subtotal-block { padding-top: 0.5rem; }
.line-items { margin-bottom: 0.75rem; font-size: 0.875rem; color: var(--text-muted); }
.line-item-row { display: flex; justify-content: space-between; gap: 0.5rem; padding: 0.2rem 0; }
.total-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.35rem 0.5rem;
  padding: 0.75rem 0;
  border-top: 1px solid var(--border);
}
.total-label { font-size: 1rem; font-weight: 600; }
.total-bonus {
  margin-left: auto;
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--accent-gold);
  transition: color var(--transition-numbers), transform var(--transition-numbers);
}
.total-bonus.is-updated { transform: scale(1.04); }
.total-unit { font-size: 1rem; color: var(--accent-gold-dim); }
@media (max-width: 768px) {
  .btn, .qty-input { min-height: 2.75rem; }
  .page-title { font-size: 1.5rem; }
  .total-bonus { font-size: 2rem; }
}
"""

_JS = r"""(function () {
  "use strict";
  /* 福貓獎金計算機前端：fetch products.json、搜尋、購物車、總獎金 Σ(bonus×qty) */
  var allProducts = [];
  var cart = new Map();
  var elSearch = document.getElementById("search-input");
  var elProductList = document.getElementById("product-list");
  var elProductsEmpty = document.getElementById("products-empty");
  var elCartList = document.getElementById("cart-list");
  var elCartEmpty = document.getElementById("cart-empty");
  var elLineItems = document.getElementById("line-items");
  var elTotalBonus = document.getElementById("total-bonus");
  var elClearAll = document.getElementById("clear-all");

  async function loadProducts() {
    var res = await fetch("products.json", { cache: "no-store" });
    if (!res.ok) throw new Error("load fail");
    var data = await res.json();
    allProducts = Array.isArray(data) ? data : [];
  }

  function filterProducts(q) {
    var needle = q.trim().toLowerCase();
    if (!needle) return allProducts;
    return allProducts.filter(function (p) {
      var name = (p.name || "").toLowerCase();
      var code = (p.code || "").toLowerCase();
      return name.indexOf(needle) !== -1 || code.indexOf(needle) !== -1;
    });
  }

  function createProductCard(p) {
    var card = document.createElement("article");
    card.className = "product-card";
    card.dataset.code = p.code;
    var name = document.createElement("h3");
    name.className = "product-name";
    name.textContent = p.name || "（無名稱）";
    var code = document.createElement("p");
    code.className = "product-code";
    code.textContent = p.code || "";
    var bonusLine = document.createElement("p");
    bonusLine.className = "bonus-line";
    bonusLine.innerHTML = "每件獎金 <strong>" + formatInt(p.bonus) + "</strong> <span class=\"currency\">元</span>";
    var actions = document.createElement("div");
    actions.className = "card-actions";
    var qty = document.createElement("input");
    qty.type = "number";
    qty.className = "qty-input";
    qty.min = "1";
    qty.value = "1";
    qty.setAttribute("aria-label", (p.name || "") + " 數量");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-primary";
    btn.textContent = "加入計算";
    btn.addEventListener("click", function () {
      var n = Math.max(1, parseInt(qty.value, 10) || 1);
      addToCart(p.code, n);
      qty.value = "1";
    });
    actions.appendChild(qty);
    actions.appendChild(btn);
    card.appendChild(name);
    card.appendChild(code);
    card.appendChild(bonusLine);
    card.appendChild(actions);
    return card;
  }

  function renderProductList() {
    var q = elSearch ? elSearch.value : "";
    var list = filterProducts(q);
    elProductList.innerHTML = "";
    if (list.length === 0) {
      elProductsEmpty.hidden = false;
      return;
    }
    elProductsEmpty.hidden = true;
    var frag = document.createDocumentFragment();
    list.forEach(function (p) { frag.appendChild(createProductCard(p)); });
    elProductList.appendChild(frag);
  }

  function addToCart(code, qty) {
    var product = allProducts.find(function (x) { return x.code === code; });
    if (!product) return;
    var prev = cart.get(code) || 0;
    cart.set(code, prev + qty);
    renderCart();
  }

  function removeFromCart(code) {
    cart.delete(code);
    renderCart();
  }

  function computeTotalBonus() {
    var sum = 0;
    cart.forEach(function (qty, code) {
      var product = allProducts.find(function (x) { return x.code === code; });
      if (product) sum += product.bonus * qty;
    });
    return sum;
  }

  function formatInt(n) {
    return Math.round(n).toLocaleString("zh-TW");
  }

  function setTotalDisplay(total) {
    elTotalBonus.textContent = formatInt(total);
    elTotalBonus.classList.remove("is-updated");
    void elTotalBonus.offsetWidth;
    elTotalBonus.classList.add("is-updated");
    window.setTimeout(function () { elTotalBonus.classList.remove("is-updated"); }, 400);
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function renderCart() {
    elCartList.innerHTML = "";
    elLineItems.innerHTML = "";
    if (cart.size === 0) {
      elCartEmpty.hidden = false;
      setTotalDisplay(0);
      return;
    }
    elCartEmpty.hidden = true;
    var frag = document.createDocumentFragment();
    var lineFrag = document.createDocumentFragment();
    cart.forEach(function (qty, code) {
      var product = allProducts.find(function (x) { return x.code === code; });
      if (!product) return;
      var sub = product.bonus * qty;
      var li = document.createElement("li");
      li.className = "cart-item";
      var title = document.createElement("div");
      title.className = "cart-item-name";
      title.textContent = product.name;
      var meta = document.createElement("div");
      meta.className = "cart-meta";
      meta.textContent = product.code + " · 每件 " + formatInt(product.bonus) + " 元 × " + qty;
      var subEl = document.createElement("div");
      subEl.className = "cart-sub";
      subEl.textContent = formatInt(sub) + " 元";
      var rm = document.createElement("button");
      rm.type = "button";
      rm.className = "btn-remove";
      rm.textContent = "移除此項";
      rm.addEventListener("click", function () { removeFromCart(code); });
      li.appendChild(title);
      li.appendChild(meta);
      li.appendChild(subEl);
      li.appendChild(rm);
      frag.appendChild(li);
      var row = document.createElement("div");
      row.className = "line-item-row";
      row.innerHTML = "<span>" + escapeHtml(product.name) + " × " + qty + "</span><span>" + formatInt(sub) + " 元</span>";
      lineFrag.appendChild(row);
    });
    elCartList.appendChild(frag);
    elLineItems.appendChild(lineFrag);
    setTotalDisplay(computeTotalBonus());
  }

  async function init() {
    try {
      await loadProducts();
    } catch (e) {
      elProductList.innerHTML = "<p class=\"empty-hint\">載入失敗，請先執行 update_data.py 產生 products.json。</p>";
      return;
    }
    renderProductList();
    if (elSearch) {
      elSearch.addEventListener("input", function () { renderProductList(); });
    }
    elClearAll.addEventListener("click", function () {
      cart.clear();
      renderCart();
    });
  }

  init();
})();
"""


if __name__ == "__main__":
    main()
