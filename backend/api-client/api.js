// Drop this into frontend/assets/js/ and import it from your pages.
// Every request sends cookies (credentials: "include"), so the API origin must be listed in FRONTEND_ORIGINS.
const API_BASE = "http://127.0.0.1:8000"; // change for production

let csrf = sessionStorage.getItem("csrf") || "";

async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (method !== "GET" && csrf) headers["X-CSRF-Token"] = csrf; // needed for admin writes
  const res = await fetch(API_BASE + path, {
    method, headers, credentials: "include",
    body: form || (body ? JSON.stringify(body) : undefined),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw Object.assign(new Error(Array.isArray(d) ? d.map(e => e.msg).join(", ") : d || res.statusText), { status: res.status });
  }
  return data;
}

// ---- public ----
export const getClubs = () => api("/api/clubs");
export const getClub = slug => api(`/api/clubs/${slug}`);
export const getAnnouncements = club => api("/api/announcements" + (club ? `?club=${club}` : ""));
export const getGallery = (club = "", page = 1, event = "") =>
  api(`/api/gallery?page=${page}&club=${club}&event=${encodeURIComponent(event)}`);
export const getAlbums = club => api("/api/gallery/albums" + (club ? `?club=${club}` : ""));
export const checkLink = token => api(`/api/registration-links/${token}`);

// ---- student registration: register -> sendOtp -> verifyOtp ----
export const register = form => api("/api/auth/register", { method: "POST", body: form }); // returns {pending_id}
export const sendOtp = pending_id => api("/api/auth/send-otp", { method: "POST", body: { purpose: "register", pending_id } });
export const verifyOtp = (pending_id, otp, captcha_token) =>
  api("/api/auth/verify-otp", { method: "POST", body: { pending_id, otp, captcha_token } }); // returns {membership, student}

// ---- student login (passwordless) ----
export const sendLoginOtp = email => api("/api/auth/send-otp", { method: "POST", body: { purpose: "login", email } });
export const studentLogin = (email, otp) => api("/api/auth/login", { method: "POST", body: { email, otp } });
export const myMemberships = () => api("/api/memberships/me");

// ---- admin ----
export async function adminLogin(username, password) {
  const r = await api("/api/admin/login", { method: "POST", body: { username, password } });
  csrf = r.csrf_token; sessionStorage.setItem("csrf", csrf);
  return r;
}
export async function adminMe() { const r = await api("/api/admin/me"); csrf = r.csrf_token; sessionStorage.setItem("csrf", csrf); return r; }
export const adminLogout = () => api("/api/admin/logout", { method: "POST" });
export const dashboard = () => api("/api/admin/dashboard");
export const uploadPhoto = (club_slug, title, event_name, file) => {
  const f = new FormData(); f.append("club_slug", club_slug); f.append("title", title); f.append("event_name", event_name); f.append("file", file);
  return api("/api/admin/photos", { method: "POST", form: f });
};
export const deletePhoto = id => api(`/api/admin/photos/${id}`, { method: "DELETE" });
export const createAnnouncement = body => api("/api/admin/announcements", { method: "POST", body });
export const patchAnnouncement = (id, body) => api(`/api/admin/announcements/${id}`, { method: "PATCH", body });
export const createLink = body => api("/api/admin/registration-links", { method: "POST", body });
export const patchLink = (id, body) => api(`/api/admin/registration-links/${id}`, { method: "PATCH", body });
export const listStudents = (q = "", club = "", page = 1) =>
  api(`/api/admin/students?q=${encodeURIComponent(q)}&club=${club}&page=${page}`);
export const exportUrl = (q = "", club = "") => `${API_BASE}/api/admin/students/export?q=${encodeURIComponent(q)}&club=${club}`;
