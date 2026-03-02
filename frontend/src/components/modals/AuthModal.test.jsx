import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuthModal from "./AuthModal";

const defaultProps = {
  open: true,
  tab: "login",
  error: null,
  loading: false,
  message: null,
  onClose: vi.fn(),
  onTabChange: vi.fn(),
  onAuthSuccess: vi.fn(),
  onAuthError: vi.fn(),
  loginApi: vi.fn(),
  registerApi: vi.fn(),
  fetchMeApi: vi.fn(),
};

describe("AuthModal", () => {
  test("fills credentials and submits the login form", async () => {
    const user = userEvent.setup();
    const loginApi = vi.fn().mockResolvedValue(undefined);
    const fetchMeApi = vi.fn().mockResolvedValue({ id: 1, email: "person@example.com" });

    const { container } = render(
      <AuthModal
        {...defaultProps}
        loginApi={loginApi}
        fetchMeApi={fetchMeApi}
      />
    );

    await user.type(screen.getByLabelText(/email/i), "person@example.com");
    await user.type(screen.getByLabelText(/password/i), "secret123");
    const form = container.querySelector("form.auth-form");
    await user.click(within(form).getByRole("button", { name: /^login$/i }));

    expect(loginApi).toHaveBeenCalledWith("person@example.com", "secret123");
    expect(fetchMeApi).toHaveBeenCalled();
  });

  test("disables submit button while loading", () => {
    render(<AuthModal {...defaultProps} loading />);

    const submitBtn = screen.getByRole("button", { name: /please wait/i });
    expect(submitBtn).toBeDisabled();
  });

  test("shows validation errors when login fields are empty", async () => {
    const user = userEvent.setup();

    const { container } = render(<AuthModal {...defaultProps} />);

    const form = container.querySelector("form.auth-form");
    await user.click(within(form).getByRole("button", { name: /^login$/i }));

    expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    expect(defaultProps.loginApi).not.toHaveBeenCalled();
  });

  test("Register tab shows full name, DOB, confirm password fields", () => {
    const { container } = render(<AuthModal {...defaultProps} tab="register" />);

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/date of birth/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    const form = container.querySelector("form.auth-form");
    expect(within(form).getByRole("button", { name: /^register$/i })).toBeInTheDocument();
  });

  test("Register shows error when confirm password does not match", async () => {
    const user = userEvent.setup();

    const { container } = render(<AuthModal {...defaultProps} tab="register" />);

    await user.type(screen.getByLabelText(/full name/i), "Jane Doe");
    await user.type(screen.getByLabelText(/date of birth/i), "1990-01-15");
    await user.type(screen.getByLabelText(/email/i), "jane@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "secret123");
    await user.type(screen.getByLabelText(/confirm password/i), "different");

    const form = container.querySelector("form.auth-form");
    await user.click(within(form).getByRole("button", { name: /^register$/i }));

    expect(screen.getByText(/passwords must match/i)).toBeInTheDocument();
    expect(defaultProps.registerApi).not.toHaveBeenCalled();
  });
});
