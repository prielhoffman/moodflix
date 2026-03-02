import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

const registerSchema = z
  .object({
    fullName: z.string().min(1, "Full name is required").max(255, "Full name is too long"),
    dateOfBirth: z.string().min(1, "Date of birth is required"),
    email: z.string().min(1, "Email is required").email("Enter a valid email address"),
    password: z.string().min(1, "Password is required"),
    confirmPassword: z.string().min(1, "Confirm password is required"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords must match",
    path: ["confirmPassword"],
  });

function validateDob(dateStr) {
  const dob = new Date(dateStr);
  const today = new Date();
  if (dob >= today) return "Date of birth must be in the past.";
  let age = today.getFullYear() - dob.getFullYear();
  const monthDiff = today.getMonth() - dob.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) age--;
  if (age < 13) return "You must be at least 13 years old to register.";
  if (age > 120) return "Invalid date of birth.";
  return null;
}

function AuthModal({
  open,
  tab,
  error: serverError,
  loading,
  message,
  onClose,
  onTabChange,
  onAuthStart,
  onAuthEnd,
  onAuthSuccess,
  onAuthError,
  loginApi,
  registerApi,
  fetchMeApi,
}) {
  const loginForm = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const registerForm = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      dateOfBirth: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  useEffect(() => {
    if (!open) return;
    loginForm.reset({ email: "", password: "" });
    registerForm.reset({
      fullName: "",
      dateOfBirth: "",
      email: "",
      password: "",
      confirmPassword: "",
    });
  }, [open]);

  async function onLoginSubmit(values) {
    onAuthError(null);
    onAuthStart?.();
    try {
      await loginApi(values.email, values.password);
      const user = await fetchMeApi();
      onAuthSuccess(user);
      onClose();
    } catch (err) {
      const msg = String(err?.message || "");
      if (msg.includes("HTTP 401")) {
        onAuthError("Invalid email or password.");
      } else if (
        msg.includes("temporarily busy") ||
        msg.includes("try again in a few minutes")
      ) {
        onAuthError("Server is temporarily busy. Please try again in a few minutes.");
      } else {
        onAuthError("Login failed. Please try again.");
      }
    } finally {
      onAuthEnd?.();
    }
  }

  async function onRegisterSubmit(values) {
    onAuthError(null);
    const dobError = validateDob(values.dateOfBirth);
    if (dobError) {
      onAuthError(dobError);
      return;
    }
    onAuthStart?.();
    try {
      await registerApi(values.fullName, values.dateOfBirth, values.email, values.password);
      await loginApi(values.email, values.password);
      const user = await fetchMeApi();
      onAuthSuccess(user);
      onClose();
    } catch (err) {
      const msg = String(err?.message || "");
      if (msg.includes("HTTP 400")) {
        onAuthError("Email already registered.");
      } else if (
        msg.includes("temporarily busy") ||
        msg.includes("try again in a few minutes")
      ) {
        onAuthError("Server is temporarily busy. Please try again in a few minutes.");
      } else {
        onAuthError("Registration failed. Please try again.");
      }
    } finally {
      onAuthEnd?.();
    }
  }

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal auth-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{tab === "login" ? "Login" : "Register"}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
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
            type="button"
            className={`tab-button ${tab === "login" ? "active" : ""}`}
            onClick={() => onTabChange("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={`tab-button ${tab === "register" ? "active" : ""}`}
            onClick={() => onTabChange("register")}
          >
            Register
          </button>
        </div>

        {tab === "login" ? (
          <form
            className="auth-form"
            onSubmit={loginForm.handleSubmit(onLoginSubmit)}
            noValidate
          >
            <div className="form-group">
              <label htmlFor="authEmail">Email</label>
              <input
                id="authEmail"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                {...loginForm.register("email")}
              />
              {loginForm.formState.errors.email && (
                <p className="field-error">{loginForm.formState.errors.email.message}</p>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="authPassword">Password</label>
              <input
                id="authPassword"
                type="password"
                autoComplete="current-password"
                maxLength={72}
                {...loginForm.register("password")}
              />
              {loginForm.formState.errors.password && (
                <p className="field-error">{loginForm.formState.errors.password.message}</p>
              )}
            </div>

            {serverError && <p className="error-text">{serverError}</p>}

            <button
              type="submit"
              className="primary-button"
              disabled={loading || loginForm.formState.isSubmitting}
            >
              {loading ? "Please wait..." : "Login"}
            </button>
          </form>
        ) : (
          <form
            className="auth-form"
            onSubmit={registerForm.handleSubmit(onRegisterSubmit)}
            noValidate
          >
            <div className="form-group">
              <label htmlFor="authFullName">Full name</label>
              <input
                id="authFullName"
                type="text"
                placeholder="Your full name"
                autoComplete="name"
                {...registerForm.register("fullName")}
              />
              {registerForm.formState.errors.fullName && (
                <p className="field-error">{registerForm.formState.errors.fullName.message}</p>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="authDateOfBirth">Date of birth</label>
              <input
                id="authDateOfBirth"
                type="date"
                {...registerForm.register("dateOfBirth")}
              />
              {registerForm.formState.errors.dateOfBirth && (
                <p className="field-error">{registerForm.formState.errors.dateOfBirth.message}</p>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="authEmailReg">Email</label>
              <input
                id="authEmailReg"
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                {...registerForm.register("email")}
              />
              {registerForm.formState.errors.email && (
                <p className="field-error">{registerForm.formState.errors.email.message}</p>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="authPasswordReg">Password</label>
              <input
                id="authPasswordReg"
                type="password"
                autoComplete="new-password"
                maxLength={72}
                {...registerForm.register("password")}
              />
              {registerForm.formState.errors.password && (
                <p className="field-error">{registerForm.formState.errors.password.message}</p>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="authConfirmPassword">Confirm password</label>
              <input
                id="authConfirmPassword"
                type="password"
                autoComplete="new-password"
                maxLength={72}
                {...registerForm.register("confirmPassword")}
              />
              {registerForm.formState.errors.confirmPassword && (
                <p className="field-error">
                  {registerForm.formState.errors.confirmPassword.message}
                </p>
              )}
            </div>

            {serverError && <p className="error-text">{serverError}</p>}

            <button
              type="submit"
              className="primary-button"
              disabled={loading || registerForm.formState.isSubmitting}
            >
              {loading ? "Please wait..." : "Register"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default AuthModal;
