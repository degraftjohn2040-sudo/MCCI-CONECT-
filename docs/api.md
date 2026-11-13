# API

All endpoints are same-origin JSON. Errors return FastAPI's `detail` and appropriate HTTP status. List endpoints accept `limit` (1–100, default 25) and `offset` (0–100000), returning `{items, has_more}`. Timestamps are SQLite UTC strings. API responses use `Cache-Control: no-store`.

- `POST /api/session`: `{email,password}` plus `X-Requested-With: MCCI-CONNECT`; sets session cookie and returns `{email,role,csrf_token}`. No public registration.
- `GET /api/session`: current identity and CSRF token.
- `DELETE /api/session`: revoke the current session.
- `GET /api/members`: admin/owner/super_admin/pastor. `POST`: admins; `{name,phone?,email?}`.
- `GET /api/attendance`: same readers. `POST`: admins; `{event_name,event_date: "YYYY-MM-DD",headcount}`.
- `GET /api/announcements`: any recognized authenticated role. `POST`: admins; `{title,body}`.
- `GET /api/audit`: admins only.

For authenticated mutations send `X-CSRF-Token` from the session response and the session cookie. Roles and CSRF are verified server-side regardless of UI visibility. 401 = no valid session, 403 = denied or missing CSRF, 422 = invalid input, 429 = local sign-in limit. The local limit applies to all login attempts, including successful ones. No externally consumable API contract, versioning, OAuth, per-record authorization or API keys are provided.
