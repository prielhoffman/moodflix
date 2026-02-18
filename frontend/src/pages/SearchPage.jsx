import { useState } from "react";
import { semanticSearch } from "../api/moodflixApi";

function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setIsLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const data = await semanticSearch(trimmed, 12);
      setResults(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError("Search failed. Please try again.");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="content-section">
      <div className="content-wrapper">
        <div className="search-hero">
          <h2>Search by Mood/Vibe</h2>
          <p>Describe the show you're looking for, and MoodFlix will find close matches.</p>

          <form className="search-form" onSubmit={handleSubmit}>
            <input
              className="search-input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe the show you're looking for..."
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
            {results.map((show) => (
              <article key={show.id} className="search-result-card">
                {show.poster_url ? (
                  <img src={show.poster_url} alt={show.title} className="poster-image" />
                ) : (
                  <div className="poster-placeholder">No Image</div>
                )}

                <div className="search-card-content">
                  <h4>{show.title}</h4>
                  {show.ai_match_reason && (
                    <p className="match-reason">
                      <strong>AI Match Reason:</strong> {show.ai_match_reason}
                    </p>
                  )}
                  {show.overview && <p>{show.overview}</p>}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default SearchPage;
