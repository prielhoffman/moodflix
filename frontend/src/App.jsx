import "./App.css";

import { useState } from "react";

function App() {
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="app-container">
      {!showForm ? (
        // Home Screen
        <div className="home-screen">
          <h1>MoodFlix 📺</h1>

          <p>Tell us how you feel. We’ll tell you what to binge.</p>

          <button
            onClick={() => setShowForm(true)}
            className="primary-button"
          >
            Let's go!
          </button>
        </div>
      ) : (
        // Placeholder for now
        <div className="form-screen">
          <button
            onClick={() => setShowForm(false)}
            className="back-button"
          >
            ← Back
          </button>

          <h2>Your preferences</h2>
          <p>The recommendation form will go here.</p>
        </div>
      )}
    </div>
  );
}

export default App;
