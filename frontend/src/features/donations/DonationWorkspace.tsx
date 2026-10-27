import { FormEvent, useEffect, useState } from "react";

import { ApiError, apiRequest } from "../../lib/api-client";
import type { AuthState } from "../auth/auth-service";

type DonorProfile = {
  id: string;
  owner_id: string;
  display_name: string;
  organization: string | null;
  bio: string | null;
  city: string;
  region: string;
};

type Donation = {
  id: string;
  title: string;
  description: string;
  category: string;
  quantity_available: number;
  quantity_reserved: number;
  condition: string;
  availability: string;
  pickup_available: boolean;
  delivery_available: boolean;
  city: string;
  region: string;
  status: "active" | "withdrawn";
};

const emptyProfile = { display_name: "", organization: "", bio: "", city: "", region: "" };
const emptyDonation = {
  title: "", description: "", category: "", quantity_available: "1", condition: "",
  availability: "Available now", pickup_available: true, delivery_available: false, city: "", region: "",
};

export function DonationWorkspace({ auth }: { auth: AuthState }) {
  const [profile, setProfile] = useState<DonorProfile | null>(null);
  const [profileForm, setProfileForm] = useState(emptyProfile);
  const [donations, setDonations] = useState<Donation[]>([]);
  const [form, setForm] = useState(emptyDonation);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load(): Promise<void> {
    setLoading(true);
    try {
      const [profileResponse, donationResponse] = await Promise.all([
        apiRequest<DonorProfile>("/api/donations/profile", {}, auth.accessToken),
        apiRequest<Donation[]>("/api/donations/mine", {}, auth.accessToken),
      ]);
      setProfile(profileResponse);
      setProfileForm({
        display_name: profileResponse.display_name,
        organization: profileResponse.organization ?? "",
        bio: profileResponse.bio ?? "",
        city: profileResponse.city,
        region: profileResponse.region,
      });
      setDonations(donationResponse);
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 404) {
        setProfile(null);
      } else {
        setError(requestError instanceof ApiError ? requestError.message : "Unable to load donations.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [auth.accessToken]);

  async function saveProfile(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      const saved = await apiRequest<DonorProfile>(
        profile ? "/api/donations/profile" : "/api/donations/profile",
        { method: profile ? "PATCH" : "POST", body: JSON.stringify(profileForm) },
        auth.accessToken,
      );
      setProfile(saved);
      setNotice("Donor profile saved.");
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to save profile.");
    }
  }

  async function createDonation(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      await apiRequest<Donation>("/api/donations", {
        method: "POST",
        body: JSON.stringify({ ...form, quantity_available: Number(form.quantity_available) }),
      }, auth.accessToken);
      setForm(emptyDonation);
      setNotice("Donation listing created.");
      await load();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to create listing.");
    }
  }

  async function withdraw(id: string): Promise<void> {
    try {
      await apiRequest<Donation>(`/api/donations/${id}/withdraw`, { method: "POST" }, auth.accessToken);
      setNotice("Donation listing withdrawn.");
      await load();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Unable to withdraw listing.");
    }
  }

  if (loading) return <article className="dashboard-card">Loading your donation workspace…</article>;

  return (
    <article className="dashboard-card donation-workspace">
      <span className="card-kicker">Donation listings</span>
      <h2>{profile ? "Share resources with verified schools" : "Set up your donor profile"}</h2>
      <p>List useful educational materials with clear quantity and collection options.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      {notice && <p className="notice success" role="status">{notice}</p>}
      <form className="onboarding-form" onSubmit={saveProfile}>
        <div className="form-row">
          <input required placeholder="Display name" value={profileForm.display_name} onChange={(e) => setProfileForm({ ...profileForm, display_name: e.target.value })} />
          <input placeholder="Organization (optional)" value={profileForm.organization} onChange={(e) => setProfileForm({ ...profileForm, organization: e.target.value })} />
        </div>
        <textarea placeholder="Short donor bio (optional)" value={profileForm.bio} onChange={(e) => setProfileForm({ ...profileForm, bio: e.target.value })} />
        <div className="form-row">
          <input required placeholder="City" value={profileForm.city} onChange={(e) => setProfileForm({ ...profileForm, city: e.target.value })} />
          <input required placeholder="Region" value={profileForm.region} onChange={(e) => setProfileForm({ ...profileForm, region: e.target.value })} />
        </div>
        <button className="primary-button" type="submit">{profile ? "Save donor profile" : "Create donor profile"}</button>
      </form>
      {profile && (
        <>
          <h3 className="workspace-subheading">New donation</h3>
          <form className="onboarding-form" onSubmit={createDonation}>
            <input required placeholder="Listing title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <textarea required placeholder="Describe the materials and intended use" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <div className="form-row">
              <input required placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
              <input required min="1" type="number" placeholder="Quantity" value={form.quantity_available} onChange={(e) => setForm({ ...form, quantity_available: e.target.value })} />
            </div>
            <div className="form-row">
              <input required placeholder="Condition" value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} />
              <input required placeholder="Availability" value={form.availability} onChange={(e) => setForm({ ...form, availability: e.target.value })} />
            </div>
            <div className="checkbox-row">
              <label><input type="checkbox" checked={form.pickup_available} onChange={(e) => setForm({ ...form, pickup_available: e.target.checked })} /> Pickup available</label>
              <label><input type="checkbox" checked={form.delivery_available} onChange={(e) => setForm({ ...form, delivery_available: e.target.checked })} /> Delivery possible</label>
            </div>
            <div className="form-row">
              <input required placeholder="Pickup city" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
              <input required placeholder="Region" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} />
            </div>
            <button className="primary-button" type="submit">Publish donation listing</button>
          </form>
          <h3 className="workspace-subheading">Your listings</h3>
          <div className="donation-list">
            {donations.length === 0 && <p>No donation listings yet.</p>}
            {donations.map((donation) => (
              <div className="donation-item" key={donation.id}>
                <div>
                  <strong>{donation.title}</strong>
                  <span>{donation.category} · {donation.quantity_available - donation.quantity_reserved} available · {donation.status}</span>
                </div>
                {donation.status === "active" && <button className="outline-button" type="button" onClick={() => withdraw(donation.id)}>Withdraw</button>}
              </div>
            ))}
          </div>
        </>
      )}
    </article>
  );
}
