import { Link, NavLink, useLocation } from "react-router-dom";
import UserMenu from "./UserMenu";
import "./Header.css";

function Header({
  authUser,
  onLogin,
  onRegister,
  onLogout,
  onOpenProfile,
  onGoToSemanticSearch,
}) {
  const location = useLocation();
  const isGuestHome = !authUser && location.pathname === "/";
  const onRecommendRoute = authUser && (location.pathname === "/" || location.pathname === "/recommend");
  const userDisplayName =
    authUser?.full_name?.trim() || authUser?.email || "Account";

  return (
    <header className={`header ${isGuestHome ? "header-guest" : ""}`}>
      <div className="header-inner">
        <Link to="/" className="logo-link" aria-label="Home">
          <h2 className="logo">MoodFlix</h2>
        </Link>

        {authUser && (
          <nav className="nav" aria-label="Primary">
            <NavLink
              to="/recommend"
              className={({ isActive }) => `nav-link ${isActive || onRecommendRoute ? "active" : ""}`}
            >
              Recommend
            </NavLink>
            <NavLink
              to="/search"
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              onClick={onGoToSemanticSearch}
            >
              Search
            </NavLink>
            <NavLink
              to="/watchlist"
              className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            >
              Watchlist
            </NavLink>
          </nav>
        )}

        <div className="auth-area">
          {authUser ? (
            <UserMenu
              userDisplayName={userDisplayName}
              onSemanticSearchClick={onGoToSemanticSearch}
              onProfileClick={onOpenProfile}
              onLogoutClick={onLogout}
            />
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
