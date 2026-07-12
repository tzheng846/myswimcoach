import { supabase } from "./supabase";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://swimnetics-api-production.up.railway.app";

// Authenticated fetch against the Railway FastAPI backend.
export async function apiFetch(path, options = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) throw new Error("Not signed in");

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) {
    const detail = body?.detail || `Request failed (${res.status})`;
    const err = new Error(
      typeof detail === "string" ? detail : `Request failed (${res.status})`
    );
    err.status = res.status;
    err.body = body; // structured error payloads (e.g. 422 {detail:{errors:[...]}})
    throw err;
  }
  return body;
}

// Authenticated multipart upload (FormData). No Content-Type header — the
// browser sets the multipart boundary itself.
export async function apiUpload(path, formData, { method = "POST" } = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) throw new Error("Not signed in");

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    body: formData,
    headers: { Authorization: `Bearer ${session.access_token}` },
  });

  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) {
    const detail = body?.detail;
    const err = new Error(
      typeof detail === "string" ? detail : `Upload failed (${res.status})`
    );
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}
