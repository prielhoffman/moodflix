function UserInfoModal({ open, fullName, email, dateOfBirth, onClose }) {
  if (!open) return null;

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>My Account</h3>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="user-info-body">
          {fullName && (
            <p>
              <strong>Name:</strong> {fullName}
            </p>
          )}
          <p>
            <strong>Email:</strong> {email}
          </p>
          {dateOfBirth && (
            <p>
              <strong>Date of birth:</strong> {dateOfBirth}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default UserInfoModal;
