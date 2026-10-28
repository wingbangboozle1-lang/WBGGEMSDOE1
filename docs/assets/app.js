"use strict";

// All prediction artifacts and decisions are precomputed. No browser upload,
// training, false generation spinner, or localhost-dependent API exists.
const filter = document.querySelector("#site-filter");
if (filter) {
  filter.addEventListener("input", () => {
    const query = filter.value.trim().toLowerCase();
    document.querySelectorAll("#site-table tbody tr").forEach(row => {
      row.hidden = !row.dataset.site.toLowerCase().includes(query);
    });
  });
}

for (const button of document.querySelectorAll("[data-copy]")) {
  button.addEventListener("click", async () => {
    const node = document.getElementById(button.dataset.copy);
    if (!node) return;
    try {
      await navigator.clipboard.writeText(node.textContent.trim());
      button.textContent = "Copied";
      button.setAttribute("aria-label", "Copied to clipboard");
    } catch {
      // Select the visible text instead of falsely claiming a copy succeeded.
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(node);
      selection.removeAllRanges();
      selection.addRange(range);
      button.textContent = "Text selected";
    }
  });
}

async function showFeed() {
  try {
    const response = await fetch("data/feed.json", {cache: "no-store"});
    if (!response.ok) throw new Error("Feed unavailable");
    const feed = await response.json();
    const observation = feed.leaderboard;
    const value = observation?.public_dw_tversky;
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) {
      throw new Error("No valid verified observation");
    }
    for (const node of document.querySelectorAll("[data-feed-score]")) {
      node.textContent = value.toFixed(4);
    }
    const date = observation.observed_utc || observation.observed_date_utc || observation.date_utc;
    for (const node of document.querySelectorAll("[data-feed-date]")) {
      node.textContent = date ? `observed ${date.replace("T", " ")}` : "observation date unavailable";
    }
    const heads = Array.isArray(feed.repository_heads) ? feed.repository_heads : [];
    const changed = heads.filter(row => row.changed_since_audit === true).length;
    const stale = heads.filter(row => row.refresh_status !== "network_verified").length;
    const fresh = feed.leaderboard_status === "network_verified";
    let status = fresh
      ? "Official public-page refresh succeeded. Not a result for any project file."
      : "Retained dated observation; a fresh official-page check is unavailable or was not attempted.";
    if (changed) status += ` ${changed} upstream heads changed since the frozen audit; no model was revalidated.`;
    if (!heads.length || stale) status += ` ${stale || "All"} upstream head observations are stale or unavailable.`;
    if (date && Date.now() - Date.parse(date) > 24 * 60 * 60 * 1000) {
      status += " Observation is older than 24 hours.";
    }
    for (const node of document.querySelectorAll("[data-feed-status]")) node.textContent = status;
  } catch {
    for (const node of document.querySelectorAll("[data-feed-status]")) {
      node.textContent = "Live feed unavailable. The dated observation above is retained, not freshly verified.";
    }
  }
}
showFeed();
