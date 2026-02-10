import { useState } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuthModal from "./AuthModal";

function AuthModalHarness({ onSubmit = vi.fn(), loading = false }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <AuthModal
      open
      tab="login"
      email={email}
      password={password}
      error={null}
      loading={loading}
      onClose={vi.fn()}
      onTabChange={vi.fn()}
      onEmailChange={setEmail}
      onPasswordChange={setPassword}
      onSubmit={onSubmit}
    />
  );
}

describe("AuthModal", () => {
  test("fills credentials and submits the form", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn((event) => event.preventDefault());

    const { container } = render(<AuthModalHarness onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/email/i), "person@example.com");
    await user.type(screen.getByLabelText(/password/i), "secret123");
    const form = container.querySelector("form");
    expect(form).not.toBeNull();
    await user.click(within(form).getByRole("button", { name: /^login$/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  test("disables submit button while loading", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<AuthModalHarness onSubmit={onSubmit} loading />);

    const submitBtn = screen.getByRole("button", { name: /please wait/i });
    expect(submitBtn).toBeDisabled();

    await user.click(submitBtn);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
