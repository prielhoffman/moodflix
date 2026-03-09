const MOODS = [
  { id: "chill", label: "Chill" },
  { id: "adrenaline", label: "Adrenaline" },
  { id: "curious", label: "Curious" },
];

function MoodSelector({ onMoodSelect, disabled }) {
  return (
    <section className="guest-mood-section" id="mood-section">
      <h2 className="guest-mood-title">What are you in the mood for tonight?</h2>
      <div className="guest-mood-pills">
        {MOODS.map((mood) => (
          <button
            key={mood.id}
            type="button"
            className="guest-mood-pill"
            onClick={() => onMoodSelect(mood.id)}
            disabled={disabled}
          >
            {mood.label}
          </button>
        ))}
      </div>
    </section>
  );
}

export default MoodSelector;
