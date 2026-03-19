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
      const data = await semanticSearch(trimmed, 10);
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
    <section className="content-section search-content-section">
      <div className="search-page">
        <section className="page-intro-band">
          <p className="page-eyebrow">Search</p>
          <h1 className="page-title">Search for shows you already have in mind</h1>
          <p className="page-subtitle">
            Look up titles, genres, or themes and browse focused matches.
          </p>
        </section>

        <section className="search-toolbar-section">
          <div className="search-toolbar-card">
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
        </section>

        <section className="search-results-section">
          <div className="search-results-header">
            <div>
              <h2>Top matches</h2>
              <p>Search results across the MoodFlix catalog.</p>
            </div>
            {!isLoading && results.length > 0 && (
              <span className="search-results-count">{results.length} results</span>
            )}
          </div>

          <div className="search-results-body">
            {!isLoading && !error && !hasSearched && (
              <div className="search-empty-state">
                <h3>Start with a title, genre, or theme</h3>
                <p>
                  Search the catalog to find shows that match something specific you already have in mind.
                </p>
              </div>
            )}

            {!isLoading && !error && hasSearched && results.length === 0 && (
              <div className="search-no-results-state">
                <h3>No matches found</h3>
                <p>Try another title, broader genre, or a different theme.</p>
              </div>
            )}

            {isLoading && (
              <div className="search-loading-state">
                <p className="loading-text">Finding the best matches...</p>
              </div>
            )}

            {error && (
              <div className="search-error-state">
                <p className="error-text">{error}</p>
              </div>
            )}

            {!isLoading && !error && results.length > 0 && (
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
      </div>
    </section>
  );
}

export default SearchPage;
