import { useState } from "react";

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
  });

  // Handle changes for all inputs
  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((prevData) => ({
      ...prevData,
      [name]: value,
    }));
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

      {/* Submit button */}
      <button type="submit" className="primary-button">
        Get recommendations
      </button>
    </form>
  );
}

export default PreferenceForm;
