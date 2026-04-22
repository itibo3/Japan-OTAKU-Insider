/* ─── サイト定義（将来の複数サイト対応用） ─── */
const SITES = [
  {
    id: "joi",
    name: "Japan OTAKU Insider",
    shortName: "JOI",
    url: "https://otaku.eidosfrontier.com",
    accentHue: 174,        // teal — CSS var(--accent-hue) に対応
    emoji: "🇯🇵",
    active: true,
  },
  // 将来のサイト追加例:
  // { id: "site-b", name: "Site B", shortName: "SB", url: "...", accentHue: 270, emoji: "🎮", active: false },
];

const CURRENT_SITE = SITES.find((s) => s.active) || SITES[0];

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

function slugifyAscii(input) {
  return String(input || "")
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function pickHostname(urlOrRss) {
  try {
    const u = new URL(urlOrRss);
    return u.hostname || "";
  } catch {
    return "";
  }
}

async function generateSafeSourceId({ url, rss_url, site_title }) {
  // 1) URL/RSSのホスト名を最優先（日本語タイトルでも空にならない）
  const host = pickHostname(rss_url) || pickHostname(url);
  let base = slugifyAscii(host);

  // 2) それでも空なら、RSS/URL文字列からスラグ化
  if (!base) base = slugifyAscii(rss_url || url || "");

  // 3) 最後の保険：固定プレフィックス
  if (!base) base = "source";

  // 既存IDと重複しないように suffix を付与
  const data = await api("/api/sources");
  const existing = new Set((data.sources || []).map((s) => String(s.id || "")));

  let id = base;
  let i = 2;
  while (existing.has(id)) {
    id = `${base}-${i}`;
    i++;
  }
  return id;
}

function suggestCategories({ url, rss_url, site_title }) {
  const text = `${url || ""} ${rss_url || ""} ${site_title || ""}`.toLowerCase();
  const out = new Set();

  // ざっくりヒューリスティック（Phase Aはこれで十分）
  if (text.includes("collabo") || text.includes("cafe")) out.add("cafe");
  if (text.includes("figure") || text.includes("goodsmile") || text.includes("kotobukiya")) out.add("figure");
  if (text.includes("event") || text.includes("anime-japan") || text.includes("animejapan")) out.add("event");
  if (text.includes("anime") || text.includes("natalie") || text.includes("animes")) out.add("anime");
  if (text.includes("game") || text.includes("4gamer") || text.includes("dengeki") || text.includes("hobby")) out.add("game");
  if (text.includes("news") || text.includes("otaku")) out.add("otaku-news");

  return Array.from(out);
}

function renderSourcesTable(sources) {
  const tbody = $("#sources-tbody");
  tbody.innerHTML = "";
  if (!sources || sources.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="padding: 24px; text-align: center; background: rgba(56, 189, 248, 0.08); border-radius: 8px;">
          <p style="margin: 0 0 12px; font-size: 1.1em;">登録済みソースがありません</p>
          <p style="margin: 0 0 16px; color: var(--muted, #94a3b8);">data/sources.json から読み込むと、あみあみ・4gamer など 22 件のソースが使えるようになります</p>
          <button id="first-import-button" class="primary" style="font-size: 1em; padding: 10px 20px;">sources.json から読み込む</button>
        </td>
      </tr>
    `;
    const btn = document.getElementById("first-import-button");
    if (btn) btn.addEventListener("click", () => doImport());
    return;
  }
  for (const src of sources) {
    const tr = document.createElement("tr");
    tr.dataset.sourceId = src.id;
    const catsHtml = (src.categories || []).map((c) => `<span class="pill">${c}</span>`).join("") || `<span class="muted">(なし)</span>`;
    const cats = `<div class="cats-cell">${catsHtml}</div>`;
    const statusClass = `status-${src.status || "alive"}`;
    const hasValidId = typeof src.id === "string" && src.id.trim().length > 0;
    tr.innerHTML = `
      <td>${src.id}</td>
      <td>${src.name}</td>
      <td><a href="${src.url}" target="_blank" rel="noreferrer">${src.url}</a></td>
      <td>${src.rss_url ? `<a href="${src.rss_url}" target="_blank" rel="noreferrer">${src.rss_url}</a>` : "<span class=\"muted\">(未設定)</span>"}</td>
      <td>${cats || "<span class=\"muted\">(なし)</span>"}</td>
      <td class="${statusClass}">${src.status}</td>
      <td>
        <div class="btn-group">
          <button class="secondary btn-check" data-id="${src.id}" ${hasValidId ? "" : "disabled"}>チェック</button>
          <button class="secondary btn-edit-cats" data-id="${src.id}" ${hasValidId ? "" : "disabled"}>カテゴリ</button>
          <button class="danger btn-delete" data-id="${src.id}" ${hasValidId ? "" : "disabled"}>削除</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadSources() {
  let sources = [];
  try {
    const data = await api("/api/sources");
    sources = data.sources || [];
  } catch (e) {
    console.error("loadSources error:", e);
    sources = [];
  }
  renderSourcesTable(sources);
  const banner = document.getElementById("import-banner");
  const bannerBtn = document.getElementById("import-banner-button");
  if (banner && bannerBtn) {
    if (sources.length === 0) {
      banner.style.display = "block";
      bannerBtn.onclick = () => doImport();
    } else {
      banner.style.display = "none";
    }
  }
  return sources;
}

async function doImport() {
  const btn = document.getElementById("import-banner-button");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "読み込み中…";
  }
  try {
    const res = await api("/api/sources/import?replace=1", { method: "POST" });
    await loadSources();
    alert(`読み込み完了: ${res.total || res.added || "?"}件のソースを登録しました`);
  } catch (e) {
    alert(`読み込みに失敗しました: ${e.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "sources.json から読み込む（あみあみ・4gamer など 22 件）";
    }
  }
}

function safeAttrValue(value) {
  return String(value).replace(/"/g, '\\"');
}

function highlightRowById(id) {
  const tbody = $("#sources-tbody");
  const row = tbody.querySelector(`tr[data-source-id="${safeAttrValue(id)}"]`);
  if (!row) return false;
  row.scrollIntoView({ block: "center", behavior: "smooth" });
  row.style.outline = "2px solid rgba(56, 189, 248, 0.8)";
  row.style.outlineOffset = "2px";
  setTimeout(() => {
    row.style.outline = "";
    row.style.outlineOffset = "";
  }, 1800);
  return true;
}

async function discoverRss() {
  const urlInput = $("#discover-url");
  const box = $("#discover-result");
  const url = urlInput.value.trim();
  if (!url) return;
  box.textContent = "RSSを探索中…";
  try {
    const result = await api("/api/sources/search", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
    if (!result.found) {
      box.innerHTML = `<span class="muted">RSSフィードは見つかりませんでした。</span>`;
      return;
    }
    const id = await generateSafeSourceId({
      url,
      rss_url: result.rss_url,
      site_title: result.site_title,
    });
    const suggestedCategories = suggestCategories({
      url,
      rss_url: result.rss_url,
      site_title: result.site_title,
    });
    const preview = Array.isArray(result.preview) ? result.preview : [];
    const previewHtml = preview.length
      ? `
        <div style="margin-top:8px;"><strong>追加前プレビュー（最新${preview.length}件）</strong></div>
        <ol style="margin:6px 0 0 18px; display:flex; flex-direction:column; gap:4px;">
          ${preview
            .map(
              (it) =>
                `<li><a href="${it.link}" target="_blank" rel="noreferrer">${it.title || it.link}</a><span class="muted"> ${it.published ? `(${it.published})` : ""}</span></li>`,
            )
            .join("")}
        </ol>
      `
      : `<div class="muted" style="margin-top:8px;">プレビュー取得に失敗しました（RSSは見つかっています）。</div>`;

    const suggestedHtml = suggestedCategories.length
      ? `
        <div style="margin-top:8px;"><strong>カテゴリ候補</strong></div>
        <div style="margin-top:6px; display:flex; flex-wrap:wrap; gap:6px;">
          ${suggestedCategories
            .map((c) => `<button class="secondary btn-suggest-cat" data-cat="${c}">${c}</button>`)
            .join("")}
        </div>
        <div class="muted" style="margin-top:6px;">追加後にカテゴリを自動設定します（候補をクリック）。</div>
      `
      : `<div class="muted" style="margin-top:8px;">カテゴリ候補は見つかりませんでした。</div>`;

    box.innerHTML = `
      <div><strong>RSS発見:</strong> <a href="${result.rss_url}" target="_blank" rel="noreferrer">${result.rss_url}</a></div>
      <div>サイトタイトル: ${result.site_title || "(不明)"}</div>
      <div>検出方法: ${result.method}</div>
      <div class="muted">追加予定ID: ${id}</div>
      ${suggestedHtml}
      ${previewHtml}
      <div style="margin-top:10px;">
        <button id="add-source-button">このRSSをソースとして追加</button>
      </div>
    `;

    const selectedCats = new Set();
    box.querySelectorAll(".btn-suggest-cat").forEach((btn) => {
      btn.addEventListener("click", () => {
        const cat = btn.getAttribute("data-cat");
        if (!cat) return;
        if (selectedCats.has(cat)) {
          selectedCats.delete(cat);
          btn.style.borderColor = "";
          btn.style.color = "";
        } else {
          selectedCats.add(cat);
          btn.style.borderColor = "rgba(56, 189, 248, 0.7)";
          btn.style.color = "var(--text)";
        }
      });
    });
    $("#add-source-button").addEventListener("click", async () => {
      try {
        await api("/api/sources/add", {
          method: "POST",
          body: JSON.stringify({
            id,
            name: result.site_title || id,
            url,
            rss_url: result.rss_url,
            type: "rss",
            categories: Array.from(selectedCats),
          }),
        });
        // 追加後もプレビューが確認できるよう、画面は極力そのままにしてメッセージだけ出す
        const note = document.createElement("div");
        note.className = "muted";
        note.style.marginTop = "8px";
        note.textContent = `追加しました。追加ID: ${id}（下の一覧へ移動します）`;
        box.appendChild(note);
        const pushNote = document.createElement("div");
        pushNote.className = "muted";
        pushNote.style.marginTop = "6px";
        pushNote.style.color = "var(--accent-cyan, #38bdf8)";
        pushNote.textContent = "※ Daily Update ワークフローで反映するには「GitHubにプッシュ」を押してください。";
        box.appendChild(pushNote);
        urlInput.value = "";
        await loadSources();
        // 追加された行が見つからない場合は、同じIDで上書きされた可能性がある
        const found = highlightRowById(id);
        if (!found) {
          const warn = document.createElement("div");
          warn.className = "muted";
          warn.style.marginTop = "6px";
          warn.textContent =
            "一覧にIDが見つかりませんでした（同じIDで上書きされた/並び替えの影響の可能性があります）。";
          box.appendChild(warn);
        }
      } catch (e) {
        box.textContent = `追加に失敗しました: ${e.message}`;
      }
    });
  } catch (e) {
    box.textContent = `エラー: ${e.message}`;
  }
}

function setupTabs() {
  $$(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.classList.contains("disabled")) return;
      const tab = btn.getAttribute("data-tab");
      $$(".tab").forEach((b) => b.classList.toggle("active", b === btn));
      $$(".tab-panel").forEach((p) => {
        p.classList.toggle("active", p.id === `tab-${tab}`);
      });
      // 収集記事タブに切り替えたら一覧を再読み込み（運用品質の詰め）
      if (tab === "articles") {
        loadArticles();
      }
    });
  });
}

function promptCategories(defaultValue) {
  const input = window.prompt(
    "カテゴリをカンマ区切りで入力（例: cafe,figure,otaku-news）",
    defaultValue || "",
  );
  if (input == null) return null;
  return input
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function setupTableActions() {
  const tbody = $("#sources-tbody");
  tbody.addEventListener("click", async (e) => {
    const target = e.target;
    if (!(target instanceof HTMLButtonElement)) return;
    const id = target.getAttribute("data-id");
    if (!id) return;

    if (target.classList.contains("btn-check")) {
      try {
        const res = await api(`/api/sources/${encodeURIComponent(id)}/check`);
        await loadSources();
        highlightRowById(id);
        if (res && typeof res.ok === "boolean") {
          const msg = res.ok ? "OK（到達できた）" : "NG（到達できない）";
          alert(`生存確認: ${id} → ${msg}`);
        }
      } catch (err) {
        alert(`生存確認に失敗しました: ${err.message}`);
      }
      return;
    }

    if (target.classList.contains("btn-delete")) {
      if (!window.confirm(`ソース「${id}」を削除しますか？`)) return;
      await api(`/api/sources/${encodeURIComponent(id)}`, { method: "DELETE" });
      loadSources();
      return;
    }

    if (target.classList.contains("btn-edit-cats")) {
      const row = target.closest("tr");
      const catsCell = row?.querySelector("td:nth-child(5)");
      const currentText = catsCell?.textContent || "";
      const current =
        currentText && !currentText.includes("なし")
          ? currentText
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean)
            .join(",")
          : "";
      const categories = promptCategories(current);
      if (categories == null) return;
      await api(`/api/sources/${encodeURIComponent(id)}/category`, {
        method: "PUT",
        body: JSON.stringify({ categories }),
      });
      loadSources();
    }
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPublishedAt(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleDateString("ja-JP", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return String(isoStr).slice(0, 10);
  }
}

function renderArticlesList(articles, totalCount) {
  const list = $("#articles-list");
  if (!list) return;

  const items = Array.isArray(articles) ? articles : [];
  if (items.length === 0) {
    list.innerHTML = `<div class="muted">記事がありません（まだ収集されていません）。</div>`;
    return;
  }

  const countHtml = totalCount != null
    ? `<div class="muted" style="margin-bottom:12px;">全 ${totalCount} 件中 ${items.length} 件表示</div>`
    : "";

  list.innerHTML = countHtml + items
    .map((a) => {
      const id = a.id;
      const title = escapeHtml(a.title);
      const url = a.url || "#";
      let excerpt = a.excerpt ? escapeHtml(a.excerpt) : "";
      if (excerpt.length > 120) excerpt = excerpt.slice(0, 117) + "…";
      const publishedAt = formatPublishedAt(a.published_at);
      const isBookmarked = Boolean(a.is_bookmarked);
      const star = isBookmarked ? "★" : "☆";
      const sourceId = a.source_id ? `<span class="pill">${escapeHtml(a.source_id)}</span>` : "";
      const ogpHtml = a.ogp_image
        ? `<img class="article-ogp" src="${escapeHtml(a.ogp_image)}" alt="" loading="lazy">`
        : "";

      return `
        <article class="article-item ${a.is_bookmarked ? 'bookmarked' : ''}">
          <div class="article-top">
            ${ogpHtml}
            <div class="article-body">
              <a class="article-link" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${title}</a>
              ${excerpt ? `<div class="article-excerpt">${excerpt}</div>` : ""}
              <div class="muted article-meta">
                ${publishedAt ? `${publishedAt}` : ""}
                ${sourceId}
              </div>
            </div>
            <button class="secondary btn-bookmark" data-id="${id}" title="ブックマーク">${star}</button>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadArticles() {
  const list = $("#articles-list");
  if (!list) return;
  list.innerHTML = `<div class="muted">読み込み中…</div>`;
  try {
    const data = await api("/api/articles?limit=100", { method: "GET" });
    renderArticlesList(data.articles || [], data.count);
  } catch (e) {
    list.innerHTML = `<div class="muted">記事一覧の読み込みに失敗しました: ${escapeHtml(
      e.message || String(e)
    )}</div>`;
  }
}

function setupArticlesActions() {
  const list = $("#articles-list");
  if (!list) return;

  list.addEventListener("click", async (e) => {
    const target = e.target;
    if (!(target instanceof HTMLButtonElement)) return;
    if (!target.classList.contains("btn-bookmark")) return;

    const id = target.getAttribute("data-id");
    if (!id) return;

    target.disabled = true;
    try {
      await api(`/api/articles/${encodeURIComponent(id)}/bookmark`, {
        method: "PUT",
        body: JSON.stringify({}),
      });
      await loadArticles();
    } catch (err) {
      alert(`ブックマーク切替に失敗: ${err.message}`);
    } finally {
      target.disabled = false;
    }
  });
}

function setupArticlesButtons() {
  const fetchBtn = $("#fetch-articles-button");
  const refreshBtn = $("#refresh-articles-button");
  const limitInput = $("#fetch-limit");
  const summary = $("#articles-fetch-summary");
  if (!fetchBtn || !refreshBtn || !limitInput || !summary) return;

  fetchBtn.addEventListener("click", async () => {
    fetchBtn.disabled = true;
    summary.innerHTML = `<div class="muted">収集中…</div>`;

    const limit = Math.max(1, Math.min(50, parseInt(limitInput.value || "5", 10) || 5));

    try {
      const res = await api("/api/fetch", {
        method: "POST",
        body: JSON.stringify({ limit }),
      });

      const totalInserted = res.total_inserted ?? 0;
      const results = Array.isArray(res.results) ? res.results : [];

      const breakdownHtml =
        results.length > 0
          ? `
        <div style="margin-top:6px;">
          <strong>ソース別</strong>
          <div style="display:flex; flex-direction:column; gap:4px; margin-top:6px;">
            ${results
              .map((r) => {
                const sid = escapeHtml(r.source_id || "");
                const inserted = r.inserted ?? 0;
                const skipped = r.skipped_existing ?? 0;
                const ok = r.ok ? "OK" : "NG";
                const err = r.error ? ` (${escapeHtml(r.error)})` : "";
                return `<div class="muted">${sid}: ${ok} / +${inserted}（既存スキップ:${skipped}）${err}</div>`;
              })
              .join("")}
          </div>
        </div>
      `
          : "";

      summary.innerHTML = `
        <div><strong>新規件数:</strong> ${totalInserted}</div>
        ${breakdownHtml}
      `;

      await loadArticles();
    } catch (e) {
      summary.innerHTML = `<div class="muted">収集に失敗しました: ${escapeHtml(
        e.message || String(e)
      )}</div>`;
    } finally {
      fetchBtn.disabled = false;
    }
  });

  refreshBtn.addEventListener("click", async () => {
    await loadArticles();
  });
}

function setupButtons() {
  $("#discover-button").addEventListener("click", (e) => {
    e.preventDefault();
    discoverRss();
  });
  $("#discover-url").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      discoverRss();
    }
  });
  $("#check-all-button").addEventListener("click", async () => {
    try {
      await api("/api/sources/check-all", { method: "POST" });
      loadSources();
    } catch (e) {
      alert(`生存確認に失敗しました: ${e.message}`);
    }
  });

  $("#import-sources-button").addEventListener("click", async () => {
    const replace = window.confirm(
      "data/sources.json からソースを読み込みます。\n\n" +
      "OK: 足りない分だけ追加（既存はそのまま）\n" +
      "キャンセル: 強制上書き（DBを空にして全件取り込み）"
    );
    try {
      const res = await api(
        `/api/sources/import?replace=${replace ? "0" : "1"}`,
        { method: "POST" }
      );
      await loadSources();
      const msg = replace
        ? `${res.added}件追加`
        : `全件再読み込み完了（${res.total || res.added || "?"}件）`;
      alert(`読み込み完了: ${msg}`);
    } catch (e) {
      alert(`読み込みに失敗しました: ${e.message}`);
    }
  });

  $("#export-sources-button").addEventListener("click", async () => {
    if (!window.confirm("DBの内容を data/sources.json に書き戻します。よろしいですか？（バックアップ作成あり）")) {
      return;
    }
    try {
      const res = await api("/api/sources/export", { method: "POST" });
      alert(`書き戻し完了: ${res.count}件\n${res.path}`);
    } catch (e) {
      alert(`書き戻しに失敗しました: ${e.message}`);
    }
  });

  $("#push-github-button").addEventListener("click", async () => {
    if (!window.confirm("sources.json を書き戻して GitHub にプッシュします。よろしいですか？")) return;
    try {
      const res = await api("/api/git/push", { method: "POST" });
      alert(res.message || "プッシュ完了");
    } catch (e) {
      let msg = e.message || String(e);
      try {
        const err = JSON.parse(msg);
        if (err.error) msg = err.error;
      } catch (_) {
        if (msg.includes("<!") || msg.length > 150) {
          msg = "サーバーエラーです。RSS Manager を再起動してからもう一度お試しください。";
        }
      }
      alert(`プッシュに失敗しました: ${msg}`);
    }
  });
}

// ─── 手動追加タブのロジック ───

function setupManualAdd() {
  // 今日の日付をデフォルトにセット
  const today = new Date().toISOString().slice(0, 10);
  $("#manual-date").value = today;

  // git pull ボタン
  $("#manual-pull-latest-button").addEventListener("click", () => pullLatest());

  // サムネイルプレビュー
  $("#manual-thumbnail").addEventListener("input", () => {
    const url = $("#manual-thumbnail").value.trim();
    const preview = $("#manual-thumbnail-preview");
    const img = $("#manual-thumbnail-img");
    if (url) {
      img.src = url;
      preview.style.display = "block";
    } else {
      preview.style.display = "none";
    }
  });

  // URL から情報取得
  $("#manual-fetch-meta-button").addEventListener("click", () => fetchEntryMeta());
  $("#manual-url").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); fetchEntryMeta(); }
  });

  // entries.json に追加
  $("#manual-add-button").addEventListener("click", () => submitManualEntry());

  // GitHub に公開
  $("#manual-push-button").addEventListener("click", () => pushEntries());
}

