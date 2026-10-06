# YSH demo login design and implementation plan

User approved a one-click “进入演示” login using an independent non-admin account. Existing admin login stays available. Homepage already redirects to /login.

Use one provisioned passwordless user, pinned by server environment user ID. Do not send any admin or demo password to the browser. POST /api/v1/auth/login/demo sets the existing HttpOnly session and CSRF cookies; GET /api/v1/auth/demo-status reports availability. Default disabled. Missing user, admin role, setup-required or password-bearing user must fail closed. Disabled demo also rejects existing demo sessions. Requests use the existing same-origin auth CSRF policy. Block demo account credential-management routes, retaining ordinary chat owner isolation and user permissions. This is shared demonstration history and UI must disclose that; it is not isolated anonymous user provisioning.

Alternatives considered: prefilled password exposes credentials; per-visitor accounts need extra expiry/cleanup infrastructure. Use the approved shared demo account for this iteration.

1. Add backend regression tests for disabled/missing/admin rejection, valid demo cookies, hostile origin, demo credential-management denial, and normal admin preservation.
2. Add auth/demo.py policy helpers, demo routes to routers/auth.py, explicit public paths and CSRF auth classification; restrict demo sessions in middleware.
3. Add frontend availability fetch and one-click demo component on login, loading/error state and shared-space notice. Test successful navigation, failure and hidden/disabled availability.
4. Provision a passwordless normal user server-side once; set DEMO_USER_ID and DEMO_LOGIN_ENABLED in runtime.env. Preserve admin and database.
5. Run relevant auth tests, backend offline/blocking checks, frontend lint/typecheck and production build. Build on WSL, deploy with backups, verify public cookies/me/admin denial and chat creation. Push code and deployment instructions to GitHub.
