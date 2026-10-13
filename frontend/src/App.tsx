import { useEffect, useState } from "react";

type Readiness = {
  status: string;
  database: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function App() {
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiBaseUrl}/ready`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }
        return response.json() as Promise<Readiness>;
      })
      .then(setReadiness)
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : "Backend unavailable");
      });
  }, []);

  return (
    <main className="page-shell">
      <section className="hero-card" aria-labelledby="page-title">
        <p className="eyebrow">Shiksha Setu</p>
        <h1 id="page-title">Bridging resources. Empowering girls.</h1>
        <p className="intro">
          A trusted foundation for connecting schools with educational materials and support.
        </p>
        <div className="status-panel" aria-live="polite">
          <strong>Platform status</strong>
          {error && <span className="status error">{error}</span>}
          {!error && !readiness && <span className="status">Checking backend readiness…</span>}
          {readiness && (
            <span className={`status ${readiness.status === "ready" ? "success" : "warning"}`}>
              API: {readiness.status}; database: {readiness.database}
            </span>
          )}
        </div>
      </section>
    </main>
  );
}
