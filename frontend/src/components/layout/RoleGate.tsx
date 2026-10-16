import type { ReactNode } from "react";

import type { UserRole } from "../../features/auth/auth-service";

type RoleGateProps = {
  role: UserRole;
  allowedRoles: readonly UserRole[];
  children: ReactNode;
  fallback?: ReactNode;
};

export function RoleGate({
  role,
  allowedRoles,
  children,
  fallback = null,
}: RoleGateProps) {
  return allowedRoles.includes(role) ? <>{children}</> : <>{fallback}</>;
}
