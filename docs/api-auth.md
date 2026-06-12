# API Authentication and Route Access

## Route Access Levels

| Router | Required Role | Allowed Identities |
|---|---|---|
| `GET /api/v1/events/*` | None (public) | Anyone |
| `GET /api/v1/identity/me` | Any authenticated user | admin, manager, moderator, user |
| `GET/POST/PATCH/DELETE /api/v1/moderation/*` | `moderator` or above | moderator, manager, admin |
| `POST/DELETE /api/v1/ingestion/*` | `service` | service only |

## Role Hierarchy

```
admin > manager > moderator > user    (human hierarchy)
service                               (isolated — pipeline/automation only)
```

`service` is fully isolated from the human hierarchy: an `admin` JWT cannot call ingestion routes, and a `service` JWT cannot call moderation routes.

## Service Authentication for Ingestion Routes

Ingestion endpoints (`/api/v1/ingestion/*`) are protected by `require_service` (FOMO-150).

Any caller — including automated pipelines and n8n workflows — must present a **Bearer JWT** that resolves to a FOMO user with `system_role = service`.

### Distinction: n8n auth vs FOMO API service auth

n8n has its own authentication layer that controls who can access the n8n interface and its workflows. That authentication is separate from and does not satisfy FOMO API authentication.

When an n8n workflow sends an HTTP request to a FOMO ingestion endpoint, the request must include a Bearer token accepted by the FOMO API's own auth mechanism (`require_service`). n8n's internal credentials are not forwarded automatically.

Operational details for provisioning service credentials (Keycloak client setup, token grant, user bootstrap) are documented in the `fomo-platform` repository.

## Public Discovery Routes

The following routes intentionally require no authentication and are accessible to anonymous mobile clients:

- `GET /api/v1/events/discovery`
- `GET /api/v1/events/{event_id}`
- `GET /api/v1/health`

## Approve/Reject Overlap

`ingestion/approve` and `ingestion/reject` duplicate equivalent moderation routes. They exist for automated pipeline use (e.g., auto-approve high-confidence events). Human moderators should use:

- `POST /api/v1/moderation/pending-events/{id}/approve`
- `POST /api/v1/moderation/pending-events/{id}/reject`
