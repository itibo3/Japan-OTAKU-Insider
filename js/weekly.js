function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderSimpleMarkdown(md) {
  const lines = String(md || "").split(/\r?\n/);
  const out = [];
  let inList = false;
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      continue;
    }
    if (line.startsWith("### ")) {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      out.push(`<h3>${escapeHtml(line.slice(4))}</h3>`);
      continue;
    }
    if (line.startsWith("## ")) {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      out.push(`<h2>${escapeHtml(line.slice(3))}</h2>`);
      continue;
    }
    if (line.startsWith("# ")) {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      out.push(`<h1>${escapeHtml(line.slice(2))}</h1>`);
      continue;
    }
    if (line.startsWith("- ")) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${escapeHtml(line.slice(2))}</li>`);
      continue;
    }
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
    out.push(`<p>${escapeHtml(line)}</p>`);
  }
  if (inList) out.push("</ul>");
  return out.join("\n");
}

async function loadEntriesByLang() {
  const lang = localStorage.getItem("otaku_lang") || "en";
  const url = lang === "ja" ? "/data/entries_ja.json" : "/data/entries.json";
  const resp = await fetch(url);
  const db = await resp.json();
  return db.entries || [];
}

function getQueryId() {
  const qs = new URLSearchParams(window.location.search);
  return qs.get("id") || "";
}

function isWeeklyEntry(e) {
  return e && (e._source === "joi-weekly" || e._source_id === "joi-weekly");
}

async function main() {
  const titleEl = document.getElementById("weeklyTitle");
  const metaEl = document.getElementById("weeklyMeta");
  const contentEl = document.getElementById("weeklyContent");
  try {
    const id = getQueryId();
    if (!id) throw new Error("Article ID is missing.");
    const entries = await loadEntriesByLang();
    const entry = entries.find((e) => String(e.id) === String(id));
    if (!entry || !isWeeklyEntry(entry)) throw new Error("Weekly article not found.");

    const title = entry.title_ja || entry.title || "Weekly JOI Article";
    const dateText = (entry.dates && entry.dates.display) ? entry.dates.display : "";
    const body = entry.article_markdown_ja || entry.description || "";

    document.title = `${title} | Japan OTAKU Insider`;
    titleEl.textContent = title;
    metaEl.textContent = dateText ? `Published: ${dateText}` : "";
    contentEl.innerHTML = renderSimpleMarkdown(body);
  } catch (e) {
    titleEl.textContent = "Weekly article unavailable";
    metaEl.textContent = "";
    contentEl.innerHTML = `<p>${escapeHtml(e.message || "Failed to load article.")}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", main);
