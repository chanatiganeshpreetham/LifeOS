---
name: "LifeOS 02 - Auth0 Authentication"
description: "Integrate Auth0 Universal Login with the LifeOS React client and FastAPI API."
argument-hint: "Optional Auth0 sub-feature, such as callback handling or profile provisioning"
agent: "agent"
---

Implement the LifeOS authentication stage using the configured Auth0 tenant. Inspect the current code and follow established patterns. Read the relevant SRS/authentication requirements, architecture, Auth0 environment configuration, and the `users` table schema. Stop and ask before making a security or account-migration decision that is still open.

Implement only the approved Phase 1 auth requirements:
- Use Auth0 Universal Login for sign-in, sign-up, and account recovery from the responsive React client.
- Use the Auth0 React SDK with the configured tenant domain, SPA client ID, and LifeOS API audience.
- Keep Auth0 tokens in the SDK's in-memory cache; never put tokens in localStorage, sessionStorage, URLs, logs, or rendered markup.
- Verify API access tokens in FastAPI using Auth0's JWKS, RS256, exact issuer, audience, and expiry checks.
- Initialize LifeOS profiles only from a separately verified Auth0 ID token whose subject matches the API access token. Require a verified email.
- Store the stable Auth0 subject on the PostgreSQL user profile. Do not silently link an existing profile based only on email.
- Add Alembic migrations for schema changes and keep authenticated data scoped to the mapped LifeOS user.
- Remove or disable legacy local-password endpoints and UI so they cannot act as an alternate authentication path.

Security and correctness constraints:
- The frontend must never contain an Auth0 client secret. Use environment variables for the domain, public client ID, and audience.
- Never trust profile fields supplied by the client unless they come from a cryptographically verified Auth0 token.
- Preserve existing user data; require an explicitly approved secure linking flow if local accounts already exist.
- Keep API authentication failures explicit and avoid broad exception catches or success-shaped fallbacks.
- Do not add tests unless requested; run the existing focused checks and verify migrations and frontend/backend startup behavior.
- Do not add unrelated profile, OAuth-provider, or authorization features. Summarize behavior, changed files, verification, required dashboard settings, and remaining limitations.
