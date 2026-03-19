import { Link } from "react-router-dom";

function WatchlistPage({
  authUser,
  watchlist,
  onOpenLogin,
  onRemoveFromWatchlist,
}) {
  const savedCount = Array.isArray(watchlist) ? watchlist.length : 0;

  return (
    <section className="content-section watchlist-content-section">
      <div className="watchlist-page">
        <section className="page-intro-band">
          <p className="page-eyebrow">Favorites</p>
          <h1 className="page-title">Your favorites</h1>
          <p className="page-subtitle">
            Keep track of the series you want to come back to later.
          </p>
        </section>

        <section className="watchlist-summary-row">
          <div className="watchlist-summary-card">
            <span className="watchlist-summary-label">Favorite shows</span>
            <strong className="watchlist-summary-value">{savedCount}</strong>
          </div>
        </section>

        <section className="watchlist-results-section">
          <div className="watchlist-results-header">
            <div>
              <h2>Your collection</h2>
              <p>Shows you liked from recommendations and search.</p>
            </div>
          </div>

          <div className="watchlist-results-body">
            {!authUser && (
              <div className="watchlist-empty-state">
                <h3>Please log in to view your favorites</h3>
                <button className="primary-button watchlist-empty-action" onClick={onOpenLogin}>
                  Login
                </button>
              </div>
            )}

            {authUser && savedCount === 0 && (
              <div className="watchlist-empty-state">
                <h3>Your favorites are empty</h3>
                <p>Like shows from recommendations or search to build your collection.</p>
                <div className="watchlist-empty-actions">
                  <Link className="primary-button watchlist-empty-action" to="/recommend">
                    Browse recommendations
                  </Link>
                  <Link className="watchlist-secondary-link" to="/search">
                    Search by description
                  </Link>
                </div>
              </div>
            )}

            {authUser && savedCount > 0 && (
              <div className="watchlist-grid">
                {watchlist.map((show, i) => (
                  <article key={show.show_id ?? show.title ?? i} className="watchlist-card">
                    {show.poster_url ? (
                      <img
                        src={show.poster_url}
                        alt={show.title}
                        className="poster-image"
                      />
                    ) : (
                      <div className="poster-placeholder">No Image</div>
                    )}

                    <div className="watchlist-card-content">
                      <h3>{show.title}</h3>
                      <p>In favorites</p>
                      <button
                        className="remove-button"
                        onClick={() => onRemoveFromWatchlist(show)}
                      >
                        Remove from favorites
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </section>
  );
}

export default WatchlistPage;
