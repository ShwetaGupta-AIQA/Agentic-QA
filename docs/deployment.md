# Controlled local deployment

The platform supports a protected local Docker demonstration. Production promotion remains blocked by unresolved Chroma dependency advisories; see [security review](security.md).

```powershell
backend/.venv/Scripts/python.exe scripts/setup_demo.py
docker compose up -d --build --wait --wait-timeout 180
python scripts/smoke.py --restart
```

For a fresh checkout, create a Python tooling environment and install bcrypt before running scripts/setup_demo.py. Open http://127.0.0.1:8080. Private login details are in ignored .secrets/demo-login.json; the separate release-review credential is in .secrets/reviewer_token. Never commit these files.

PostgreSQL stores workflow checkpoints and bounded execution jobs. Chroma and artifacts use persistent volumes. The API does not launch browser tests in queue mode; a separate resource-limited worker runs approved registered suites. Uncertain worker leases fail and require explicit resubmission. The controlled API disables browser-based healing operations.

Only the gateway publishes a loopback port. Runtime status is available on /operations; readiness and metadata counters are available through authenticated /api/ready and /api/metrics. Native development on ports 8001/5174 defaults to local memory checkpoints and must remain on loopback.

CI checks Python/React tests, builds and dependencies. Manual staging requires successful CI for the same commit, configured environment reviewers and a trusted self-hosted runner. External hosting and enterprise identities are not provisioned. Do not suppress dependency findings to obtain a green deployment.

Use docker compose stop or down to stop services while retaining named volumes. Avoid down -v unless intentionally deleting data. Back up database and artifact volumes together. PostgreSQL password rotation requires updating the database role and private secret file.

Optional sanitized LangSmith export is configured using deploy/compose.langsmith.yml and a private .secrets/langsmith_api_key file. Raw graph tracing is disabled. External export is not verified without account configuration.
