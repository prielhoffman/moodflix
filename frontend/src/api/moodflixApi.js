// src/api/moodflixApi.js

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

/*
  Local poster cache.
  Used to keep poster URLs for watchlist
  even if backend returns only titles.
*/
const POSTER_CACHE_KEY = "moodflix_poster_cache_v1";

function loadPosterCache() {
  try {
    return JSON.parse(localStorage.getItem(POSTER_CACHE_KEY) || "{}");
  } catch {
    return {};
  }
}

function savePosterCache(cache) {
  try {
    localStorage.setItem(POSTER_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // ignore
  }
}

/*
  Save posters from recommendation results
  into local cache.
*/
function cacheShowsPosters(shows) {
  if (!Array.isArray(shows)) return;

  const cache = loadPosterCache();
  let changed = false;

  for (const show of shows) {
    const title = show?.title;
    const poster = show?.poster_url;

    if (title && poster && !cache[title]) {
      cache[title] = poster;
      changed = true;
    }
  }

  if (changed) savePosterCache(cache);
}

/*
  Normalize backend watchlist response
  into unified format:
  [{ title, poster_url }]
*/
function normalizeWatchlist(rawWatchlist) {
  const cache = loadPosterCache();

  if (!Array.isArray(rawWatchlist)) return [];

  // If backend returns ["title1", "title2"]
  if (rawWatchlist.length > 0 && typeof rawWatchlist[0] === "string") {
    return rawWatchlist.map((title) => ({
      title,
      poster_url: cache[title] || null,
    }));
  }

  // If backend returns objects
  return rawWatchlist
    .map((item) => {
      const title = item?.title;
      if (!title) return null;

      return {
        title,
        poster_url: item?.poster_url || cache[title] || null,
      };
    })
    .filter(Boolean);
}

/*
  Generic JSON request helper
*/
async function requestJson(path, options = {}) {
  const url = `${API_BASE}${path}`;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} on ${path}: ${text}`);
  }

  const contentType = res.headers.get("content-type") || "";

  if (!contentType.includes("application/json")) return {};

  return await res.json();
}

/*
  Try multiple possible backend paths
  (for compatibility)
*/
async function tryPaths(paths, options) {
  let lastError = null;

  for (const path of paths) {
    try {
      return await requestJson(path, options);
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error("All paths failed");
}

/* ================= API FUNCTIONS ================= */

export async function recommendShows(preferences) {
  const data = await tryPaths(
    [
      "/recommend",
      "/api/recommend",
      "/recommendations",
      "/api/recommendations",
    ],
    {
      method: "POST",
      body: JSON.stringify(preferences),
    }
  );

  const shows = Array.isArray(data)
    ? data
    : data.recommendations || data.results || [];

  cacheShowsPosters(shows);

  return shows;
}

/*
  Supports both:
  addToWatchlist("Title")
  addToWatchlist(showObject)
*/
export async function addToWatchlist(input) {
  const title = typeof input === "string" ? input : input?.title;

  if (typeof input === "object" && input?.title && input?.poster_url) {
    cacheShowsPosters([input]);
  }

  if (!title) throw new Error("addToWatchlist: missing title");

  const data = await tryPaths(
    [
      "/watchlist/add",
      "/api/watchlist/add",
      "/watchlist",
      "/api/watchlist",
    ],
    {
      method: "POST",
      body: JSON.stringify({ title }),
    }
  );

  const raw = data.watchlist ?? data.items ?? data.results ?? [];

  return { watchlist: normalizeWatchlist(raw) };
}

export async function removeFromWatchlist(title) {
  if (!title) throw new Error("removeFromWatchlist: missing title");

  const data = await tryPaths(
    [
      "/watchlist/remove",
      "/api/watchlist/remove",
      "/watchlist/delete",
      "/api/watchlist/delete",
      "/watchlist",
      "/api/watchlist",
    ],
    {
      method: "POST",
      body: JSON.stringify({ title }),
    }
  );

  const raw = data.watchlist ?? data.items ?? data.results ?? [];

  return { watchlist: normalizeWatchlist(raw) };
}

export async function fetchWatchlist() {
  const data = await tryPaths(
    ["/watchlist", "/api/watchlist"],
    { method: "GET" }
  );

  const raw = data.watchlist ?? data.items ?? data.results ?? [];

  return { watchlist: normalizeWatchlist(raw) };
}
