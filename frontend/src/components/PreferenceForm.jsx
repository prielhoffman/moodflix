import { useState } from "react";

const SUPPORTED_GENRES = [
  "action",
  "animation",
  "comedy",
  "crime",
  "documentary",
  "drama",
  "family",
  "kids",
  "mystery",
  "news",
  "reality",
  "sci-fi",
  "soap",
  "talk",
  "war",
  "western",
];

const LANGUAGE_OPTIONS = [
  "English",
  "Hebrew",
  "Spanish",
  "German",
  "French",
  "Japanese",
  "Korean",
  "Hindi",
  "Arabic",
];

/*
  PreferenceForm collects the user's basic preferences
  and sends them to the parent component via onSubmit.
*/
function PreferenceForm({ onSubmit }) {
  // Form state: matches backend field names exactly
  const [formData, setFormData] = useState({
    age: "",
    mood: "chill",
    binge_preference: "binge",
    preferred_genres: [],
    language_preference: "",
    episode_length_preference: "any",
    watching_context: "alone",
    query: "",
  });

  // Handle changes for all inputs
  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
  }

  function handleGenreToggle(genre) {
    setFormData((prevData) => {
      const current = prevData.preferred_genres || [];
      const nextGenres = current.includes(genre)
        ? current.filter((g) => g !== genre)
        : [...current, genre];

      return {
        ...prevData,
        preferred_genres: nextGenres,
      };
    });
  }

  // Handle form submission
  function handleSubmit(event) {
    event.preventDefault();

    // Prepare data for backend:
    // convert age from string to number
    const preparedData = {
      ...formData,
      age: Number(formData.age),
    };

    const trimmedQuery = preparedData.query?.trim();
    if (!trimmedQuery) {
      delete preparedData.query;
    } else {
      preparedData.query = trimmedQuery;
    }

    if (!preparedData.language_preference) {
      delete preparedData.language_preference;
    }

    if (preparedData.episode_length_preference === "any") {
      delete preparedData.episode_length_preference;
    }

    // Send data to parent (App.jsx)
    onSubmit(preparedData);
  }

  return (
    <form className="preference-form" onSubmit={handleSubmit}>
      <h2>Your preferences</h2>

      {/* Mood selection */}
      <div className="form-group">
        <label htmlFor="mood">Mood</label>

        <select
          id="mood"
          name="mood"
          value={formData.mood}
          onChange={handleChange}
        >
          <option value="chill">Chill</option>
          <option value="happy">Happy</option>
          <option value="familiar">Familiar</option>
          <option value="focused">Focused</option>
          <option value="adrenaline">Adrenaline</option>
          <option value="dark">Dark</option>
          <option value="curious">Curious</option>
        </select>
      </div>

      {/* Age input */}
      <div className="form-group">
        <label htmlFor="age">Age</label>

        <input
          type="number"
          id="age"
          name="age"
          min="0"
          required
          value={formData.age}
          onChange={handleChange}
        />
      </div>

      {/* Binge preference */}
      <div className="form-group">
        <label>Binge preference</label>

        <div className="radio-group">
          <label>
            <input
              type="radio"
              name="binge_preference"
              value="binge"
              checked={formData.binge_preference === "binge"}
              onChange={handleChange}
            />
            Binge
          </label>

          <label>
            <input
              type="radio"
              name="binge_preference"
              value="short_series"
              checked={formData.binge_preference === "short_series"}
              onChange={handleChange}
            />
            Short series
          </label>
        </div>
      </div>

      {/* Advanced options */}
      <details className="advanced-options">
        <summary>Advanced preferences</summary>

        <div className="advanced-fields">
          <div className="form-group">
            <label>Preferred genres</label>
            <div className="genre-grid">
              {SUPPORTED_GENRES.map((genre) => (
                <label key={genre} className="genre-option">
                  <input
                    type="checkbox"
                    checked={formData.preferred_genres.includes(genre)}
                    onChange={() => handleGenreToggle(genre)}
                  />
                  <span>{genre}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="language_preference">Language</label>
            <select
              id="language_preference"
              name="language_preference"
              value={formData.language_preference}
              onChange={handleChange}
            >
              <option value="">Any</option>
              {LANGUAGE_OPTIONS.map((language) => (
                <option key={language} value={language}>
                  {language}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="episode_length_preference">Episode length</label>
            <select
              id="episode_length_preference"
              name="episode_length_preference"
              value={formData.episode_length_preference}
              onChange={handleChange}
            >
              <option value="any">Any</option>
              <option value="short">Short (30 min max)</option>
              <option value="long">Long (31+ min)</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="watching_context">Watching context</label>
            <select
              id="watching_context"
              name="watching_context"
              value={formData.watching_context}
              onChange={handleChange}
            >
              <option value="alone">Alone</option>
              <option value="partner">Partner</option>
              <option value="family">Family</option>
            </select>
          </div>
        </div>
      </details>

      {/* Optional semantic query */}
      <div className="form-group">
        <label htmlFor="query">Search (optional)</label>
        <input
          type="text"
          id="query"
          name="query"
          placeholder="e.g., funny workplace comedy"
          value={formData.query}
          onChange={handleChange}
        />
      </div>

      {/* Submit button */}
      <button type="submit" className="primary-button">
        Get recommendations
      </button>
    </form>
  );
}

export default PreferenceForm;
