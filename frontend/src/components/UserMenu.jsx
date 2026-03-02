import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import "./UserMenu.css";

function UserMenu({
  userDisplayName,
  onSemanticSearchClick,
  onProfileClick,
  onLogoutClick,
}) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);
  const panelRef = useRef(null);

  function close() {
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;

    function handleClickOutside(e) {
      const trigger = triggerRef.current;
      const panel = panelRef.current;
      if (trigger?.contains(e.target) || panel?.contains(e.target)) {
        return;
      }
      close();
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  useEffect(() => {
    if (!open) return;

    function handleEscape(e) {
      if (e.key === "Escape") close();
    }

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [open]);

  const triggerRect = triggerRef.current?.getBoundingClientRect?.();
  const showPanel = open && triggerRect;

  const menuPanel = showPanel
    ? createPortal(
        <div
          ref={panelRef}
          className="user-menu-panel"
          role="menu"
          aria-label="User menu"
          style={{
            position: "fixed",
            top: triggerRect.bottom + 6,
            left: triggerRect.left,
            minWidth: Math.max(triggerRect.width, 200),
          }}
        >
          <Link
            to="/watchlist"
            className="user-menu-item"
            role="menuitem"
            onClick={close}
          >
            My Watchlist
          </Link>
          <Link
            to="/search"
            className="user-menu-item"
            role="menuitem"
            onClick={() => {
              close();
              onSemanticSearchClick?.();
            }}
          >
            Semantic Search
          </Link>
          <button
            type="button"
            className="user-menu-item"
            role="menuitem"
            onClick={() => {
              close();
              onProfileClick?.();
            }}
          >
            User Profile
          </button>
          <button
            type="button"
            className="user-menu-item user-menu-item-logout"
            role="menuitem"
            onClick={() => {
              close();
              onLogoutClick?.();
            }}
          >
            Logout
          </button>
        </div>,
        document.body
      )
    : null;

  return (
    <div className="user-menu">
      <button
        ref={triggerRef}
        type="button"
        className="user-menu-trigger"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Open user menu"
      >
        {userDisplayName}
      </button>
      {menuPanel}
    </div>
  );
}

export default UserMenu;
