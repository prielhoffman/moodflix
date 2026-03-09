function GuestFooter() {
  return (
    <footer className="guest-footer">
      <div className="guest-footer-inner">
        <div className="guest-footer-brand">
          <span className="guest-footer-logo">MoodFlix</span>
          <span className="guest-footer-tagline">AI-powered show discovery</span>
        </div>
        <div className="guest-footer-links">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="guest-footer-link"
          >
            GitHub
          </a>
          <a href="#" className="guest-footer-link">
            Docs
          </a>
        </div>
      </div>
    </footer>
  );
}

export default GuestFooter;
