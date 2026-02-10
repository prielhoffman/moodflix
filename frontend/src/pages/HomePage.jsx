function HomePage({ onStart }) {
  return (
    <section className="hero-section">
      <div className="hero-content">
        <h1>MoodFlix 📺</h1>
        <p>Tell us how you feel. We’ll tell you what to binge.</p>

        <button className="primary-button" onClick={onStart}>
          Tell me what to binge
        </button>
      </div>
    </section>
  );
}

export default HomePage;
