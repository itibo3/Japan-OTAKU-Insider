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
  return { lang, entries: db.entries || [] };
}

function getQueryId() {
  const qs = new URLSearchParams(window.location.search);
  return qs.get("id") || "";
}

function isWeeklyEntry(e) {
  return e && (e._source === "joi-weekly" || e._source_id === "joi-weekly");
}

function containsJapanese(text) {
  return /[\u3040-\u30ff\u4e00-\u9fff]/.test(String(text || ""));
}

async function main() {
  const titleEl = document.getElementById("weeklyTitle");
  const metaEl = document.getElementById("weeklyMeta");
  const contentEl = document.getElementById("weeklyContent");
  const heroEl = document.getElementById("weeklyHero");
  const imageNoteEl = document.getElementById("weeklyImageNote");
  const backToSiteLinkEl = document.getElementById("backToSiteLink");
  try {
    const id = getQueryId();
    if (!id) throw new Error("Article ID is missing.");
    const loaded = await loadEntriesByLang();
    const lang = loaded.lang || "en";
    const entries = loaded.entries || [];
    const entry = entries.find((e) => String(e.id) === String(id));
    if (!entry || !isWeeklyEntry(entry)) throw new Error("Weekly article not found.");

    const title = lang === "ja" ? (entry.title_ja || entry.title) : (entry.title || entry.title_ja) || "Weekly JOI Article";
    const dateText = (entry.dates && entry.dates.display) ? entry.dates.display : "";
    let body = lang === "ja"
      ? (entry.article_markdown_ja || entry.description || "")
      : (entry.article_markdown_en || entry.summary_en || entry.description || entry.article_markdown_ja || "");
    if (lang !== "ja" && containsJapanese(body)) {
      body = entry.summary_en || "Weekly otaku highlights are being prepared in English.";
    }
    const hero = entry.thumbnail || "";
    const imagePrompt = entry.header_image_prompt_en || "";

    document.title = `${title} | Japan OTAKU Insider`;
    titleEl.textContent = title;
    metaEl.textContent = dateText ? `Published: ${dateText}` : "";
    if (backToSiteLinkEl) {
      backToSiteLinkEl.innerHTML = lang === "ja" ? "サイトに戻る &rarr;" : "Back to Site &rarr;";
    }
    if (heroEl && hero) {
      heroEl.src = hero;
      heroEl.style.display = "block";
    }
    if (imageNoteEl && !hero && imagePrompt) {
      imageNoteEl.textContent = `Header image draft prompt: ${imagePrompt}`;
    } else if (imageNoteEl) {
      imageNoteEl.textContent = "";
    }
    contentEl.innerHTML = renderSimpleMarkdown(body);
  } catch (e) {
    titleEl.textContent = "Weekly article unavailable";
    metaEl.textContent = "";
    contentEl.innerHTML = `<p>${escapeHtml(e.message || "Failed to load article.")}</p>`;
  }
}

document.addEventListener("DOMContentLoaded", main);
