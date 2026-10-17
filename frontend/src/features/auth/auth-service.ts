import { apiRequest } from "../../lib/api-client";

const authStorageKey = "shiksha-setu.auth.v1";

export type UserRole = "donor" | "school" | "volunteer" | "administrator";

export type User = {
  id: string;
  email: string;
  username: string;
  role: UserRole;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
};

export type AuthState = {
  accessToken: string;
  refreshToken: string;
  user: User;
};

export type LoginCredentials = {
  identifier: string;
  password: string;
};

export type RegistrationPayload = {
  email: string;
  username: string;
  password: string;
  role: Exclude<UserRole, "administrator">;
};

export type VerificationStatus = "pending" | "approved" | "rejected";

export type SchoolProfile = {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  city: string;
  region: string;
  website: string | null;
  verification_status: VerificationStatus;
  created_at: string;
  updated_at: string;
};

export type VerificationRecord = {
  id: string;
  school_id: string;
  submitted_by: string;
  registration_reference: string;
  evidence_description: string;
  status: VerificationStatus;
  decision_reason: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
};

export function loadAuth(): AuthState | null {
  try {
    const saved = localStorage.getItem(authStorageKey);
    return saved ? (JSON.parse(saved) as AuthState) : null;
  } catch {
    return null;
  }
}

export function saveAuth(auth: AuthState | null): void {
  if (auth) {
    localStorage.setItem(authStorageKey, JSON.stringify(auth));
  } else {
    localStorage.removeItem(authStorageKey);
  }
}

export function toAuthState(response: AuthResponse): AuthState {
  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    user: response.user,
  };
}

export function login(credentials: LoginCredentials): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function register(payload: RegistrationPayload): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCurrentUser(accessToken: string): Promise<User> {
  return apiRequest<User>("/api/auth/me", {}, accessToken);
}

export function logout(refreshToken: string): Promise<void> {
  return apiRequest<void>("/api/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function getSchoolProfile(accessToken: string): Promise<SchoolProfile> {
  return apiRequest<SchoolProfile>("/api/schools/profile", {}, accessToken);
}

export function createSchoolProfile(
  payload: Omit<SchoolProfile, "id" | "owner_id" | "verification_status" | "created_at" | "updated_at">,
  accessToken: string,
): Promise<SchoolProfile> {
  return apiRequest<SchoolProfile>("/api/schools/profile", {
    method: "POST",
    body: JSON.stringify(payload),
  }, accessToken);
}

export function submitSchoolVerification(
  payload: { registration_reference: string; evidence_description: string },
  accessToken: string,
): Promise<VerificationRecord> {
  return apiRequest<VerificationRecord>("/api/schools/profile/verification", {
    method: "POST",
    body: JSON.stringify(payload),
  }, accessToken);
}

export function getSchoolVerifications(accessToken: string): Promise<VerificationRecord[]> {
  return apiRequest<VerificationRecord[]>("/api/schools/profile/verifications", {}, accessToken);
}

export function getAdminVerificationQueue(accessToken: string): Promise<VerificationRecord[]> {
  return apiRequest<VerificationRecord[]>("/api/admin/school-verifications", {}, accessToken);
}

export function decideSchoolVerification(
  verificationId: string,
  payload: { status: "approved" | "rejected"; reason: string },
  accessToken: string,
): Promise<VerificationRecord> {
  return apiRequest<VerificationRecord>(`/api/admin/school-verifications/${verificationId}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, accessToken);
}