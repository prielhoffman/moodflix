import "./App.css";

import { useEffect, useRef, useState } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";

import Header from "./components/Header";
import PreferenceForm from "./components/PreferenceForm";

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

  /* Debug: identify the topmost element capturing clicks */
  useEffect(() => {
    const handler = (e) => {
      const el = document.elementFromPoint(
        e.clientX ?? 0,
        e.clientY ?? 0
      );
      console.log("clicked", e.target, "topmost", el);
    };
    document.addEventListener("click", handler, true);
    return () => document.removeEventListener("click", handler, true);
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

      {authOpen && (
        <div className="modal-overlay" onClick={closeAuthModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{authTab === "login" ? "Login" : "Register"}</h3>
              <button className="modal-close" onClick={closeAuthModal}>
                ✕
              </button>
            </div>

            <div className="modal-tabs">
              <button
                className={`tab-button ${authTab === "login" ? "active" : ""}`}
                onClick={() => {
                  setAuthTab("login");
                  setAuthError(null);
                }}
              >
                Login
              </button>
              <button
                className={`tab-button ${authTab === "register" ? "active" : ""}`}
                onClick={() => {
                  setAuthTab("register");
                  setAuthError(null);
                }}
              >
                Register
              </button>
            </div>

            <form className="auth-form" onSubmit={handleAuthSubmit}>
              <div className="form-group">
                <label htmlFor="authEmail">Email</label>
                <input
                  id="authEmail"
                  type="email"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label htmlFor="authPassword">Password</label>
                <input
                  id="authPassword"
                  type="password"
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                />
              </div>

              {authError && <p className="error-text">{authError}</p>}

              <button type="submit" className="primary-button" disabled={authLoading}>
                {authLoading ? "Please wait..." : authTab === "login" ? "Login" : "Register"}
              </button>
            </form>
          </div>
        </div>
      )}

      {userInfoOpen && (
        <div
          className="modal-overlay"
          onClick={() => setUserInfoOpen(false)}
          onKeyDown={(e) => {
            if (e.key === "Escape") setUserInfoOpen(false);
          }}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>My Account</h3>
              <button
                className="modal-close"
                onClick={() => setUserInfoOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="user-info-body">
              <p>
                <strong>Email:</strong> {authUser?.email}
              </p>
            </div>
          </div>
        </div>
      )}

      <main className="page-container">
        <div className="page-inner">
          <Routes>
            {/* HOME */}
            <Route
              path="/"
              element={
                <section className="hero-section">
                  <div className="hero-content">
                    <h1>MoodFlix 📺</h1>
                    <p>Tell us how you feel. We’ll tell you what to binge.</p>

                    <button
                      className="primary-button"
                      onClick={() => navigate("/recommend")}
                    >
                      Tell me what to binge
                    </button>
                  </div>
                </section>
              }
            />

            {/* RECOMMEND */}
            <Route
              path="/recommend"
              element={
                <section className="content-section">
                  <div className="content-wrapper">
                    <div className="preferences-box">
                      <PreferenceForm onSubmit={handleFormSubmit} />
                    </div>

                    {isLoading && (
                      <div className="status-center">
                        <p className="loading-text">Loading...</p>
                      </div>
                    )}

                    {error && (
                      <div className="status-center">
                        <p className="error-text">{error}</p>
                      </div>
                    )}

                    {!isLoading && recommendations.length > 0 && (
                      <div className="results-section">
                        <h3>Recommended for you</h3>

                        <div className="carousel-wrapper">
                          <button
                            className="carousel-arrow"
                            onClick={() => scrollCarousel("left")}
                          >
                            ←
                          </button>

                          <div className="carousel-container" ref={carouselRef}>
                            {recommendations.map((show, i) => {
                              const saved = isSaved(show.title);

                              return (
                                <div key={i} className="poster-card">
                                  <button
                                    className={`save-button ${
                                      saved ? "saved" : ""
                                    }`}
                                    onClick={() => toggleSave(show)}
                                    disabled={savingTitle === show.title}
                                  >
                                    {saved ? "❤️ Saved" : "♡ Save"}
                                  </button>

                                  {show.poster_url ? (
                                    <img
                                      src={show.poster_url}
                                      alt={show.title}
                                      className="poster-image"
                                    />
                                  ) : (
                                    <div className="poster-placeholder">
                                      No Image
                                    </div>
                                  )}

                                  <div className="card-content">
                                    <h4>{show.title}</h4>

                                    {show.tmdb_rating && (
                                      <p>⭐ {show.tmdb_rating}</p>
                                    )}

                                    <p>{show.short_summary}</p>

                                    <p>
                                      <strong>Why:</strong>{" "}
                                      {show.recommendation_reason}
                                    </p>
                                  </div>
                                </div>
                              );
                            })}
                          </div>

                          <button
                            className="carousel-arrow"
                            onClick={() => scrollCarousel("right")}
                          >
                            →
                          </button>
                        </div>
                      </div>
                    )}

                  </div>
                </section>
              }
            />

            {/* WATCHLIST */}
            <Route
              path="/watchlist"
              element={
                <section className="content-section">
                  <div className="content-wrapper">
                    <h2>My Watchlist</h2>

                    {!authUser && (
                      <div className="empty-watchlist">
                        <p>Please log in to view your watchlist</p>
                        <button
                          className="primary-button"
                          onClick={() => openAuthModal("login")}
                        >
                          Login
                        </button>
                      </div>
                    )}

                    {authUser && watchlist.length === 0 && (
                      <div className="empty-watchlist">
                        <p>No saved shows yet</p>
                        <p>Start adding some TV series 📺</p>
                      </div>
                    )}

                    {authUser && watchlist.length > 0 && (
                      <div className="watchlist-grid">
                        {watchlist.map((show, i) => (
                          <div key={i} className="watchlist-card">
                            {show.poster_url ? (
                              <img
                                src={show.poster_url}
                                alt={show.title}
                                className="poster-image"
                              />
                            ) : (
                              <div className="poster-placeholder">
                                No Image
                              </div>
                            )}

                            <h4>{show.title}</h4>

                            <button
                              className="remove-button"
                              onClick={() =>
                                handleRemoveFromWatchlist(show.title)
                              }
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </section>
              }
            />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default App;
