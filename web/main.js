(function () {
  "use strict";
  /* 福貓挖寶 獎金計算機（前端）：分類、分頁、方案選單（與官網 prod_plan_select）、套數／單一價格、結算 */

  var allProducts = [];
  /* 結算：依加入時所選「獎金比例」分三格；key = code 或 code::p{方案索引} */
  var RATIO_ORDER = ["100", "50", "25"];
  var RATIO_MULT = { "100": 1, "50": 0.5, "25": 0.25 };
  var carts = {
    "100": new Map(),
    "50": new Map(),
    "25": new Map(),
  };

  /* v2：舊鍵 fumao-page-size 曾記 48 等，會蓋掉預設 5；改鍵後一律以每頁 5 為首次默認 */
  var LS_PAGE_SIZE = "fumao-page-size-v2";
  var LS_BONUS_RATIO = "fumao-bonus-ratio";
  var LS_FULL_ATTENDANCE = "fumao-full-attendance";
  var selectedCategory = "all";
  var currentPage = 1;

  var elSearch = document.getElementById("search-input");
  var elPageSize = document.getElementById("page-size-select");
  var elProductsStats = document.getElementById("products-stats");
  var elCategoryBar = document.getElementById("category-bar");
  var elProductList = document.getElementById("product-list");
  var elProductsEmpty = document.getElementById("products-empty");
  var elPaginationBar = document.getElementById("pagination-bar");
  var elCheckoutSections = document.getElementById("checkout-sections");
  var elCartEmptyGlobal = document.getElementById("cart-empty-global");
  var elTotalRevenue = document.getElementById("total-revenue");
  var elTotalBonus = document.getElementById("total-bonus");
  var elFullAttendanceCheck = document.getElementById("full-attendance-check");
  var elFullAttendanceBlock = document.getElementById("full-attendance-bonus-block");
  var elFullAttendanceBonus = document.getElementById("full-attendance-bonus");
  var elClearAll = document.getElementById("clear-all");

  var CART_PLAN_SEP = "::p";

  /* M 與 S01 之間數字先 ×2 才是每件獎金；再由獎金比例（100/50/25）折算實得 */
  function parseBonusFromCode(code) {
    var s = String(code || "");
    var m = s.match(/M(\d+)S01/);
    if (!m) return null;
    var n = parseInt(m[1], 10);
    if (isNaN(n)) return null;
    return n * 2;
  }

  function getUnitBonus(p) {
    var fromCode = parseBonusFromCode(p.code);
    if (fromCode !== null) return fromCode;
    var b = Number(p.bonus);
    return isNaN(b) ? 0 : b;
  }

  function getProductCategory(p) {
    var c = p && p.category != null ? String(p.category).trim() : "";
    return c || "未分類";
  }

  function productHasPlans(p) {
    return !!(p && Array.isArray(p.plans) && p.plans.length);
  }

  function makeCartKey(code, planIndex) {
    if (planIndex == null || planIndex < 0) return String(code);
    return String(code) + CART_PLAN_SEP + String(planIndex);
  }

  function parseCartKey(key) {
    var s = String(key);
    var i = s.lastIndexOf(CART_PLAN_SEP);
    if (i === -1) return { code: s, planIndex: -1 };
    var idx = parseInt(s.slice(i + CART_PLAN_SEP.length), 10);
    if (isNaN(idx)) return { code: s, planIndex: -1 };
    return { code: s.slice(0, i), planIndex: idx };
  }

  function getSelectedRatioKey() {
    var el = document.querySelector('input[name="bonus-ratio"]:checked');
    var v = el ? el.value : "100";
    return RATIO_MULT[v] != null ? v : "100";
  }

  function getRatioMultiplier(ratioKey) {
    return RATIO_MULT[ratioKey] != null ? RATIO_MULT[ratioKey] : 1;
  }

  function cartHasAnyItem() {
    return RATIO_ORDER.some(function (k) {
      return carts[k].size > 0;
    });
  }

  function refreshAllCardBonusPreviews() {
    document.querySelectorAll("article.product-card").forEach(function (card) {
      var code = card.dataset.code;
      var p = allProducts.find(function (x) {
        return x.code === code;
      });
      if (p) updateCardPreview(card, p);
    });
  }

  function getPlanFromCard(card, p) {
    var sel = card.querySelector(".plan-select");
    if (!productHasPlans(p) || !sel) return null;
    var idx = parseInt(sel.value, 10);
    if (isNaN(idx) || !p.plans[idx]) return p.plans[0];
    return p.plans[idx];
  }

  function getPageSize() {
    if (!elPageSize) return 48;
    var v = parseInt(elPageSize.value, 10);
    return isFinite(v) && v > 0 ? v : 48;
  }

  function updateProductsStats(filteredTotal, pageSize) {
    if (!elProductsStats) return;
    if (filteredTotal === 0) {
      elProductsStats.textContent = "已載入 " + allProducts.length + " 筆；目前篩選 0 筆。";
      return;
    }
    var ps = pageSize >= 99999 ? filteredTotal : pageSize;
    var totalPages = Math.max(1, Math.ceil(filteredTotal / Math.max(1, ps)));
    var start = (currentPage - 1) * ps + 1;
    var end = Math.min(filteredTotal, currentPage * ps);
    var perLabel = pageSize >= 99999 ? "全部" : String(pageSize);
    elProductsStats.textContent =
      "已載入 " +
      allProducts.length +
      " 筆商品；篩選後 " +
      filteredTotal +
      " 筆；本頁第 " +
      start +
      "–" +
      end +
      " 筆（每頁 " +
      perLabel +
      "；第 " +
      currentPage +
      "/" +
      totalPages +
      " 頁）。";
  }

  /* 營業額與獎金：無方案時 bundles=數量（件）；有方案時 bundles=套數（該方案買幾次） */
  function lineRevenueBonus(product, planIndex, bundles) {
    var n = Math.max(1, bundles);
    if (planIndex >= 0 && product.plans && product.plans[planIndex]) {
      var pl = product.plans[planIndex];
      var total = Number(pl.total);
      var pq = Number(pl.qty);
      if (!isFinite(total)) total = 0;
      if (!isFinite(pq)) pq = 0;
      return {
        rev: total * n,
        bon: getUnitBonus(product) * pq * n,
      };
    }
    return {
      rev: Number(product.price) * n,
      bon: getUnitBonus(product) * n,
    };
  }

  function refreshCardPriceLine(card, p) {
    var line = card.querySelector(".price-line-dynamic");
    if (!line) return;
    var pl = getPlanFromCard(card, p);
    if (pl) {
      line.innerHTML =
        "方案總額 <strong>" +
        formatInt(pl.total) +
        "</strong> 元（均 <strong>" +
        formatInt(pl.avg) +
        "</strong> 元／單位）";
    } else {
      line.innerHTML =
        "單價 <strong>" +
        formatInt(p.price) +
        '</strong> <span class="currency">元</span>';
    }
  }

  function updateCardPreview(card, p) {
    var qtyEl = card.querySelector(".qty-input");
    var n = Math.max(1, parseInt(qtyEl.value, 10) || 1);
    var sel = card.querySelector(".plan-select");
    var planIdx = sel ? parseInt(sel.value, 10) : -1;
    if (isNaN(planIdx)) planIdx = -1;
    var lb = lineRevenueBonus(p, productHasPlans(p) ? planIdx : -1, n);
    var elRev = card.querySelector("[data-preview-revenue]");
    var elBon = card.querySelector("[data-preview-bonus]");
    var rmul = getRatioMultiplier(getSelectedRatioKey());
    if (elRev) elRev.textContent = formatInt(lb.rev);
    if (elBon) elBon.textContent = formatInt(lb.bon * rmul);
    refreshCardPreviewHint(card, p);
  }

  /* 預覽區小字：有方案時說明為「總價×套數」「獎金×件數」 */
  function refreshCardPreviewHint(card, p) {
    var hint = card.querySelector("[data-preview-hint]");
    if (!hint) return;
    var pct = getSelectedRatioKey() + "%";
    if (productHasPlans(p)) {
      hint.textContent =
        "營業額＝方案總額×套數；獎金＝每件獎金×（方案件數×套數）。預覽獎金已依「你的獎金比例」(" +
        pct +
        ") 折算，營業額不變。加入後會列入對應比例結算區。";
    } else {
      hint.textContent =
        "營業額＝單價×數量；獎金＝每件獎金×數量。預覽獎金已依「你的獎金比例」(" +
        pct +
        ") 折算，營業額不變。加入後會列入對應比例結算區。";
    }
  }

  function collectCategories() {
    var seen = Object.create(null);
    allProducts.forEach(function (p) {
      seen[getProductCategory(p)] = true;
    });
    var keys = Object.keys(seen);
    keys.sort(function (a, b) {
      if (a === "未分類") return 1;
      if (b === "未分類") return -1;
      return a.localeCompare(b, "zh-Hant");
    });
    return keys;
  }

  async function loadProducts() {
    var res = await fetch("products.json", { cache: "no-store" });
    if (!res.ok) throw new Error("load fail");
    var data = await res.json();
    allProducts = Array.isArray(data) ? data : [];
  }

  function filterProductsBySearch(q) {
    var needle = q.trim().toLowerCase();
    if (!needle) return allProducts.slice();
    return allProducts.filter(function filtering(p) {
      var name = (p.name || "").toLowerCase();
      var code = (p.code || "").toLowerCase();
      return name.indexOf(needle) !== -1 || code.indexOf(needle) !== -1;
    });
  }

  function getFilteredList() {
    var q = elSearch ? elSearch.value : "";
    var list = filterProductsBySearch(q);
    if (selectedCategory === "all") return list;
    return list.filter(function (p) {
      return getProductCategory(p) === selectedCategory;
    });
  }

  function renderCategoryBar() {
    if (!elCategoryBar) return;
    elCategoryBar.innerHTML = "";
    var frag = document.createDocumentFragment();

    function addChip(label, value) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "category-chip" + (selectedCategory === value ? " is-active" : "");
      btn.textContent = label;
      btn.setAttribute("aria-pressed", selectedCategory === value ? "true" : "false");
      btn.addEventListener("click", function () {
        selectedCategory = value;
        currentPage = 1;
        renderCategoryBar();
        renderProductList();
      });
      frag.appendChild(btn);
    }

    addChip("全部", "all");
    collectCategories().forEach(function (c) {
      addChip(c, c);
    });
    elCategoryBar.appendChild(frag);
  }

  function renderPagination(totalPages, totalCount) {
    if (!elPaginationBar) return;
    if (totalCount === 0) {
      elPaginationBar.hidden = true;
      elPaginationBar.innerHTML = "";
      return;
    }
    elPaginationBar.hidden = false;
    elPaginationBar.innerHTML = "";

    var prev = document.createElement("button");
    prev.type = "button";
    prev.className = "btn page-btn";
    prev.textContent = "上一頁";
    prev.disabled = currentPage <= 1;
    prev.addEventListener("click", function () {
      currentPage = Math.max(1, currentPage - 1);
      renderProductList();
    });

    var pagesWrap = document.createElement("div");
    pagesWrap.className = "pagination-pages";
    if (totalPages > 1) {
      var maxBtns = 11;
      var half = Math.floor(maxBtns / 2);
      var start = Math.max(1, currentPage - half);
      var end = Math.min(totalPages, start + maxBtns - 1);
      start = Math.max(1, end - maxBtns + 1);
      for (var pi = start; pi <= end; pi++) {
        var pb = document.createElement("button");
        pb.type = "button";
        pb.className = "btn page-btn page-num-btn" + (pi === currentPage ? " is-current-page" : "");
        pb.textContent = String(pi);
        if (pi === currentPage) {
          pb.setAttribute("aria-current", "page");
          pb.disabled = true;
        }
        (function (pageNum) {
          pb.addEventListener("click", function () {
            currentPage = pageNum;
            renderProductList();
          });
        })(pi);
        pagesWrap.appendChild(pb);
      }
    }

    var info = document.createElement("span");
    info.className = "pagination-info";
    info.textContent = "第 " + currentPage + " / " + totalPages + " 頁（共 " + totalCount + " 筆）";

    var next = document.createElement("button");
    next.type = "button";
    next.className = "btn page-btn";
    next.textContent = "下一頁";
    next.disabled = currentPage >= totalPages;
    next.addEventListener("click", function () {
      currentPage = Math.min(totalPages, currentPage + 1);
      renderProductList();
    });

    elPaginationBar.appendChild(prev);
    elPaginationBar.appendChild(pagesWrap);
    elPaginationBar.appendChild(info);
    elPaginationBar.appendChild(next);
  }

  function buildProductThumb(p) {
    var wrap = document.createElement("div");
    wrap.className = "product-thumb";
    var url = p && p.image ? String(p.image).trim() : "";
    if (url) {
      var img = document.createElement("img");
      img.src = url;
      img.alt = p && p.name ? String(p.name) : "";
      img.loading = "lazy";
      img.decoding = "async";
      img.addEventListener("error", function () {
        img.remove();
        wrap.className = "product-thumb product-thumb--empty";
        wrap.textContent = "無圖";
      });
      wrap.appendChild(img);
    } else {
      wrap.className = "product-thumb product-thumb--empty";
      wrap.textContent = "無圖";
    }
    return wrap;
  }

  function createProductCard(p) {
    var card = document.createElement("article");
    card.className = "product-card";
    card.dataset.code = p.code != null ? String(p.code) : "";

    var body = document.createElement("div");
    body.className = "product-card-body";

    var name = document.createElement("h3");
    name.className = "product-name";
    name.textContent = p.name || "（無名稱）";
    body.appendChild(name);

    var planSelect = null;
    if (productHasPlans(p)) {
      var planRow = document.createElement("div");
      planRow.className = "plan-row";
      var planLblEl = document.createElement("label");
      planLblEl.className = "plan-label";
      planLblEl.textContent = "方案";
      planSelect = document.createElement("select");
      planSelect.className = "plan-select";
      planSelect.setAttribute("aria-label", (p.name || "") + " 方案");
      p.plans.forEach(function (pl, idx) {
        var o = document.createElement("option");
        o.value = String(idx);
        var optLabel = pl.label || "件數 " + pl.qty + " · 總額 " + formatInt(pl.total) + " 元";
        o.textContent = optLabel;
        o.title = optLabel;
        planSelect.appendChild(o);
      });
      planSelect.addEventListener("change", function () {
        refreshCardPriceLine(card, p);
        updateCardPreview(card, p);
      });
      planRow.appendChild(planLblEl);
      planRow.appendChild(planSelect);
      body.appendChild(planRow);
    }

    var priceLine = document.createElement("p");
    priceLine.className = "price-line price-line-dynamic";
    body.appendChild(priceLine);

    var bonusLine = document.createElement("p");
    bonusLine.className = "bonus-line";
    bonusLine.innerHTML =
      "每件獎金 <strong>" + formatInt(getUnitBonus(p)) + '</strong> <span class="currency">元</span>';
    body.appendChild(bonusLine);

    var preview = document.createElement("div");
    preview.className = "card-preview";
    preview.setAttribute("aria-live", "polite");
    var initIdx = planSelect ? parseInt(planSelect.value, 10) || 0 : -1;
    var initLb = lineRevenueBonus(p, productHasPlans(p) ? initIdx : -1, 1);
    preview.innerHTML =
      '<p class="preview-hint" data-preview-hint></p>' +
      '<div class="preview-rev">營業額：<strong data-preview-revenue>' +
      formatInt(initLb.rev) +
      "</strong> 元</div>" +
      '<div class="preview-bonus">獎金：<strong data-preview-bonus>' +
      formatInt(initLb.bon) +
      "</strong> 元</div>";

    var actions = document.createElement("div");
    actions.className = "card-actions";
    var qty = document.createElement("input");
    qty.type = "number";
    qty.className = "qty-input";
    qty.min = "1";
    qty.value = "1";
    if (productHasPlans(p)) {
      qty.setAttribute("aria-label", (p.name || "") + " 套數（同款方案買幾次）");
    } else {
      qty.setAttribute("aria-label", (p.name || "") + " 數量");
    }
    qty.addEventListener("input", function () {
      updateCardPreview(card, p);
    });

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-primary";
    btn.textContent = "加入計算";
    btn.addEventListener("click", function () {
      var n = Math.max(1, parseInt(qty.value, 10) || 1);
      var pIdx = -1;
      if (planSelect) pIdx = parseInt(planSelect.value, 10) || 0;
      addToCart(p.code, n, planSelect ? pIdx : -1);
      qty.value = "1";
      updateCardPreview(card, p);
    });

    actions.appendChild(qty);
    actions.appendChild(btn);

    body.appendChild(preview);
    body.appendChild(actions);

    card.appendChild(buildProductThumb(p));
    card.appendChild(body);

    refreshCardPriceLine(card, p);
    refreshCardPreviewHint(card, p);
    updateCardPreview(card, p);
    return card;
  }

  function renderProductList() {
    var list = getFilteredList();
    var totalCount = list.length;
    var pageSize = getPageSize();
    var effectiveSize = pageSize >= 99999 ? totalCount : pageSize;
    if (effectiveSize <= 0) effectiveSize = 32;
    var totalPages = Math.max(1, Math.ceil(totalCount / effectiveSize));

    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    updateProductsStats(totalCount, pageSize);

    elProductList.innerHTML = "";
    if (totalCount === 0) {
      elProductsEmpty.hidden = false;
      renderPagination(1, 0);
      return;
    }
    elProductsEmpty.hidden = true;

    var start = (currentPage - 1) * effectiveSize;
    var pageSlice = list.slice(start, start + effectiveSize);

    var frag = document.createDocumentFragment();
    pageSlice.forEach(function eachProduct(p) {
      try {
        frag.appendChild(createProductCard(p));
      } catch (err) {
        console.error("商品卡渲染失敗", p && p.code, err);
        var errP = document.createElement("p");
        errP.className = "empty-hint";
        errP.textContent =
          "（無法顯示此筆：" + (p && p.name ? String(p.name).slice(0, 80) : p && p.code ? p.code : "未知") + "）";
        frag.appendChild(errP);
      }
    });
    elProductList.appendChild(frag);
    renderPagination(totalPages, totalCount);
  }

  function addToCart(code, bundles, planIndex) {
    planIndex = planIndex == null ? -1 : planIndex;
    var product = allProducts.find(function (x) {
      return x.code === code;
    });
    if (!product) return;
    var ratioKey = getSelectedRatioKey();
    var m = carts[ratioKey];
    if (!m) return;
    var key = makeCartKey(code, planIndex);
    var prev = m.get(key) || 0;
    m.set(key, prev + bundles);
    renderCart();
  }

  function setCartQty(ratioKey, key, qty) {
    var n = Math.max(1, parseInt(qty, 10) || 1);
    var m = carts[ratioKey];
    if (!m) return;
    var parts = parseCartKey(key);
    if (!allProducts.some(function (x) {
      return x.code === parts.code;
    })) return;
    m.set(key, n);
    renderCart();
  }

  function removeFromCart(ratioKey, key) {
    var m = carts[ratioKey];
    if (!m) return;
    m.delete(key);
    renderCart();
  }

  function computeGrandRevenue() {
    var sum = 0;
    RATIO_ORDER.forEach(function (rk) {
      carts[rk].forEach(function (bundles, key) {
        var parts = parseCartKey(key);
        var product = allProducts.find(function (x) {
          return x.code === parts.code;
        });
        if (!product) return;
        sum += lineRevenueBonus(product, parts.planIndex, bundles).rev;
      });
    });
    return sum;
  }

  function computeGrandBonusScaled() {
    var sum = 0;
    RATIO_ORDER.forEach(function (rk) {
      var mult = getRatioMultiplier(rk);
      carts[rk].forEach(function (bundles, key) {
        var parts = parseCartKey(key);
        var product = allProducts.find(function (x) {
          return x.code === parts.code;
        });
        if (!product) return;
        var lb = lineRevenueBonus(product, parts.planIndex, bundles);
        sum += lb.bon * mult;
      });
    });
    return sum;
  }

  function formatInt(n) {
    var x = Number(n);
    if (!isFinite(x)) return "—";
    return Math.round(x).toLocaleString("zh-TW");
  }

  function pulseEl(el) {
    if (!el) return;
    el.classList.remove("is-updated");
    void el.offsetWidth;
    el.classList.add("is-updated");
    window.setTimeout(function () {
      el.classList.remove("is-updated");
    }, 400);
  }

  /* 含全勤後獎金＝「總獎金合計（各比例實得加總）」×1.25 */
  function updateFullAttendanceDisplay(baseBonus) {
    if (!elFullAttendanceBlock || !elFullAttendanceBonus || !elFullAttendanceCheck) return;
    if (elFullAttendanceCheck.checked) {
      elFullAttendanceBlock.hidden = false;
      var fa = Math.round(Number(baseBonus) * 1.25);
      elFullAttendanceBonus.textContent = formatInt(fa);
      pulseEl(elFullAttendanceBonus);
    } else {
      elFullAttendanceBlock.hidden = true;
    }
  }

  function updateTotalsDisplay() {
    var base = computeGrandBonusScaled();
    elTotalRevenue.textContent = formatInt(computeGrandRevenue());
    elTotalBonus.textContent = formatInt(base);
    pulseEl(elTotalRevenue);
    pulseEl(elTotalBonus);
    updateFullAttendanceDisplay(base);
  }

  function renderCart() {
    if (!cartHasAnyItem()) {
      if (elCheckoutSections) elCheckoutSections.hidden = true;
      if (elCartEmptyGlobal) elCartEmptyGlobal.hidden = false;
      elTotalRevenue.textContent = "0";
      elTotalBonus.textContent = "0";
      updateFullAttendanceDisplay(0);
      RATIO_ORDER.forEach(function (rk) {
        var ul = document.getElementById("cart-list-" + rk);
        var hint = document.getElementById("cart-hint-" + rk);
        if (ul) ul.innerHTML = "";
        if (hint) hint.hidden = true;
        var srev = document.getElementById("sub-revenue-" + rk);
        var sbon = document.getElementById("sub-bonus-" + rk);
        if (srev) srev.textContent = "0";
        if (sbon) sbon.textContent = "0";
      });
      return;
    }

    if (elCheckoutSections) elCheckoutSections.hidden = false;
    if (elCartEmptyGlobal) elCartEmptyGlobal.hidden = true;

    RATIO_ORDER.forEach(function (ratioKey) {
      var map = carts[ratioKey];
      var mult = getRatioMultiplier(ratioKey);
      var ul = document.getElementById("cart-list-" + ratioKey);
      var hint = document.getElementById("cart-hint-" + ratioKey);
      var subRevEl = document.getElementById("sub-revenue-" + ratioKey);
      var subBonEl = document.getElementById("sub-bonus-" + ratioKey);
      if (!ul) return;
      ul.innerHTML = "";

      if (map.size === 0) {
        if (hint) hint.hidden = false;
        if (subRevEl) subRevEl.textContent = "0";
        if (subBonEl) subBonEl.textContent = "0";
        return;
      }
      if (hint) hint.hidden = true;

      var frag = document.createDocumentFragment();
      var secRev = 0;
      var secBonScaled = 0;

      map.forEach(function eachEntry(bundles, key) {
        var parts = parseCartKey(key);
        var product = allProducts.find(function (x) {
          return x.code === parts.code;
        });
        if (!product) return;

        var lb = lineRevenueBonus(product, parts.planIndex, bundles);
        var bonScaled = lb.bon * mult;

        secRev += lb.rev;
        secBonScaled += bonScaled;

        var li = document.createElement("li");
        li.className = "cart-item";

        var top = document.createElement("div");
        top.className = "cart-item-top";

        var title = document.createElement("div");
        title.className = "cart-item-name";
        title.textContent = product.name;

        var qtyWrap = document.createElement("div");
        qtyWrap.className = "cart-qty-wrap";

        var qtyLabel = document.createElement("label");
        qtyLabel.className = "visually-hidden";
        qtyLabel.textContent = parts.planIndex >= 0 ? product.name + " 套數" : product.name + " 數量";
        var qtyIn = document.createElement("input");
        qtyIn.type = "number";
        qtyIn.className = "cart-qty";
        qtyIn.min = "1";
        qtyIn.value = String(bundles);
        qtyIn.setAttribute("aria-label", (product.name || "") + (parts.planIndex >= 0 ? " 套數" : " 數量"));
        qtyIn.addEventListener("change", function () {
          setCartQty(ratioKey, key, qtyIn.value);
        });

        qtyWrap.appendChild(qtyLabel);
        qtyWrap.appendChild(qtyIn);
        top.appendChild(title);
        top.appendChild(qtyWrap);

        var rm = document.createElement("button");
        rm.type = "button";
        rm.className = "btn-remove";
        rm.textContent = "移除此項";
        rm.addEventListener("click", function () {
          removeFromCart(ratioKey, key);
        });

        li.appendChild(top);
        li.appendChild(rm);
        frag.appendChild(li);
      });

      ul.appendChild(frag);
      if (subRevEl) subRevEl.textContent = formatInt(secRev);
      if (subBonEl) subBonEl.textContent = formatInt(secBonScaled);
    });
    updateTotalsDisplay();
  }

  async function init() {
    try {
      await loadProducts();
    } catch (e) {
      elProductList.innerHTML =
        '<p class="empty-hint">載入失敗，請先執行 update_data.py 產生 products.json。</p>';
      return;
    }
    renderCategoryBar();
    if (elPageSize) {
      var allowed = ["5", "16", "32", "48", "96", "99999"];
      var saved = localStorage.getItem(LS_PAGE_SIZE);
      if (saved && allowed.indexOf(saved) !== -1) {
        elPageSize.value = saved;
      } else {
        elPageSize.value = "5";
      }
      elPageSize.addEventListener("change", function () {
        localStorage.setItem(LS_PAGE_SIZE, elPageSize.value);
        currentPage = 1;
        renderProductList();
      });
    }
    var savedRatio = localStorage.getItem(LS_BONUS_RATIO);
    if (savedRatio && RATIO_MULT[savedRatio] != null) {
      var ratioInp = document.querySelector(
        'input[name="bonus-ratio"][value="' + savedRatio + '"]'
      );
      if (ratioInp) ratioInp.checked = true;
    }
    document.querySelectorAll('input[name="bonus-ratio"]').forEach(function (inp) {
      inp.addEventListener("change", function () {
        localStorage.setItem(LS_BONUS_RATIO, getSelectedRatioKey());
        refreshAllCardBonusPreviews();
      });
    });

    if (elFullAttendanceCheck) {
      if (localStorage.getItem(LS_FULL_ATTENDANCE) === "1") {
        elFullAttendanceCheck.checked = true;
      }
      elFullAttendanceCheck.addEventListener("change", function () {
        localStorage.setItem(LS_FULL_ATTENDANCE, elFullAttendanceCheck.checked ? "1" : "0");
        updateTotalsDisplay();
      });
      updateFullAttendanceDisplay(computeGrandBonusScaled());
    }

    renderProductList();
    if (elSearch) {
      elSearch.addEventListener("input", function () {
        currentPage = 1;
        renderProductList();
      });
    }
    elClearAll.addEventListener("click", function () {
      RATIO_ORDER.forEach(function (k) {
        carts[k].clear();
      });
      renderCart();
    });
  }

  init();
})();