async function pullLatest() {
  const btn = $("#manual-pull-latest-button");
  const resultBox = $("#manual-pull-result");
  btn.disabled = true;
  resultBox.textContent = "🔄 取得中...";
  resultBox.className = "result-box";
  resultBox.style.display = "block";

  try {
    const res = await api("/api/entries/pull", { method: "POST" });
    resultBox.textContent = `✅ ${res.message}${res.detail ? `（${res.detail}）` : ""}`;
    resultBox.classList.remove("error");
  } catch (e) {
    let msg = e.message || String(e);
    try { const err = JSON.parse(msg); if (err.error) msg = err.error; } catch (_) {}
    resultBox.textContent = `❌ 取得失敗: ${msg}`;
    resultBox.classList.add("error");
  } finally {
    btn.disabled = false;
  }
}

async function fetchEntryMeta() {
  const url = $("#manual-url").value.trim();
  if (!url) { alert("URL を入力してください"); return; }

  const resultBox = $("#manual-fetch-result");
  resultBox.textContent = "🔄 情報取得中...";
  resultBox.className = "result-box";
  resultBox.style.display = "block";

  try {
    const meta = await api("/api/entries/fetch-meta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (meta.error) {
      resultBox.textContent = `❌ 取得失敗: ${meta.error}`;
      resultBox.classList.add("error");
      return;
    }
    if (meta.url_status !== 200) {
      resultBox.textContent = `⚠️ URL ステータス: ${meta.url_status ?? "接続不可"}（URL を確認してください）`;
      resultBox.classList.add("warn");
      return;
    }

    // フォームに自動入力（日本語欄を優先して埋める）
    if (meta.title) {
      if (!$("#manual-title-ja").value) $("#manual-title-ja").value = meta.title;
      if (!$("#manual-title").value) $("#manual-title").value = meta.title;
    }
    if (meta.description) {
      if (!$("#manual-description-ja").value) $("#manual-description-ja").value = meta.description;
      if (!$("#manual-description").value) $("#manual-description").value = meta.description;
    }
    if (meta.og_image && !$("#manual-thumbnail").value) {
      $("#manual-thumbnail").value = meta.og_image;
      $("#manual-thumbnail-img").src = meta.og_image;
      $("#manual-thumbnail-preview").style.display = "block";
    }

    resultBox.textContent = `✅ 取得成功（ステータス ${meta.url_status}）：タイトル「${meta.title || "(なし)"}」`;
    resultBox.classList.remove("error", "warn");
  } catch (e) {
    resultBox.textContent = `❌ 取得エラー: ${e.message}`;
    resultBox.classList.add("error");
  }
}

