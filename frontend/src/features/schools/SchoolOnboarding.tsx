import { FormEvent, useEffect, useState } from "react";

import {
  createSchoolProfile,
  getSchoolProfile,
  getSchoolVerifications,
  submitSchoolVerification,
  type AuthState,
  type SchoolProfile,
  type VerificationRecord,
} from "../auth/auth-service";

export function SchoolOnboarding({ auth }: { auth: AuthState }) {
  const [profile, setProfile] = useState<SchoolProfile | null>(null);
  const [verifications, setVerifications] = useState<VerificationRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getSchoolProfile(auth.accessToken),
      getSchoolVerifications(auth.accessToken),
    ])
      .then(([nextProfile, nextVerifications]) => {
        setProfile(nextProfile);
        setVerifications(nextVerifications);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.message.includes("not found")) {
          return;
        }
        setError(requestError instanceof Error ? requestError.message : "Unable to load school onboarding.");
      })
      .finally(() => setIsLoading(false));
  }, [auth.accessToken]);

  async function createProfile(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    try {
      const nextProfile = await createSchoolProfile({
        name: String(form.get("name") ?? ""),
        description: String(form.get("description") ?? "") || null,
        city: String(form.get("city") ?? ""),
        region: String(form.get("region") ?? ""),
        website: String(form.get("website") ?? "") || null,
      }, auth.accessToken);
      setProfile(nextProfile);
      setMessage("School profile created. Submit verification details when ready.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create school profile.");
    }
  }

  async function submitVerification(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    try {
      const record = await submitSchoolVerification({
        registration_reference: String(form.get("registration_reference") ?? ""),
        evidence_description: String(form.get("evidence_description") ?? ""),
      }, auth.accessToken);
      setVerifications((current) => [record, ...current]);
      setProfile((current) => current ? { ...current, verification_status: "pending" } : current);
      setMessage("Verification submitted for administrator review.");
      event.currentTarget.reset();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to submit verification.");
    }
  }

  if (isLoading) {
    return <article className="dashboard-card">Loading school onboarding…</article>;
  }

  if (!profile) {
    return (
      <article className="dashboard-card onboarding-card">
        <span className="card-kicker">School onboarding</span>
        <h2>Create your school profile</h2>
        <p>Only safe school-level information is public. Verification evidence stays restricted.</p>
        {error && <p className="form-error">{error}</p>}
        <form className="onboarding-form" onSubmit={createProfile}>
          <input name="name" required minLength={2} placeholder="School name" aria-label="School name" />
          <div className="form-row">
            <input name="city" required minLength={2} placeholder="City" aria-label="City" />
            <input name="region" required minLength={2} placeholder="State or region" aria-label="State or region" />
          </div>
          <input name="website" type="url" placeholder="Website (optional)" aria-label="Website" />
          <textarea name="description" maxLength={2000} placeholder="Short public description (optional)" aria-label="Description" />
          <button className="primary-button" type="submit">Create school profile</button>
        </form>
      </article>
    );
  }

  return (
    <article className="dashboard-card onboarding-card">
      <span className="card-kicker">School verification</span>
      <h2>{profile.name}</h2>
      <p>{profile.city}, {profile.region} · Status: <strong>{profile.verification_status}</strong></p>
      {message && <p className="notice success">{message}</p>}
      {error && <p className="form-error">{error}</p>}
      {profile.verification_status !== "approved" && (
        <form className="onboarding-form" onSubmit={submitVerification}>
          <input name="registration_reference" required minLength={2} placeholder="Registration reference" aria-label="Registration reference" />
          <textarea name="evidence_description" required minLength={10} maxLength={4000} placeholder="Describe the verification evidence available to administrators" aria-label="Evidence description" />
          <button className="primary-button" type="submit">Submit for review</button>
        </form>
      )}
      {verifications.length > 0 && (
        <div className="verification-history">
          <h3>Submission history</h3>
          {verifications.map((record) => (
            <div className="verification-item" key={record.id}>
              <strong>{record.status}</strong>
              <span>{record.registration_reference}</span>
              {record.decision_reason && <p>{record.decision_reason}</p>}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
