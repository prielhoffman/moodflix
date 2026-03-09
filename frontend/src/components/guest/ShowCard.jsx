function ShowCard({ show, className = "" }) {
  const title = show?.title ?? "Unknown";
  const posterUrl = show?.poster_url;
  const rating = show?.tmdb_rating;

  return (
    <div className={`show-card ${className}`}>
      <div className="show-card-poster">
        {posterUrl ? (
          <img src={posterUrl} alt={title} loading="lazy" />
        ) : (
          <div className="show-card-placeholder">No Image</div>
        )}
      </div>
      <div className="show-card-overlay">
        <h4 className="show-card-title">{title}</h4>
        {rating != null && (
          <span className="show-card-rating">★ {Number(rating).toFixed(1)}</span>
        )}
      </div>
    </div>
  );
}

export default ShowCard;
