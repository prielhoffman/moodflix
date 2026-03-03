const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

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
  [{ show_id?, title, poster_url }]
*/
function normalizeWatchlist(rawWatchlist) {
  const cache = loadPosterCache();

  if (!Array.isArray(rawWatchlist)) return [];

  // If backend returns ["title1", "title2"]
  if (rawWatchlist.length > 0 && typeof rawWatchlist[0] === "string") {
    return rawWatchlist.map((title) => ({
      show_id: null,
      title,
      poster_url: cache[title] || null,
    }));
  }

  // If backend returns objects (show_id, title, poster_url)
  return rawWatchlist
    .map((item) => {
      const title = item?.title;
      if (!title) return null;

      return {
        show_id: item?.show_id ?? null,
        title,
        poster_url: item?.poster_url ?? cache[title] ?? null,
      };
    })
    .filter(Boolean);
}

/*
  Generic JSON request helper
*/
function createApiError(message, status) {
  const err = new Error(message);
  if (status != null) err.status = status;
  return err;
}

async function requestJson(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const token = getAccessToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    // Always send Bearer token when present so watchlist/auth requests are authenticated
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let message = `Request failed: ${text || res.statusText || res.status}`;
    try {
      const body = JSON.parse(text);
      if (body?.message && typeof body.message === "string") {
        message = body.message;
      }
    } catch (_) {
      // keep default message
    }
    throw createApiError(message, res.status);
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

export async function register(fullName, dateOfBirth, email, password) {
  if (!fullName?.trim() || !dateOfBirth || !email || !password) {
    throw new Error("register: missing full_name, date_of_birth, email, or password");
  }

  // Backend expects { full_name, date_of_birth, email, password }
  const data = await requestJson("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      full_name: fullName.trim(),
      date_of_birth: dateOfBirth,
      email,
      password,
    }),
  });

  return data; // { id, full_name, email, date_of_birth, created_at }
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
  Add by show_id (preferred) or by title when show_id is missing.
  Backend expects { show_id: number } or { title: string }; show_id must be integer.
*/
export async function addToWatchlist(input) {
  const showId = typeof input === "object" && input != null ? input.id ?? input.show_id : null;
  const title = typeof input === "object" && input != null ? input.title : null;
  const hasValidId = showId != null && Number(showId) > 0;
  const hasTitle = title != null && String(title).trim() !== "";

  if (!hasValidId && !hasTitle) {
    throw new Error("addToWatchlist: show must have an id (show_id) or title");
  }

  if (typeof input === "object" && input?.title && input?.poster_url) {
    cacheShowsPosters([input]);
  }

  const payload = hasValidId
    ? { show_id: Number(showId) }
    : {
        title: String(title).trim(),
        ...(input?.poster_url ? { poster_url: input.poster_url } : {}),
      };
  console.log("Watchlist add payload sent:", payload);

  const data = await tryPaths(
    [
      "/watchlist/add",
      "/api/watchlist/add",
      "/watchlist",
      "/api/watchlist",
    ],
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );

  const raw = data.watchlist ?? data.items ?? data.results ?? [];
  return { watchlist: normalizeWatchlist(raw) };
}

/*
  Remove by show_id (preferred) or title. Pass item or { show_id } or { title } or string title.
*/
export async function removeFromWatchlist(itemOrTitle) {
  let body;
  if (typeof itemOrTitle === "string" && itemOrTitle.trim()) {
    body = { title: itemOrTitle.trim() };
  } else if (typeof itemOrTitle === "object" && itemOrTitle != null) {
    const id = itemOrTitle.show_id ?? itemOrTitle.id;
    if (id != null && Number(id) > 0) {
      body = { show_id: Number(id) };
    } else if (itemOrTitle.title) {
      body = { title: String(itemOrTitle.title).trim() };
    } else {
      throw new Error("removeFromWatchlist: item must have show_id or title");
    }
  } else {
    throw new Error("removeFromWatchlist: pass item (show_id/title) or title string");
  }

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
      body: JSON.stringify(body),
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

/* ================= SEMANTIC SEARCH ================= */

export async function semanticSearch(query, topK = 10) {
  const trimmed = String(query || "").trim();
  if (!trimmed) throw new Error("semanticSearch: missing query");

  return await requestJson("/search/semantic", {
    method: "POST",
    body: JSON.stringify({
      query: trimmed,
      top_k: topK,
    }),
  });
}
