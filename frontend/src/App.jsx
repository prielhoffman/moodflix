import "./App.css";

import { useEffect, useRef, useState } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";

import Header from "./components/Header";
import AuthModal from "./components/modals/AuthModal";
import UserInfoModal from "./components/modals/UserInfoModal";
import HomePage from "./pages/HomePage";
import RecommendPage from "./pages/RecommendPage";
import SearchPage from "./pages/SearchPage";
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
  const [lastRecommendationInput, setLastRecommendationInput] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [savingTitle, setSavingTitle] = useState(null);
  const [authUser, setAuthUser] = useState(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState("login"); // "login" | "register"
  const [authContextMessage, setAuthContextMessage] = useState(null); // e.g. why modal was opened (watchlist)
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

  /* Close modals on Escape */
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key !== "Escape") return;
      if (userInfoOpen) setUserInfoOpen(false);
      if (authOpen) closeAuthModal();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [userInfoOpen, authOpen]);

  /* Clear recommendations when leaving the recommend view (/ when auth, /recommend) */
  useEffect(() => {
    const onRecommendView =
      location.pathname === "/recommend" ||
      (location.pathname === "/" && authUser);
    if (!onRecommendView) {
      setRecommendations([]);
    }
  }, [location.pathname, authUser]);

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
    setLastRecommendationInput(preferences);

    try {
      const results = await recommendShows(preferences);
      setRecommendations(Array.isArray(results) ? results : []);
      await loadWatchlist();
    } catch (err) {
      console.error(err);
      setError(err?.message || "Recommendations temporarily unavailable. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  /** Home quick flow: mood or search query → POST /recommend → navigate to /recommend with results. */
  async function handleQuickRecommend({ mood, query, guestFamilySafe }) {
    setIsLoading(true);
    setError(null);
    setRecommendations([]);

    const payload = {
      mood: mood || "chill",
      binge_preference: "binge",
      preferred_genres: [],
      episode_length_preference: "any",
      watching_context: "alone",
      ...(query && query.trim() ? { query: query.trim() } : {}),
    };
    if (!authUser && typeof guestFamilySafe === "boolean") {
      payload.guest_family_safe = guestFamilySafe;
    }
    setLastRecommendationInput(payload);

    try {
      const results = await recommendShows(payload);
      setRecommendations(Array.isArray(results) ? results : []);
      await loadWatchlist();
      navigate("/recommend");
    } catch (err) {
      console.error(err);
      setError(err?.message || "Recommendations temporarily unavailable. Please try again.");
      navigate("/recommend");
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

  /* Check if show or title exists in watchlist (by show_id or title) */
  function isSaved(showOrTitle) {
    if (showOrTitle == null) return false;
    if (typeof showOrTitle === "string") {
      return watchlist.some((item) => item?.title === showOrTitle);
    }
    const id = showOrTitle.id ?? showOrTitle.show_id;
    const title = showOrTitle.title;
    return watchlist.some(
      (item) =>
        (id != null && item?.show_id === id) || item?.title === title
    );
  }

  function handleWatchlistError(err) {
    const status = err?.status;
    const msg = String(err?.message || "").trim();

    if (status === 401 || status === 403 || msg.toLowerCase().includes("credentials") || msg.toLowerCase().includes("unauthorized")) {
      setAuthContextMessage("Please log in or register to save to your watchlist.");
      openAuthModal("login");
      return;
    }

    if (status === 404 && msg) {
      setError(msg);
      return;
    }
    setError(msg || "Could not update watchlist. Please try again.");
  }

  function openAuthModal(tab, contextMessage = null) {
    setAuthTab(tab || "login");
    setAuthError(null);
    setAuthContextMessage(contextMessage ?? null);
    setAuthOpen(true);
  }

  function closeAuthModal() {
    setAuthOpen(false);
    setAuthError(null);
    setAuthContextMessage(null);
    setAuthLoading(false);
  }

  function handleAuthSuccess(user) {
    setAuthUser(user);
    loadWatchlist().catch(() => setError("Logged in, but failed to load watchlist."));
    closeAuthModal();
    navigate("/");
  }

  function handleAuthError(message) {
    setAuthError(message);
  }

  function handleLogout() {
    logout();
    setAuthUser(null);
    setWatchlist([]);
    setError(null);
    setUserInfoOpen(false);
  }

  /** Clear recommendation state before leaving recommend flow. */
  function handleGoToSemanticSearch() {
    setRecommendations([]);
    setError(null);
  }

  async function toggleSave(show) {
    const title = show?.title;
    if (!title) return;
    if (savingTitle) return;

    if (!hasAccessToken()) {
      openAuthModal("login", "Please log in or register to save to your watchlist.");
      return;
    }

    const id = show.id ?? show.show_id;
    const hasValidId = id != null && Number(id) > 0;
    const hasTitle = title && String(title).trim() !== "";
    if (!isSaved(show) && !hasValidId && !hasTitle) {
      setError("This show isn't in the catalog and can't be added to the watchlist.");
      return;
    }

    const prevWatchlist = watchlist;
    const willRemove = isSaved(show);

    setSavingTitle(title);

    if (willRemove) {
      setWatchlist((prev) => prev.filter((item) => {
        const itemId = item?.show_id ?? item?.id;
        const matchId = id != null && itemId != null && Number(itemId) === Number(id);
        const matchTitle = item?.title === title;
        return !(matchId || matchTitle);
      }));
    } else {
      setWatchlist((prev) => [...prev, { show_id: hasValidId ? id : null, title: show.title, poster_url: show.poster_url ?? null }]);
    }

    try {
      if (willRemove) {
        const data = await removeFromWatchlist(show);
        setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
      } else {
        const data = await addToWatchlist(show);
        setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
      }
    } catch (err) {
      console.error(err);
      setWatchlist(prevWatchlist);
      handleWatchlistError(err);
    } finally {
      setSavingTitle(null);
    }
  }

  async function handleRemoveFromWatchlist(item) {
    try {
      const data = await removeFromWatchlist(item);
      setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
    } catch (err) {
      console.error("Remove failed", err);
      handleWatchlistError(err);
    }
  }

  return (
    <div className="app">
      <Header
        authUser={authUser}
        onLogin={() => openAuthModal("login")}
        onRegister={() => openAuthModal("register")}
        onLogout={handleLogout}
        onOpenProfile={() => setUserInfoOpen(true)}
        onGoToSemanticSearch={handleGoToSemanticSearch}
      />

      <AuthModal
        open={authOpen}
        tab={authTab}
        error={authError}
        loading={authLoading}
        message={authContextMessage}
        onClose={closeAuthModal}
        onTabChange={(tab) => {
          setAuthTab(tab);
          setAuthError(null);
        }}
        onAuthStart={() => setAuthLoading(true)}
        onAuthEnd={() => setAuthLoading(false)}
        onAuthSuccess={handleAuthSuccess}
        onAuthError={handleAuthError}
        loginApi={login}
        registerApi={register}
        fetchMeApi={fetchMe}
      />

      <UserInfoModal
        open={userInfoOpen}
        fullName={authUser?.full_name}
        email={authUser?.email}
        dateOfBirth={authUser?.date_of_birth}
        onClose={() => setUserInfoOpen(false)}
      />

      <main className="page-container">
        <div className="page-inner">
          <Routes>
            <Route
              path="/"
              element={
                <HomePage
                  authUser={authUser}
                  onQuickRecommend={handleQuickRecommend}
                  isLoading={isLoading}
                  onSubmitPreferences={handleFormSubmit}
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

            <Route
              path="/search"
              element={
                <SearchPage
                  isSaved={isSaved}
                  onToggleSave={toggleSave}
                  savingTitle={savingTitle}
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
