function esc(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function idDateFromId(id) {
  const m = /^.+-(\d{8,12})-/.exec(id || "");
  return m ? m[1].padEnd(12, "0") : "000000000000";
}

async function loadEntries() {
  const lang = localStorage.getItem("otaku_lang") || "en";
  const url = lang === "ja" ? "/data/entries_ja.json" : "/data/entries.json";
  const resp = await fetch(url);
  const db = await resp.json();
  return { lang, entries: db.entries || [] };
}

function isWeekly(e) {
  return e && (e._source_id === "joi-weekly" || e._source === "joi-weekly");
}

function renderRow(e, lang) {
  const title = lang === "ja" ? (e.title_ja || e.title || "Weekly Article") : (e.title || e.title_ja || "Weekly Article");
  const summary = lang === "ja" ? (e.summary_ja || e.summary_en || "") : (e.summary_en || e.summary_ja || "");
  const dateText = (e.dates && e.dates.display) ? e.dates.display : "";
  const href = `/weekly.html?id=${encodeURIComponent(e.id)}`;
  return `
    <article class="archive-item">
      <h2 class="archive-title"><a href="${href}">${esc(title)}</a></h2>
      <div class="weekly-meta">${esc(dateText)}</div>
      <p>${esc(summary)}</p>
      <a href="${href}" class="modal-link">Read Article &rarr;</a>
    </article>
  `;
}

async function main() {
  const list = document.getElementById("weeklyArchiveList");
  if (!list) return;
  try {
    const loaded = await loadEntries();
    const lang = loaded.lang;
    const entries = loaded.entries.filter(isWeekly).sort((a, b) => idDateFromId(b.id).localeCompare(idDateFromId(a.id)));
    if (!entries.length) {
      list.innerHTML = "<p>週間記事はまだありません。</p>";
      return;
    }
    list.innerHTML = entries.map((e) => renderRow(e, lang)).join("\n");
  } catch (e) {
    list.innerHTML = `<p>${esc(e.message || "Failed to load archive.")}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", main);
