# Commerce Pages Implementation Plan

**Goal:** Publish a sibling commerce project with a usable static analysis app and retained backend.

**Architecture:** Python generates public synthetic data and expected fixtures. Browser modules generate constrained SQL through DeepSeek, execute SQLite in a disposable Worker, validate raw rows independently, calculate exact contributions, and download evidence. GitHub Actions publishes only the static app.

**Tech Stack:** JavaScript ES modules, sql.js WASM, BigInt fractions, Node test runner, Python 3.11, GitHub Pages.

## Global Constraints

- No credentials, runtime databases, logs or virtual environments in commits; only freshly generated synthetic fixture database is public.
- Existing sibling projects are unchanged except root navigation documentation.
- Browser mode is an explicit port, not the official AWEL runtime.
- Keep supplied Key in page memory only; fixed DeepSeek HTTPS origin; never include Key in evidence or errors.

## Execution

- [ ] Prepare sibling source, commit approved design, generate synthetic database and Python expected fixtures.
- [ ] Implement core.mjs: parameters, query validation, independent raw-row totals, exact fraction decomposition; tests compare every supported region/month to Python output and reject corrupted rows.
- [ ] Implement query-worker.js: load same-origin WASM/SQLite, query_only, single statement, row cap; main thread terminates after budget.
- [ ] Implement model.mjs: constrained JSON SQL requests, 90 second cancellation, safe HTTP errors, one repair; tests use injected fetch mocks for authentication errors and output validation.
- [ ] Implement index.html, styles.css, app.mjs: responsive dashboard, input Key, baseline/live actions, cancellation, evidence export, scope and architecture explanation. Render model strings only with textContent.
- [ ] Implement build/export script and Pages workflow; publish only approved static paths. Run Node tests, browser QA, secret scan, then commit and push. Check Pages deployment and public URL; document any authentication blocker.
- [ ] Update README and deployment guide with exact Windows install/start commands and backend hosting boundaries.

Verification commands: `npm ci`; `npm test` in db-gpt-commerce/web. Python exporter uses standard library plus local commerce modules only. Expected East China July/August net delta is -9900000 cents, factors [-4480000,-3277500,-1342500,-800000]. Network tests use fake test tokens and never real credentials. Production model validation requires user-entered Key.

Execution proceeds inline under existing user authorization; no additional execution-choice approval is needed.

## Outcome

Sibling project implemented and pushed to main; initial deployment run 36553465239 succeeded. Ten Node tests pass, all four Python numerical comparisons pass. Local browser baseline and invalid-Key behavior verified; public static resources match the build. Pages and HTTPS enabled. Real paid-key success, online browser interaction, download receipt, and exhaustive cancellation/timeout UI tests remain unverified; no claim of those checks passing. No new backend server was needed for the static simulation app; Windows backend retained with deployment guidance.
