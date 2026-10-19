import { useEffect, useState } from "react";

import { ApiError, apiRequest } from "../../lib/api-client";

type PublicNeed = {
  id: string;
  school_name: string;
  title: string;
  description: string;
  category: string;
  quantity_requested: number;
  quantity_fulfilled: number;
  condition: string;
  urgency: string;
  priority: string;
  city: string;
  region: string;
  fulfillment_percent: number;
};

type DiscoveryResponse = {
  items: PublicNeed[];
  total: number;
  offset: number;
  limit: number;
};

const emptyFilters = { search: "", category: "", urgency: "", priority: "", region: "" };

export function NeedsDiscoveryPage() {
  const [filters, setFilters] = useState(emptyFilters);
  const [result, setResult] = useState<DiscoveryResponse | null>(null);
  const [selected, setSelected] = useState<PublicNeed | null>(null);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams({ offset: String(offset), limit: "12" });
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    setError(null);
    apiRequest<DiscoveryResponse>(`/api/needs/discover?${params}`)
      .then(setResult)
      .catch((requestError) => {
        setError(requestError instanceof ApiError ? requestError.message : "Unable to load needs.");
      });
  }, [filters, offset]);

  async function openNeed(id: string): Promise<void> {
    try {
      setSelected(await apiRequest<PublicNeed>(`/api/needs/${id}`));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to load this need.");
    }
  }

  const pageSize = result?.limit ?? 12;
  const hasPrevious = offset > 0;
  const hasNext = result ? offset + pageSize < result.total : false;

  return (
    <main className="discovery-page">
      <header className="discovery-header">
        <div>
          <p className="eyebrow">Verified school needs</p>
          <h1>Help move a need closer to fulfilled.</h1>
          <p>Explore transparent, school-level requests without exposing student information.</p>
        </div>
        <a className="outline-button" href="/">Sign in</a>
      </header>
      <section className="discovery-content" aria-label="Public needs discovery">
        <form
          className="discovery-filters"
          onSubmit={(event) => {
            event.preventDefault();
            setOffset(0);
          }}
        >
          <input
            aria-label="Search needs"
            placeholder="Search textbooks, school, or category"
            value={filters.search}
            onChange={(event) => setFilters({ ...filters, search: event.target.value })}
          />
          {(["category", "urgency", "priority", "region"] as const).map((field) => (
            <input
              key={field}
              aria-label={`Filter by ${field}`}
              placeholder={field[0].toUpperCase() + field.slice(1)}
              value={filters[field]}
              onChange={(event) => setFilters({ ...filters, [field]: event.target.value })}
            />
          ))}
          <button className="primary-button" type="submit">Search</button>
        </form>
        {error && <p className="form-error" role="alert">{error}</p>}
        {!result && !error && <p className="discovery-state">Loading verified needs…</p>}
        {result && result.items.length === 0 && <p className="discovery-state">No published needs match these filters.</p>}
        <div className="need-grid">
          {result?.items.map((need) => (
            <article className="need-card" key={need.id}>
              <div className="need-card-topline">
                <span className="verified-badge">✓ Verified school</span>
                <span className={`urgency-badge urgency-${need.urgency}`}>{need.urgency} urgency</span>
              </div>
              <p className="card-kicker">{need.category} · {need.city}, {need.region}</p>
              <h2>{need.title}</h2>
              <p>{need.description}</p>
              <div className="need-school">{need.school_name}</div>
              <div className="progress-label">
                <span>{need.quantity_fulfilled} of {need.quantity_requested} fulfilled</span>
                <strong>{need.fulfillment_percent}%</strong>
              </div>
              <div className="progress-track" aria-label={`${need.fulfillment_percent}% fulfilled`}>
                <span style={{ width: `${need.fulfillment_percent}%` }} />
              </div>
              <button className="text-button strong need-detail-button" type="button" onClick={() => openNeed(need.id)}>
                View need →
              </button>
            </article>
          ))}
        </div>
        {result && result.total > pageSize && (
          <nav className="pagination" aria-label="Needs pages">
            <button className="outline-button" disabled={!hasPrevious} onClick={() => setOffset(Math.max(0, offset - pageSize))}>
              Previous
            </button>
            <span>Showing {offset + 1}–{Math.min(offset + pageSize, result.total)} of {result.total}</span>
            <button className="outline-button" disabled={!hasNext} onClick={() => setOffset(offset + pageSize)}>
              Next
            </button>
          </nav>
        )}
      </section>
      {selected && (
        <div className="need-modal-backdrop" role="presentation" onClick={() => setSelected(null)}>
          <article className="need-modal" role="dialog" aria-modal="true" aria-labelledby="need-detail-title" onClick={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" aria-label="Close need details" onClick={() => setSelected(null)}>×</button>
            <span className="verified-badge">✓ Verified school</span>
            <p className="card-kicker">{selected.school_name} · {selected.city}, {selected.region}</p>
            <h2 id="need-detail-title">{selected.title}</h2>
            <p>{selected.description}</p>
            <dl className="need-facts">
              <div><dt>Category</dt><dd>{selected.category}</dd></div>
              <div><dt>Condition</dt><dd>{selected.condition}</dd></div>
              <div><dt>Priority</dt><dd>{selected.priority}</dd></div>
              <div><dt>Quantity</dt><dd>{selected.quantity_requested}</dd></div>
            </dl>
            <div className="progress-track"><span style={{ width: `${selected.fulfillment_percent}%` }} /></div>
            <p className="modal-footnote">{selected.fulfillment_percent}% fulfilled · Sign in to coordinate support.</p>
          </article>
        </div>
      )}
    </main>
  );
}
