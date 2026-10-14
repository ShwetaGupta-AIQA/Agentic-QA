# Security review — 2026-10-13

## Active production blocker

pip-audit reported five entries (four unique PYSEC IDs) for chromadb 1.5.9; the audit data supplied no fixed versions. The package index showed 1.5.9 as the newest available version at verification time. No findings are suppressed. The CI dependency job fails and manual staging requires that job to pass.

- [PYSEC-2026-311](https://osv.dev/vulnerability/PYSEC-2026-311): remote-code execution risk in server collection configuration.
- [PYSEC-2026-3814](https://osv.dev/vulnerability/PYSEC-2026-3814): server collection-update code injection.
- [PYSEC-2026-3815](https://osv.dev/vulnerability/PYSEC-2026-3815): resource scoping in authorization.
- [PYSEC-2026-3813](https://osv.dev/vulnerability/PYSEC-2026-3813): cross-tenant authorization concerns.

The raw scan is preserved in ignored reports; checked-in security-scan.json summarizes it. The frontend dependency scan reported zero vulnerabilities. These scans do not prove the absence of other vulnerabilities.

The local demo keeps Chroma on an internal network with no published port, uses fixed collection identity and explicit precomputed embeddings, and exposes no generic Chroma collection/configuration API. This reduces exposure; it is not a claim that the dependency is patched or that a compromised internal client is harmless. Keep the demo local until the findings are resolved or formally reviewed with evidence.

## Trust boundaries

The browser first authenticates to the gateway with a generated login. The gateway injects a separate private API capability. Reviewer authorization additionally requires the configured reviewer identity and bearer credential forwarded via X-QA-Reviewer; clients cannot replace the gateway capability. The API is not directly published. This provides single-operator demonstration access control, not named-user RBAC or tenant isolation.

Tests, retrieved documents and model output are untrusted. Pydantic models reject invalid structures; registered fixed suites prevent arbitrary code/URLs from reaching the worker. Release gates are deterministic and cannot be overridden by model explanations. Source hashes and freshness are checked again before a decision. These hashes protect changes during review; they are not signatures against an administrator who can rewrite files and hashes.

Workers receive the database queue credential but no LLM key, gateway secret or release-review token. They run non-root under filesystem/network/resource constraints. Artifact volumes and PostgreSQL remain trusted sensitive storage; the current service role is not least-privilege per component. Production needs separate DB roles, encryption/secret lifecycle, per-user audit identity, admission/rate controls and further threat testing.

Logs exclude bodies, query strings, full URLs and exception text. No trace includes requirements or customer data. Optional LangSmith uploads only sanitized metadata; external export is not enabled or verified locally. Native development is intentionally unauthenticated on loopback and must not be exposed publicly.
