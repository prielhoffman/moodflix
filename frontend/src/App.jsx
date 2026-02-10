import "./App.css";

import { useEffect, useRef, useState } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";

import Header from "./components/Header";
import AuthModal from "./components/modals/AuthModal";
import UserInfoModal from "./components/modals/UserInfoModal";
import HomePage from "./pages/HomePage";
import RecommendPage from "./pages/RecommendPage";
import WatchlistPage from "./pages/WatchlistPage";

import {
  recommendShows,
  addToWatchlist,
  removeFromWatchlist,
  fetchWatchlist,
  hasAccessToken,
  login,
  register,
  fetchMe,
  logout,
} from "./api/moodflixApi";

function App() {
  const [recommendations, setRecommendations] = useState([]);
  const [watchlist, setWatchlist] = useState([]); // [{ title, poster_url }]
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [savingTitle, setSavingTitle] = useState(null);
  const [authUser, setAuthUser] = useState(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState("login"); // "login" | "register"
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [userInfoOpen, setUserInfoOpen] = useState(false);

  const carouselRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  /* Load watchlist on app startup */
  useEffect(() => {
    loadWatchlist();
  }, []);

  /* Close User Info modal on Escape */
  useEffect(() => {
    if (!userInfoOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") setUserInfoOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [userInfoOpen]);

  /* Clear recommendations when navigating away from /recommend */
  useEffect(() => {
    if (location.pathname !== "/recommend") {
      setRecommendations([]);
    }
  }, [location.pathname]);

  /* Load current user if token exists */
  useEffect(() => {
    if (!hasAccessToken()) return;

    fetchMe()
      .then((user) => {
        setAuthUser(user);
        loadWatchlist();
        if (authOpen) {
          closeAuthModal();
        }
      })
      .catch(() => {
        logout();
        setAuthUser(null);
      });
  }, []);

  async function loadWatchlist() {
    if (!hasAccessToken()) {
      setWatchlist([]);
      return;
    }

    try {
      const data = await fetchWatchlist();
      setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
    } catch (err) {
      console.error("Watchlist load failed", err);
    }
  }

  async function handleFormSubmit(preferences) {
    setIsLoading(true);
    setError(null);
    setRecommendations([]);

    try {
      const results = await recommendShows(preferences);
      setRecommendations(Array.isArray(results) ? results : []);
      await loadWatchlist();
    } catch (err) {
      console.error(err);
      setError("Something went wrong. Try again.");
    } finally {
      setIsLoading(false);
    }
  }

  function scrollCarousel(direction) {
    if (!carouselRef.current) return;

    carouselRef.current.scrollBy({
      left: direction === "left" ? -400 : 400,
      behavior: "smooth",
    });
  }

  /* Check if show exists in watchlist */
  function isSaved(title) {
    return watchlist.some((item) => item?.title === title);
  }

  function handleWatchlistError(err) {
    const msg = String(err?.message || "");

    if (msg.includes("HTTP 401") || msg.includes("HTTP 403")) {
      setError("Please log in to save to watchlist.");
      return;
    }

    setError("Could not update watchlist. Please try again.");
  }

  function openAuthModal(tab) {
    setAuthTab(tab || "login");
    setAuthError(null);
    setAuthOpen(true);
  }

  function closeAuthModal() {
    setAuthOpen(false);
    setAuthError(null);
    setAuthLoading(false);
    setAuthEmail("");
    setAuthPassword("");
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    let authSucceeded = false;

    try {
      if (authTab === "register") {
        await register(authEmail, authPassword);
      }

      await login(authEmail, authPassword);
      authSucceeded = true;

      try {
        const user = await fetchMe();
        setAuthUser(user);
      } catch (err) {
        console.error("fetchMe failed after auth", err);
      }

      try {
        await loadWatchlist();
      } catch (err) {
        console.error("Watchlist load failed after auth", err);
        setError("Logged in, but failed to load watchlist.");
      }
    } catch (err) {
      const msg = String(err?.message || "");
      if (msg.includes("HTTP 401")) {
        setAuthError("Invalid email or password.");
      } else if (msg.includes("HTTP 400") && authTab === "register") {
        setAuthError("Email already registered.");
      } else {
        setAuthError("Login failed. Please try again.");
      }
    } finally {
      if (authSucceeded) {
        closeAuthModal();
      }
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    logout();
    setAuthUser(null);
    setWatchlist([]);
    setError(null);
    setUserInfoOpen(false);
  }

  async function toggleSave(show) {
    const title = show?.title;

    if (!title) return;
    if (savingTitle) return;

    // Watchlist endpoints require JWT.
    if (!hasAccessToken()) {
      setError("Please log in to save to watchlist.");
      openAuthModal("login");
      return;
    }

    setSavingTitle(title);

    try {
      const data = isSaved(title)
        ? await removeFromWatchlist(title)
        : await addToWatchlist(show);

      setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
    } catch (err) {
      console.error(err);
      handleWatchlistError(err);
    } finally {
      setSavingTitle(null);
    }
  }

  async function handleRemoveFromWatchlist(title) {
    try {
      const data = await removeFromWatchlist(title);
      setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
    } catch (err) {
      console.error("Remove failed", err);
      handleWatchlistError(err);
    }
  }

  return (
    <div className="app">
      <Header
        userEmail={authUser?.email}
        onLogin={() => openAuthModal("login")}
        onRegister={() => openAuthModal("register")}
        onLogout={handleLogout}
        onEmailClick={() => setUserInfoOpen(true)}
      />

      <AuthModal
        open={authOpen}
        tab={authTab}
        email={authEmail}
        password={authPassword}
        error={authError}
        loading={authLoading}
        onClose={closeAuthModal}
        onTabChange={(tab) => {
          setAuthTab(tab);
          setAuthError(null);
        }}
        onEmailChange={setAuthEmail}
        onPasswordChange={setAuthPassword}
        onSubmit={handleAuthSubmit}
      />

      <UserInfoModal
        open={userInfoOpen}
        email={authUser?.email}
        onClose={() => setUserInfoOpen(false)}
      />

      <main className="page-container">
        <div className="page-inner">
          <Routes>
            <Route
              path="/"
              element={
                <HomePage
                  onStart={() => navigate("/recommend")}
                />
              }
            />

            <Route
              path="/recommend"
              element={
                <RecommendPage
                  onSubmitPreferences={handleFormSubmit}
                  isLoading={isLoading}
                  error={error}
                  recommendations={recommendations}
                  carouselRef={carouselRef}
                  onScrollCarousel={scrollCarousel}
                  isSaved={isSaved}
                  onToggleSave={toggleSave}
                  savingTitle={savingTitle}
                />
              }
            />

            <Route
              path="/watchlist"
              element={
                <WatchlistPage
                  authUser={authUser}
                  watchlist={watchlist}
                  onOpenLogin={() => openAuthModal("login")}
                  onRemoveFromWatchlist={handleRemoveFromWatchlist}
                />
              }
            />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default App;
