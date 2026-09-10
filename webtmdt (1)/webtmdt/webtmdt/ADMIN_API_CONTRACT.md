# Admin API Contract

The current frontend runs with `BOOKHUB_DATA_SOURCE=mock` by default. The service interface in `static/js/admin_services.js` is the only UI boundary. A future API adapter should preserve these response shapes and operation names.

## Disputes

- `GET /api/admin/disputes` -> `Dispute[]`
- `GET /api/admin/disputes/{id}` -> `Dispute`
- `PATCH /api/admin/disputes/{id}/status` body `{ "status": "UNDER_REVIEW" }`
- `POST /api/admin/disputes/{id}/request-seller-response` -> `Dispute`
- `POST /api/admin/disputes/{id}/resolve` body `{ "decision": "REFUND_BUYER|RESOLVE_FOR_SELLER", "note": "..." }`
- `POST /api/admin/disputes/{id}/reject` body `{ "reason": "..." }`

Dispute statuses: `OPEN`, `UNDER_REVIEW`, `WAITING_SELLER`, `WAITING_BUYER`, `RESOLVED`, `REJECTED`.

## Payouts

- `GET /api/admin/payouts` -> `PayoutRequest[]`
- `GET /api/admin/payouts/{id}` -> `PayoutRequest`
- `POST /api/admin/payouts/{id}/approve` -> `PayoutRequest`
- `POST /api/admin/payouts/{id}/reject` body `{ "reason": "..." }` -> `PayoutRequest`

Payout statuses: `PENDING`, `APPROVED`, `PROCESSING`, `COMPLETED`, `REJECTED`. The API must reject approval for non-`PENDING` records and must enforce available-balance limits server-side.

## Documents

- `GET /api/admin/documents/{id}` -> `Document`
- `GET /api/admin/documents/{id}/preview` -> `{ "available": true, "previewUrl": "...", "mimeType": "application/pdf" }`
- `GET /api/admin/documents/{id}/download` -> file response or signed URL

The frontend must show `Document preview chua duoc ket noi voi storage backend.` when no storage URL is available. It must not claim verification or availability from mock state.

## Roles and permissions

- `GET /api/admin/roles` -> `Role[]`
- `GET /api/admin/permissions` -> `string[]`
- `PUT /api/admin/roles/{id}/permissions` body `{ "permissions": ["users.view", "payouts.approve"] }` -> `Role`

Frontend permission checks are for UI/UX only. Backend authorization remains the security boundary.

## Audit logs

- `GET /api/admin/audit-logs` -> `AuditLog[]`
- Server-side actions should write audit records for seller approval/rejection, payout actions, refunds, dispute resolution, user locks, and permission changes.
