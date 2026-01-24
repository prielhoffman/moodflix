import { NavLink } from "react-router-dom";
import "./Header.css";

function Header() {
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
      </div>
    </header>
  );
}

export default Header;