async function submitManualEntry() {
  const url = $("#manual-url").value.trim();
  const title = $("#manual-title").value.trim();
  const title_ja = $("#manual-title-ja").value.trim();
  const description_ja = $("#manual-description-ja").value.trim();
  const description = $("#manual-description").value.trim();
  const category = $("#manual-category").value;
  const display_date = $("#manual-date").value;
  const thumbnail = $("#manual-thumbnail").value.trim();

  if (!url || !(title_ja || title) || !(description_ja || description)) {
    alert("URL・タイトル（日本語または英語）・概要（日本語または英語）は必須です");
    return;
  }

  const resultBox = $("#manual-add-result");
  resultBox.textContent = "🔄 追加中...";
  resultBox.className = "result-box";
  resultBox.style.display = "block";
  $("#manual-add-button").disabled = true;

  try {
    const res = await api("/api/entries/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, title, title_ja, description, description_ja, category, display_date, thumbnail }),
    });

    if (res.ok) {
      const note = res.note ? ` / ${res.note}` : "";
      resultBox.textContent = `✅ ${res.message}${note}（ID: ${res.entry_id}）`;
      resultBox.classList.remove("error");
      $("#manual-push-button").disabled = false;
    } else {
      resultBox.textContent = `❌ 追加失敗: ${res.message || res.error}`;
      resultBox.classList.add("error");
      $("#manual-add-button").disabled = false;
    }
  } catch (e) {
    resultBox.textContent = `❌ エラー: ${e.message}`;
    resultBox.classList.add("error");
    $("#manual-add-button").disabled = false;
  }
}

