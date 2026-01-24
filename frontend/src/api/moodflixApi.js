const API_BASE_URL = "http://127.0.0.1:8000";

/*
  Fetch recommendations from backend
*/
export async function recommendShows(preferences) {
  const response = await fetch(`${API_BASE_URL}/recommend`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(preferences),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch recommendations");
  }

  return response.json();
}


/*
  Add show to watchlist
*/
export async function addToWatchlist(title) {
  const response = await fetch(`${API_BASE_URL}/watchlist/add`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw new Error("Failed to add to watchlist");
  }

  return response.json();
}


/*
  Remove show from watchlist
*/
export async function removeFromWatchlist(title) {
  const response = await fetch(`${API_BASE_URL}/watchlist/remove`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw new Error("Failed to remove from watchlist");
  }

  return response.json();
}


/*
  Get full watchlist
*/
export async function fetchWatchlist() {
  const response = await fetch(`${API_BASE_URL}/watchlist`);

  if (!response.ok) {
    throw new Error("Failed to fetch watchlist");
  }

  return response.json();
}
