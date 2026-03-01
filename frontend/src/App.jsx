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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [savingTitle, setSavingTitle] = useState(null);
  const [authUser, setAuthUser] = useState(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState("login"); // "login" | "register"
  const [authContextMessage, setAuthContextMessage] = useState(null); // e.g. why modal was opened (watchlist)
  const [authFullName, setAuthFullName] = useState("");
  const [authDateOfBirth, setAuthDateOfBirth] = useState("");
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
      setError(err?.message || "Recommendations temporarily unavailable. Please try again.");
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
    const msg = String(err?.message || "");

    if (msg.includes("HTTP 401") || msg.includes("HTTP 403")) {
      setAuthContextMessage("Please log in or register to save to your watchlist.");
      openAuthModal("login");
      return;
    }

    setError("Could not update watchlist. Please try again.");
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
    setAuthFullName("");
    setAuthDateOfBirth("");
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
        // Client-side validation: user must be at least 13
        const dob = new Date(authDateOfBirth);
        const today = new Date();
        let age = today.getFullYear() - dob.getFullYear();
        const monthDiff = today.getMonth() - dob.getMonth();
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
          age--;
        }
        if (age < 13) {
          setAuthError("You must be at least 13 years old to register.");
          setAuthLoading(false);
          return;
        }
        if (dob >= today) {
          setAuthError("Date of birth must be in the past.");
          setAuthLoading(false);
          return;
        }
        await register(authFullName, authDateOfBirth, authEmail, authPassword);
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

    if (!hasAccessToken()) {
      openAuthModal("login", "Please log in or register to save to your watchlist.");
      return;
    }

    setSavingTitle(title);

    try {
      if (isSaved(show)) {
        const data = await removeFromWatchlist(show);
        setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
      } else {
        const id = show.id ?? show.show_id;
        if (id == null || Number(id) <= 0) {
          setError("This show isn't in the catalog and can't be added to the watchlist.");
          return;
        }
        const data = await addToWatchlist(show);
        setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
      }
    } catch (err) {
      console.error(err);
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
        userEmail={authUser?.email}
        onLogin={() => openAuthModal("login")}
        onRegister={() => openAuthModal("register")}
        onLogout={handleLogout}
        onEmailClick={() => setUserInfoOpen(true)}
      />

      <AuthModal
        open={authOpen}
        tab={authTab}
        fullName={authFullName}
        dateOfBirth={authDateOfBirth}
        email={authEmail}
        password={authPassword}
        error={authError}
        loading={authLoading}
        message={authContextMessage}
        onClose={closeAuthModal}
        onTabChange={(tab) => {
          setAuthTab(tab);
          setAuthError(null);
        }}
        onFullNameChange={setAuthFullName}
        onDateOfBirthChange={setAuthDateOfBirth}
        onEmailChange={setAuthEmail}
        onPasswordChange={setAuthPassword}
        onSubmit={handleAuthSubmit}
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
