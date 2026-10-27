import { FormEvent, ReactNode, useState } from "react";

import logo from "../../assets/image/logo.png";
import { ProtectedRoute } from "../../components/layout/ProtectedRoute";
import { RoleGate } from "../../components/layout/RoleGate";
import { SchoolOnboarding } from "../schools/SchoolOnboarding";
import { AdminVerificationQueue } from "../schools/AdminVerificationQueue";
import { DonationWorkspace } from "../donations/DonationWorkspace";
import type {
  AuthResponse,
  AuthState,
  LoginCredentials,
  RegistrationPayload,
} from "./auth-service";

type AuthView = "login" | "register" | "forgot";

type AuthContentProps = {
  auth: AuthState | null;
  onAuthenticated: (response: AuthResponse) => void;
  onLogout: () => Promise<void>;
  onLogin: (credentials: LoginCredentials) => Promise<AuthResponse>;
  onRegister: (payload: RegistrationPayload) => Promise<AuthResponse>;
};

export function AuthContent({
  auth,
  onAuthenticated,
  onLogout,
  onLogin,
  onRegister,
}: AuthContentProps) {
  const [view, setView] = useState<AuthView>("login");
  const [notice, setNotice] = useState<string | null>(null);

  if (auth) {
    return (
      <ProtectedRoute auth={auth}>
        <Dashboard auth={auth} onLogout={onLogout} />
      </ProtectedRoute>
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-story" aria-labelledby="brand-title">
        <div className="brand-lockup">
          <span className="brand-mark">
            <img src={logo} alt="Shiksha Setu logo" />
          </span>
          <span>Shiksha Setu</span>
        </div>
        <div className="story-content">
          <p className="eyebrow">Bridging resources · empowering girls</p>
          <h1 id="brand-title">Every child deserves the chance to learn.</h1>
          <p>
            A trusted bridge between schools with urgent needs and people ready
            to help. Together, we make every contribution count.
          </p>
        </div>
        <div className="story-proof">
          <div>
            <strong>01</strong>
            <span>Verified school needs</span>
          </div>
          <div>
            <strong>02</strong>
            <span>Transparent resource journeys</span>
          </div>
          <div>
            <strong>03</strong>
            <span>More opportunity for girls</span>
          </div>
        </div>
      </section>

      <section className="auth-panel" aria-label="Account access">
        <div className="mobile-brand brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            SS
          </span>
          <span>Shiksha Setu</span>
        </div>
        {notice && <div className="notice success">{notice}</div>}
        {view === "login" && (
          <LoginScreen
            onLogin={onLogin}
            onAuthenticated={onAuthenticated}
            onCreateAccount={() => {
              setNotice(null);
              setView("register");
            }}
            onForgotPassword={() => {
              setNotice(null);
              setView("forgot");
            }}
          />
        )}
        {view === "register" && (
          <RegisterScreen
            onRegister={onRegister}
            onAuthenticated={onAuthenticated}
            onSignIn={() => {
              setNotice(null);
              setView("login");
            }}
          />
        )}
        {view === "forgot" && (
          <ForgotPasswordScreen
            onBackToSignIn={() => {
              setNotice(null);
              setView("login");
            }}
          />
        )}
      </section>
    </main>
  );
}

function LoginScreen({
  onLogin,
  onAuthenticated,
  onCreateAccount,
  onForgotPassword,
}: {
  onLogin: (credentials: LoginCredentials) => Promise<AuthResponse>;
  onAuthenticated: (response: AuthResponse) => void;
  onCreateAccount: () => void;
  onForgotPassword: () => void;
}) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await onLogin({
        identifier,
        password,
      });
      onAuthenticated(response);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthCard
      eyebrow="Welcome back"
      title="Sign in to your account"
      subtitle="Continue your work of connecting resources to possibility."
    >
      <form className="auth-form" onSubmit={submit}>
        <FormField
          id="login-identifier"
          label="Email or username"
          type="text"
          value={identifier}
          onChange={setIdentifier}
          placeholder="you@example.com"
          autoComplete="username"
          required
        />
        <div className="field-group">
          <div className="field-label-row">
            <label htmlFor="login-password">Password</label>
            <button type="button" className="text-button" onClick={onForgotPassword}>
              Forgot password?
            </button>
          </div>
          <PasswordInput
            id="login-password"
            value={password}
            onChange={setPassword}
            showPassword={showPassword}
            onToggle={() => setShowPassword((current) => !current)}
            autoComplete="current-password"
          />
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={remember}
            onChange={(event) => setRemember(event.target.checked)}
          />
          <span>Keep me signed in on this device</span>
        </label>
        {error && <FormError message={error} />}
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing you in…" : "Sign in"}
          <span aria-hidden="true">→</span>
        </button>
      </form>
      <p className="switch-prompt">
        New to Shiksha Setu?{" "}
        <button type="button" className="text-button strong" onClick={onCreateAccount}>
          Create an account
        </button>
      </p>
      <p className="form-footnote">
        By continuing, you agree to our community guidelines and privacy policy.
      </p>
    </AuthCard>
  );
}

