import "./App.css";

import { useState } from "react";

// Import the PreferenceForm component
import PreferenceForm from "./components/PreferenceForm";

function App() {
  // Controls whether we show Home screen or Form screen
  const [showForm, setShowForm] = useState(false);

  // Called when the form is submitted
  function handleFormSubmit(preferences) {
    // For now, just log the data to the console
    console.log("Submitted preferences:", preferences);
  }

  return (
    <div className="app-container">
      {!showForm ? (
        // ---------------- Home Screen ----------------
        <div className="home-screen">
          <h1>MoodFlix 📺</h1>

          <p>Tell us how you feel. We’ll tell you what to binge.</p>

          <button
            onClick={() => setShowForm(true)}
            className="primary-button"
          >
            Tell me what to binge
          </button>
        </div>
      ) : (
        // ---------------- Form Screen ----------------
        <div className="form-screen">
          {/* Back button: returns to Home screen */}
          <button
            onClick={() => setShowForm(false)}
            className="back-button"
          >
            ← Back
          </button>

          {/* Preference form */}
          <PreferenceForm onSubmit={handleFormSubmit} />
        </div>
      )}
    </div>
  );
}

export default App;
