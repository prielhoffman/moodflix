import { useState } from "react";

// App is the root component of the frontend.
// It decides which screen to show: Home or Preference Form.
function App() {
  // Controls whether the user has started the flow
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="app-container">
      {!showForm ? (
        // ---------------- Home / Intro Screen ----------------
        <div className="home-screen">
          <h1>MoodFlix</h1>

          <p>
            Tell us how you feel. We’ll tell you what to binge.
          </p>

          <button
            onClick={() => setShowForm(true)}
            className="primary-button"
          >
            Tell me what to binge
          </button>
        </div>
      ) : (
        // ---------------- Form Screen (placeholder for now) ----------------
        <div className="form-screen">
          <h2>Your preferences</h2>
          <p>The recommendation form will go here.</p>
        </div>
      )}
    </div>
  );
}

export default App;
