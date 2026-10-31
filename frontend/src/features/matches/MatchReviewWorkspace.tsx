import { useEffect, useState } from "react";

import { ApiError, apiRequest } from "../../lib/api-client";
import type { AuthState } from "../auth/auth-service";

type Match = {
  id: string;
  need_id: string;
  donation_id: string;
  score: number;
  explanation: string;
  status: "proposed" | "accepted" | "rejected" | "expired";
  need_title: string;
  donation_title: string;
  quantity_remaining: number;
  need_city: string;
  need_region: string;
  donation_city: string;
  donation_region: string;
};

type Need = { id: string; title: string; status: string };
type Props = { auth: AuthState; role: "donor" | "school" };

export function MatchReviewWorkspace({ auth, role }: Props) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      if (role === "donor") {
        setMatches(await apiRequest<Match[]>("/api/matches/mine", {}, auth.accessToken));
      } else {
        const needs = await apiRequest<Need[]>("/api/needs/school/mine", {}, auth.accessToken);
        const matchLists = await Promise.all(
          needs
            .filter((need) => need.status === "published")
            .map((need) => apiRequest<Match[]>(`/api/matches/need/${need.id}`, {}, auth.accessToken)),
        );
        setMatches(matchLists.flat());
      }
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to load match reviews.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [auth.accessToken, role]);

  async function review(matchId: string, action: "accept" | "reject"): Promise<void> {
    setBusyId(matchId);
    setError(null);
    setNotice(null);
    try {
      await apiRequest<Match>(`/api/matches/${matchId}/${action}`, { method: "POST" }, auth.accessToken);
      setNotice(action === "accept" ? "Match accepted and inventory reserved." : "Match declined.");
      await load();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to update this match.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <article className="dashboard-card match-review-workspace">
      <span className="card-kicker">Match review</span>
      <h2>{role === "donor" ? "Review resource matches" : "Review suggested donations"}</h2>
      <p>{role === "donor"
        ? "See why a school need fits your listing before reserving inventory."
        : "Review transparent, explainable matches for your published needs."}</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p className="notice success" role="status">{notice}</p>}
      {loading && <p className="match-review-state">Loading matches…</p>}
      {!loading && matches.length === 0 && <p className="match-review-state">No proposed matches yet.</p>}
      <div className="match-list">
        {matches.map((match) => (
          <div className="match-item" key={match.id}>
            <div className="match-item-copy">
              <div className="match-item-heading">
                <strong>{role === "donor" ? match.need_title : match.donation_title}</strong>
                <span className={`match-score match-score-${match.score >= 80 ? "high" : "standard"}`}>
                  {match.score}% fit
                </span>
              </div>
              <span>
                {role === "donor"
                  ? `${match.need_city}, ${match.need_region} · ${match.quantity_remaining} still available`
                  : `${match.donation_city}, ${match.donation_region} · ${match.quantity_remaining} available`}
              </span>
              <p>{match.explanation}</p>
              <span className={`match-status match-status-${match.status}`}>{match.status}</span>
            </div>
            {match.status === "proposed" && (
              <div className="match-actions">
                <button
                  className="primary-button"
                  type="button"
                  disabled={busyId === match.id}
                  onClick={() => void review(match.id, "accept")}
                >
                  {busyId === match.id ? "Saving…" : "Accept"}
                </button>
                <button
                  className="outline-button"
                  type="button"
                  disabled={busyId === match.id}
                  onClick={() => void review(match.id, "reject")}
                >
                  Decline
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </article>
  );
}
