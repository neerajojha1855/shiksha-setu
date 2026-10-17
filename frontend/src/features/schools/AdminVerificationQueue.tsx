import { useEffect, useState } from "react";

import {
  decideSchoolVerification,
  getAdminVerificationQueue,
  type AuthState,
  type VerificationRecord,
} from "../auth/auth-service";

export function AdminVerificationQueue({ auth }: { auth: AuthState }) {
  const [records, setRecords] = useState<VerificationRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminVerificationQueue(auth.accessToken)
      .then(setRecords)
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : "Unable to load review queue.");
      });
  }, [auth.accessToken]);

  async function decide(record: VerificationRecord, status: "approved" | "rejected"): Promise<void> {
    const reason = window.prompt(
      status === "approved" ? "Add an approval reason:" : "Add a rejection reason:",
    )?.trim();
    if (!reason) {
      return;
    }
    try {
      const updated = await decideSchoolVerification(
        record.id,
        { status, reason },
        auth.accessToken,
      );
      setRecords((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to save the review decision.");
    }
  }

  return (
    <article className="dashboard-card onboarding-card">
      <span className="card-kicker">Administrator review</span>
      <h2>School verification queue</h2>
      {error && <p className="form-error">{error}</p>}
      {records.length === 0 && <p>No school verification submissions are waiting for review.</p>}
      <div className="verification-history">
        {records.map((record) => (
          <div className="verification-item" key={record.id}>
            <strong>{record.status} · {record.registration_reference}</strong>
            <span>{record.evidence_description}</span>
            {record.status === "pending" && (
              <div className="review-actions">
                <button className="primary-button" type="button" onClick={() => decide(record, "approved")}>
                  Approve
                </button>
                <button className="outline-button" type="button" onClick={() => decide(record, "rejected")}>
                  Reject
                </button>
              </div>
            )}
            {record.decision_reason && <p>{record.decision_reason}</p>}
          </div>
        ))}
      </div>
    </article>
  );
}
