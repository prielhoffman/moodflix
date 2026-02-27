function AuthModal({
  open,
  tab,
  fullName,
  dateOfBirth,
  email,
  password,
  error,
  loading,
  message,
  onClose,
  onTabChange,
  onFullNameChange,
  onDateOfBirthChange,
  onEmailChange,
  onPasswordChange,
  onSubmit,
}) {
  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{tab === "login" ? "Login" : "Register"}</h3>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {message && (
          <p className="auth-modal-message" role="alert">
            {message}
          </p>
        )}

        <div className="modal-tabs">
          <button
            className={`tab-button ${tab === "login" ? "active" : ""}`}
            onClick={() => onTabChange("login")}
          >
            Login
          </button>
          <button
            className={`tab-button ${tab === "register" ? "active" : ""}`}
            onClick={() => onTabChange("register")}
          >
            Register
          </button>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          {tab === "register" && (
            <>
              <div className="form-group">
                <label htmlFor="authFullName">Full name</label>
                <input
                  id="authFullName"
                  type="text"
                  required
                  minLength={1}
                  maxLength={255}
                  placeholder="Your full name"
                  value={fullName}
                  onChange={(e) => onFullNameChange(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label htmlFor="authDateOfBirth">Date of birth</label>
                <input
                  id="authDateOfBirth"
                  type="date"
                  required
                  value={dateOfBirth}
                  onChange={(e) => onDateOfBirthChange(e.target.value)}
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="authEmail">Email</label>
            <input
              id="authEmail"
              type="email"
              required
              value={email}
              onChange={(e) => onEmailChange(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="authPassword">Password</label>
            <input
              id="authPassword"
              type="password"
              required
              minLength={1}
              value={password}
              onChange={(e) => onPasswordChange(e.target.value)}
            />
          </div>

          {error && <p className="error-text">{error}</p>}

          <button type="submit" className="primary-button" disabled={loading}>
            {loading ? "Please wait..." : tab === "login" ? "Login" : "Register"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AuthModal;
