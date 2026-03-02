import { Link } from "react-router-dom";
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
  const userDisplayName =
    authUser?.full_name?.trim() || authUser?.email || "Account";

  return (
    <header className="header">
      <div className="header-inner">
        <Link to="/" className="logo-link" aria-label="Home - Recommendations">
          <h2 className="logo">MoodFlix 📺</h2>
        </Link>

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
