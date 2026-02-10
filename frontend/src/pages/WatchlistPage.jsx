function WatchlistPage({
  authUser,
  watchlist,
  onOpenLogin,
  onRemoveFromWatchlist,
}) {
  return (
    <section className="content-section">
      <div className="content-wrapper">
        <h2>My Watchlist</h2>

        {!authUser && (
          <div className="empty-watchlist">
            <p>Please log in to view your watchlist</p>
            <button className="primary-button" onClick={onOpenLogin}>
              Login
            </button>
          </div>
        )}

        {authUser && watchlist.length === 0 && (
          <div className="empty-watchlist">
            <p>No saved shows yet</p>
            <p>Start adding some TV series 📺</p>
          </div>
        )}

        {authUser && watchlist.length > 0 && (
          <div className="watchlist-grid">
            {watchlist.map((show, i) => (
              <div key={i} className="watchlist-card">
                {show.poster_url ? (
                  <img
                    src={show.poster_url}
                    alt={show.title}
                    className="poster-image"
                  />
                ) : (
                  <div className="poster-placeholder">No Image</div>
                )}

                <h4>{show.title}</h4>

                <button
                  className="remove-button"
                  onClick={() => onRemoveFromWatchlist(show.title)}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default WatchlistPage;
