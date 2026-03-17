import { useState } from "react";
import { semanticSearch } from "../api/moodflixApi";

function extractReason(reasonString) {
  const text = String(reasonString || "").trim();
  if (!text) return "Matches your search description.";
  const parts = text.split(/\s*-\s*/);
  const explanation = parts.length > 1 ? parts.slice(1).join(" - ").trim() : text;
  return explanation || "Matches your search description.";
}

function SearchPage({ isSaved, onToggleSave, savingTitle }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      setError("Please enter a search term");
      setHasSearched(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const data = await semanticSearch(trimmed, 5);
      setResults(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError(err?.message || "Search failed. Please try again.");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="content-section">
      <div className="content-wrapper">
        <div className="search-hero">
          <h2>Search</h2>
          <p>Type a free-text vibe like "small town crime series" and MoodFlix will find close matches.</p>

          <form className="search-form" onSubmit={handleSubmit}>
            <input
              className="search-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., small town crime series"
              aria-label="Semantic search query"
            />
            <button className="primary-button search-submit" type="submit" disabled={isLoading}>
              {isLoading ? "Searching..." : "Search"}
            </button>
          </form>
        </div>

        {error && (
          <div className="status-center">
            <p className="error-text">{error}</p>
          </div>
        )}

        {!error && isLoading && (
          <div className="status-center">
            <p className="loading-text">Finding the best matches...</p>
          </div>
        )}

        {!isLoading && hasSearched && results.length === 0 && (
          <div className="status-center">
            <p className="loading-text">No matching shows found. Try a different vibe or add more details.</p>
          </div>
        )}

        {!isLoading && results.length > 0 && (
          <div className="search-results-grid">
            {results.map((show) => {
              const reasonText = extractReason(show.ai_match_reason);
              const saved = typeof isSaved === "function" ? isSaved(show.title) : false;

              return (
              <article key={show.id} className="search-result-card">
                <button
                  className={`save-button ${saved ? "saved" : ""}`}
                  onClick={() => onToggleSave?.(show)}
                  disabled={savingTitle === show.title}
                >
                  {saved ? "❤️ Saved" : "♡ Save"}
                </button>
                {show.poster_url ? (
                  <img src={show.poster_url} alt={show.title} className="poster-image" />
                ) : (
                  <div className="poster-placeholder">No Image</div>
                )}

                <div className="search-card-content">
                  <h4>{show.title}</h4>
                  {show.vote_average != null && (
                    <p className="rating-line">
                      <span className="rating-star">★</span> {Number(show.vote_average).toFixed(1)}
                    </p>
                  )}
                  {reasonText && (
                    <p className="match-reason">
                      {reasonText}
                    </p>
                  )}
                  {show.overview && <p>{show.overview}</p>}
                </div>
              </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

export default SearchPage;
