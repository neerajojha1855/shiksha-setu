import type { ReactNode } from "react";

import type { AuthState, UserRole } from "../../features/auth/auth-service";

type ProtectedRouteProps = {
  auth: AuthState | null;
  children: ReactNode;
  allowedRoles?: readonly UserRole[];
  fallback?: ReactNode;
};

export function ProtectedRoute({
  auth,
  children,
  allowedRoles,
  fallback = <AccessDenied />,
}: ProtectedRouteProps) {
  if (!auth) {
    return <AccessDenied message="Please sign in to continue." />;
  }

  if (allowedRoles && !allowedRoles.includes(auth.user.role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

function AccessDenied({ message = "You do not have access to this area." }: { message?: string }) {
  return (
    <main className="access-denied-page">
      <section className="access-denied-card" aria-labelledby="access-denied-title">
        <span className="access-denied-icon" aria-hidden="true">
          !
        </span>
        <p className="eyebrow">Access boundary</p>
        <h1 id="access-denied-title">This space is protected.</h1>
        <p>{message}</p>
      </section>
    </main>
  );
}
