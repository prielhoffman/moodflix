// Base URL of your FastAPI backend
// Adjust if your backend runs on a different host/port
const API_BASE_URL = "http://127.0.0.1:8000";

/*
  Send user preferences to the backend
  and return the list of recommendations.
*/
export async function recommendShows(preferences) {
  try {
    const response = await fetch(`${API_BASE_URL}/recommend`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(preferences),
    });

    // If the server returned an error status
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Failed to fetch recommendations");
    }

    // Parse JSON response
    const data = await response.json();

    return data;
  } catch (error) {
    console.error("API error:", error);
    throw error;
  }
}