async function pushEntries() {
  if (!window.confirm("entries.json を GitHub にプッシュします。よろしいですか？")) return;

  $("#manual-push-button").disabled = true;
  const resultBox = $("#manual-add-result");
  resultBox.textContent = "🔄 プッシュ中...";
  resultBox.style.display = "block";

  try {
    const res = await api("/api/entries/push", { method: "POST" });
    resultBox.textContent = `✅ ${res.message || "GitHub に公開しました"}`;
    resultBox.classList.remove("error");
  } catch (e) {
    let msg = e.message || String(e);
    try { const err = JSON.parse(msg); if (err.error) msg = err.error; } catch (_) {}
    resultBox.textContent = `❌ プッシュ失敗: ${msg}`;
    resultBox.classList.add("error");
    $("#manual-push-button").disabled = false;
  }
}

// ─── Web Share Target 受け取り ───
// Android の「共有」ボタンから URL が ?shared_url=... として渡される

function handleShareTarget() {
  const params = new URLSearchParams(window.location.search);
  const sharedUrl   = params.get("shared_url")   || "";
  const sharedText  = params.get("shared_text")  || "";
  const sharedTitle = params.get("shared_title") || "";

  if (!sharedUrl && !sharedText) return;

  // URL を特定する（shared_url 優先、なければ shared_text から URL っぽいものを抜く）
  let url = sharedUrl;
  if (!url && sharedText) {
    const m = sharedText.match(/https?:\/\/\S+/);
    if (m) url = m[0];
  }
  if (!url) return;

  // 手動追加タブを開く
  const manualTab = document.querySelector('[data-tab="manual-add"]');
  if (manualTab) manualTab.click();

  // フォームに入れる
  const urlInput = $("#manual-url");
  if (urlInput) {
    urlInput.value = url;
    // タイトルがあれば入れる
    if (sharedTitle) {
      const titleInput = $("#manual-title-ja");
      if (titleInput && !titleInput.value) titleInput.value = sharedTitle;
    }
  }

  // URL パラメータをきれいにしておく（リロード時に再実行されないように）
  window.history.replaceState({}, "", "./");

  // 自動で情報取得を走らせる
  if (url) {
    setTimeout(() => fetchEntryMeta(), 300);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupButtons();
  setupTableActions();
  setupArticlesActions();
  setupArticlesButtons();
  setupManualAdd();
  handleShareTarget();
  loadSources();
  loadArticles();
});

