/*
  このファイルの目的:
  - Aboutページの統計表示を data/*.json から動的に更新する
  - 自動化パイプラインの要約状態をページ下部に表示する
  入力/出力:
  - 入力: /data/entries.json, /data/sources.json
  - 出力: Aboutページ内の数値・スナップショット表示を更新
*/
(function () {
  function fmtNum(n) {
    return Number(n || 0).toLocaleString("en-US");
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function toLocalDateTime(isoText) {
    if (!isoText) return "unknown";
    const d = new Date(isoText);
    if (Number.isNaN(d.getTime())) return String(isoText);
    return d.toLocaleString();
  }

  function uniqueCategories(entries) {
    const set = new Set();
    for (const e of entries || []) {
      const cats = Array.isArray(e && e.categories) ? e.categories : [];
      for (const c of cats) {
        if (c) set.add(c);
      }
    }
    return set.size;
  }

  function renderPipelineSummary(entriesDb, sourcesDb) {
    const noteEl = document.getElementById("aboutPipelineNote");
    const listEl = document.getElementById("aboutPipelineList");
    if (!noteEl || !listEl) return;

    const lastUpdated = toLocalDateTime(entriesDb && entriesDb.last_updated);
    const sources = (sourcesDb && sourcesDb.sources) || [];
    const activeSources = sources.filter((s) => !s.disabled);
    const disabledSources = sources.filter((s) => !!s.disabled);

    noteEl.textContent = `Last content sync: ${lastUpdated}`;
    listEl.innerHTML = [
      "<li>Daily update pipeline: active (scheduled + manual trigger)</li>",
      "<li>Weekly JOI bulletin pipeline: active (scheduled + manual trigger)</li>",
      `<li>Source pipelines active: ${fmtNum(activeSources.length)} / ${fmtNum(sources.length)}</li>`,
      `<li>Paused/retired source pipelines: ${fmtNum(disabledSources.length)}</li>`,
    ].join("");
  }

  async function loadAboutStats() {
    try {
      const [entriesRes, sourcesRes] = await Promise.all([
        fetch("/data/entries.json", { cache: "no-store" }),
        fetch("/data/sources.json", { cache: "no-store" }),
      ]);
      const entriesDb = await entriesRes.json();
      const sourcesDb = await sourcesRes.json();

      const entries = entriesDb.entries || [];
      const sources = sourcesDb.sources || [];
      const rssActive = sources.filter((s) => s.type === "rss" && !s.disabled).length;

      setText("aboutStatEntries", `${fmtNum(entriesDb.total_entries || entries.length)}+`);
      setText("aboutStatRssSources", fmtNum(rssActive));
      setText("aboutStatCategories", fmtNum(uniqueCategories(entries)));
      setText("aboutSourceTotal", fmtNum(sources.length));
      setText("aboutSourceRss", fmtNum(rssActive));

      renderPipelineSummary(entriesDb, sourcesDb);
    } catch (e) {
      setText("aboutPipelineNote", "Automation status could not be loaded right now.");
      const listEl = document.getElementById("aboutPipelineList");
      if (listEl) {
        listEl.innerHTML = "<li>Please reload this page later.</li>";
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadAboutStats);
  } else {
    loadAboutStats();
  }
})();
