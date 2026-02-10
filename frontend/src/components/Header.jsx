import { NavLink } from "react-router-dom";
import "./Header.css";

function Header({ userEmail, onLogin, onRegister, onLogout, onEmailClick }) {
  return (
    <header className="header">
      <div className="header-inner">
        {/* Logo */}
        <h2 className="logo">MoodFlix 📺</h2>

        {/* Navigation */}
        <nav className="nav">
          <NavLink to="/" className="nav-link">
            Home
          </NavLink>

          <NavLink to="/recommend" className="nav-link">
            Recommend
          </NavLink>

          <NavLink to="/watchlist" className="nav-link">
            Watchlist
          </NavLink>
        </nav>

        <div className="auth-area">
          {userEmail ? (
            <>
              <button
                className="auth-email-button"
                onClick={onEmailClick}
                aria-label="View account info"
              >
                {userEmail}
              </button>
              <button className="auth-button" onClick={onLogout}>
                Logout
              </button>
            </>
          ) : (
            <>
              <button className="auth-button" onClick={onLogin}>
                Login
              </button>
              <button className="auth-button secondary" onClick={onRegister}>
                Register
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
