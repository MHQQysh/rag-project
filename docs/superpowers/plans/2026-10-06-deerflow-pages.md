# DeerFlow Web Implementation Plan

**Goal:** Publish a usable BYOK browser app at /rag-project/deerflow-web/ while preserving commerce.

**Architecture:** Browser-only modules split retrieval, streamed API transport and UI. A single Pages artifact serves both projects. Full upstream DeerFlow remains a separately hosted backend project.

**Tech Stack:** Vanilla JavaScript modules, Node test runner, HTML/CSS, GitHub Actions/Pages.

## Global Constraints

- Fixed official API endpoint; Key only in page memory; render untrusted strings as text.
- No private files, local configuration, account databases or API keys committed.
- No model-generated claims of search, code execution or full DeerFlow capability.
- Preserve existing commerce app and URL. Deploy under sibling path with relative assets.

## Execution (inline, authorized by user)

- [ ] Add failing Node tests for chunk overlap, Chinese/English retrieval, zero hits, context budgets, fragmented SSE, API errors, cancellation and incomplete streams.
- [ ] Implement `deerflow-web/core.mjs`: chunkDocument(name,text), retrieve(query,chunks), buildMessages(history,query,hits). Stable citations identify file and chunk. Cap 8 chunks and bounded excerpts/history.
- [ ] Implement `deerflow-web/model.mjs`: streamChat({key,model,messages,signal,onDelta,fetchImpl}); parse SSE split across bytes/lines, reject abnormal EOF, safe status errors, 120-second deadline and reader cleanup.
- [ ] Implement `deerflow-web/index.html`, `styles.css`, `app.mjs`: key input, model, file limits, retrieval preview, real streaming, cancel, clear, export, sample and honest status. Lock conflicting controls during execution.
- [ ] Add `guide.html`, README and public sample explaining actual implementation and full upstream directory links. Source links use GitHub rather than private filesystem paths.
- [ ] Extend `.github/workflows/commerce-pages.yml` and add `scripts/assemble-pages.mjs`: run both tests, allowlist new app files, replace root redirect with a project directory.
- [ ] Run `node --test deerflow-web/tests/*.test.mjs`, commerce build and staged-site checks. Inspect browser rendering and test UI. Review staged diff and scan secrets.
- [ ] Commit and push to main; check existing Pages settings, Actions conclusion and public resources. If credentials unavailable, ask only for the required login step. Report real live API testing boundary.

Existing authorization covers inline implementation and publication; no additional execution choice needed.
