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
const ACCESS_TOKEN_KEY = "access_token";

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

function getAccessToken() {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function hasAccessToken() {
  return Boolean(getAccessToken());
}

function setAccessToken(token) {
  try {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } catch {
    // ignore
  }
}

function clearAccessToken() {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
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
  const token = getAccessToken();

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
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

/* ================= AUTH ================= */

export async function register(email, password) {
  if (!email || !password) throw new Error("register: missing email/password");

  // Backend expects { email, password }
  const data = await requestJson("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  return data; // { id, email, created_at }
}

export async function login(email, password) {
  if (!email || !password) throw new Error("login: missing email/password");

  const data = await requestJson("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  // Backend returns { access_token, token_type }
  if (data?.access_token) setAccessToken(data.access_token);

  return data;
}

export function logout() {
  clearAccessToken();
}

export async function fetchMe() {
  return await requestJson("/auth/me", { method: "GET" });
}

/* ================= RECOMMENDATIONS ================= */

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

/* ================= WATCHLIST ================= */

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