function RegisterScreen({
  onRegister,
  onAuthenticated,
  onSignIn,
}: {
  onRegister: (payload: RegistrationPayload) => Promise<AuthResponse>;
  onAuthenticated: (response: AuthResponse) => void;
  onSignIn: () => void;
}) {
  const [form, setForm] = useState({
    email: "",
    username: "",
    password: "",
    role: "donor" as RegistrationPayload["role"],
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function update(field: keyof typeof form, value: string): void {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await onRegister(form);
      onAuthenticated(response);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Unable to create your account.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthCard
      eyebrow="Join the bridge"
      title="Create your account"
      subtitle="Choose how you want to contribute to more equitable education."
    >
      <form className="auth-form" onSubmit={submit}>
        <div className="role-grid" aria-label="Account type">
          {[
            ["donor", "Donor", "Share useful resources"],
            ["school", "School", "Publish verified needs"],
            ["volunteer", "Volunteer", "Help coordinate impact"],
          ].map(([value, label, description]) => (
            <label className={`role-option ${form.role === value ? "selected" : ""}`} key={value}>
              <input
                type="radio"
                name="role"
                value={value}
                checked={form.role === value}
                onChange={(event) => update("role", event.target.value)}
              />
              <span className="role-copy">
                <strong>{label}</strong>
                <small>{description}</small>
              </span>
            </label>
          ))}
        </div>
        <div className="form-grid">
          <FormField
            id="register-username"
            label="Username"
            type="text"
            value={form.username}
            onChange={(value) => update("username", value)}
            placeholder="your-name"
            autoComplete="username"
            required
          />
          <FormField
            id="register-email"
            label="Email address"
            type="email"
            value={form.email}
            onChange={(value) => update("email", value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </div>
        <div className="field-group">
          <label htmlFor="register-password">Password</label>
          <PasswordInput
            id="register-password"
            value={form.password}
            onChange={(value) => update("password", value)}
            showPassword={showPassword}
            onToggle={() => setShowPassword((current) => !current)}
            autoComplete="new-password"
          />
          <small className="field-hint">Use at least 12 characters.</small>
        </div>
        {error && <FormError message={error} />}
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating your account…" : "Create account"}
          <span aria-hidden="true">→</span>
        </button>
      </form>
      <p className="switch-prompt">
        Already part of the bridge?{" "}
        <button type="button" className="text-button strong" onClick={onSignIn}>
          Sign in
        </button>
      </p>
    </AuthCard>
  );
}

function ForgotPasswordScreen({ onBackToSignIn }: { onBackToSignIn: () => void }) {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <AuthCard
      eyebrow="Account recovery"
      title={submitted ? "Check your inbox" : "Reset your password"}
      subtitle={
        submitted
          ? `If an account exists for ${email}, we’ll send recovery instructions shortly.`
          : "Enter your email and we’ll help you get back to your work."
      }
    >
      {!submitted ? (
        <form className="auth-form" onSubmit={submit}>
          <FormField
            id="forgot-email"
            label="Email address"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
          <button className="primary-button" type="submit">
            Send recovery link <span aria-hidden="true">→</span>
          </button>
        </form>
      ) : (
        <div className="recovery-confirmation" role="status">
          <span className="confirmation-icon" aria-hidden="true">
            ✓
          </span>
          <p>For your safety, we never reveal whether an email is registered.</p>
        </div>
      )}
      <button type="button" className="back-button" onClick={onBackToSignIn}>
        ← Back to sign in
      </button>
    </AuthCard>
  );
}

function Dashboard({ auth, onLogout }: { auth: AuthState; onLogout: () => Promise<void> }) {
  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            SS
          </span>
          <span>Shiksha Setu</span>
        </div>
        <button className="outline-button" type="button" onClick={onLogout}>
          Sign out
        </button>
      </header>
      <section className="dashboard-content">
        <p className="eyebrow">Your bridge starts here</p>
        <h1>Welcome, {auth.user.username}.</h1>
        <p className="dashboard-intro">
          Your {auth.user.role} workspace is ready. We’ll bring your next meaningful
          action here as the platform grows.
        </p>
        <div className="dashboard-grid">
          <RoleGate
            role={auth.user.role}
            allowedRoles={["donor", "school", "volunteer", "administrator"]}
          >
            <article className="dashboard-card accent-card">
              <span className="card-kicker">Account role</span>
              <strong>{auth.user.role}</strong>
              <p>Role-based tools and workflows will appear in this workspace.</p>
            </article>
          </RoleGate>
          <RoleGate
            role={auth.user.role}
            allowedRoles={["administrator"]}
            fallback={
              <article className="dashboard-card">
                <span className="card-kicker">Your impact</span>
                <strong>Ready to begin</strong>
                <p>Small actions can help resources reach the learners who need them.</p>
              </article>
            }
          >
            <article className="dashboard-card">
              <span className="card-kicker">Administration</span>
              <strong>Review queue</strong>
              <p>Administrative verification and moderation tools will appear here.</p>
            </article>
          </RoleGate>
          <RoleGate role={auth.user.role} allowedRoles={["school"]}>
            <SchoolOnboarding auth={auth} />
          </RoleGate>
          <RoleGate role={auth.user.role} allowedRoles={["administrator"]}>
            <AdminVerificationQueue auth={auth} />
          </RoleGate>
          <RoleGate role={auth.user.role} allowedRoles={["donor"]}>
            <DonationWorkspace auth={auth} />
          </RoleGate>
        </div>
      </section>
    </main>
  );
}

function AuthCard({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="auth-card">
      <div className="auth-card-heading">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function FormField({
  id,
  label,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
  required = false,
}: {
  id: string;
  label: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  autoComplete: string;
  required?: boolean;
}) {
  return (
    <div className="field-group">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required={required}
      />
    </div>
  );
}

function PasswordInput({
  id,
  value,
  onChange,
  showPassword,
  onToggle,
  autoComplete,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  showPassword: boolean;
  onToggle: () => void;
  autoComplete: string;
}) {
  return (
    <div className="password-input">
      <input
        id={id}
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        required
      />
      <button type="button" className="password-toggle" onClick={onToggle}>
        {showPassword ? "Hide" : "Show"}
      </button>
    </div>
  );
}

function FormError({ message }: { message: string }) {
  return (
    <div className="form-error" role="alert">
      <span aria-hidden="true">!</span>
      {message}
    </div>
  );
}
