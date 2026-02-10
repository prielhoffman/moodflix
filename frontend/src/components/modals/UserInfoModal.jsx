function UserInfoModal({ open, email, onClose }) {
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
          <p>
            <strong>Email:</strong> {email}
          </p>
        </div>
      </div>
    </div>
  );
}

export default UserInfoModal;
