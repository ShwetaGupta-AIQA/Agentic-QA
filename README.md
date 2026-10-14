# Agentic QA Platform

Turn a requirement into proposed tests, review the results, run approved demo tests, and see what evidence is missing before a release.

This application helps a QA engineer work through the testing lifecycle. You stay in control: you review the analysis, approve test execution, and make the final release decision.

**Start with demo mode. No AI API key is needed.** The demo uses synthetic e-commerce examples and fixed registered tests. Public production deployment remains blocked by unresolved Chroma security advisories; see [security details](docs/security.md).

## Choose how to run it

| Option | Best for | Open in your browser |
|---|---|---|
| **Docker demo — recommended** | Trying the complete app, including persistent workflows and a separate test worker | http://127.0.0.1:8080 |
| Native development | Editing Python/React code or configuring your own AI provider | http://127.0.0.1:5174 |

The instructions below use **Windows PowerShell**. Run commands one block at a time. Keep the terminal open until a command finishes.

## Before you start

For the Docker demo, install:

- Git, to download the project.
- Python 3.12, to create the local setup tools. The containers run the app itself.
- Docker Desktop with Linux containers. **Start Docker Desktop before running Compose commands.**

For native development, also install Node.js 24, which includes npm. Docker users do not need Node.js installed on their computer.

Check your tools:

```powershell
git --version
py -3.12 --version
docker compose version
```

If a command is not recognized, install that tool and reopen PowerShell. Your computer needs internet access and enough disk space for the first container build, which downloads dependencies and a browser.

## Quick start: Docker demo

### 1. Download the project

Open PowerShell in the folder where you want to keep the project:

```powershell
git clone https://github.com/ShwetaGupta-AIQA/Agentic-QA.git
cd Agentic-QA
```

You are now in the **project root**, the folder containing README.md and docker-compose.yml. Run all Docker commands from this folder.

### 2. Generate your private login credentials

```powershell
py -3.12 -m venv .tools
.tools/Scripts/python.exe -m pip install bcrypt
.tools/Scripts/python.exe scripts/setup_demo.py
```

This creates the private `.secrets` folder automatically. You do not need to edit application code or backend/.env for the Docker demo. Running the setup script again preserves existing credentials.

### 3. Start the application

```powershell
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
```

The first build can take several minutes. Once started, frontend, backend, worker, postgres and chroma should show healthy status. If startup times out, check the troubleshooting table below.

### 4. Open the app and sign in

Open **http://127.0.0.1:8080**. Your browser will ask for a username and password.

Open `.secrets/demo-login.json` locally in your editor. Use its `username` and `password` values in the browser prompt. Keep this file private.

There are two different credentials:

| File | What it is for |
|---|---|
| `.secrets/demo-login.json` | Username/password for opening the Docker demo |
| `.secrets/reviewer_token` | Separate credential for confirming defect/risk evidence and recording a release decision |

The configured reviewer name is `local-reviewer`. You do not need the reviewer token to explore requirements or run approved demo suites.

### 5. Stop or start it again

```powershell
# Stop the application, keeping stored data
docker compose stop

# Start the existing containers again
docker compose start
```

Avoid `docker compose down -v` unless you intentionally want to delete the stored database, knowledge and artifacts.

## Your first workflow

### Analyze a requirement

1. Select **Requirements** in the sidebar.
2. Enter a requirement, for example:

   > A valid coupon gives a 10% discount during checkout. The coupon can be used once per customer, and expired coupons must be rejected.

3. Click **Run Requirements Agent**.
4. Read the proposed scenarios, ambiguities and risks. Demo mode uses deterministic rules; it does not call an AI provider.
5. Click **Approve analysis** only after reviewing it. This generates a proposed test package; it does not execute tests.
6. Follow **Review test cases** and **Explore synthetic data** to inspect the generated package. Use synthetic requirements while trying the demo.

### Execute the registered demo tests

1. Open **Executions**.
2. Select the registered commerce suites you want to run. The ten ECOM suite IDs cover 15 API/browser tests.
3. Review the selection and tick the execution approval checkbox.
4. Click **Execute approved tests**. Wait for the run to finish, then inspect its outcomes and artifacts.
5. Copy the execution ID if you want to assess release readiness.

**Generated test descriptions do not automatically become executable tests.** Execution runs the fixed registered suites against an owned synthetic commerce application, not a website or production system of your choice.

### Assess release readiness

1. Open **Release Readiness** and enter a release ID of your choice, such as `demo-release-1`.
2. Paste the execution ID into **Execution IDs**.
3. Click **Evaluate release gates**. Examine the recommendation and each gate.

Passing tests alone can still produce **NO-GO**: missing confirmed defect/risk review is unknown evidence, not proof of zero defects.

To supply that evidence, an authorized reviewer opens **Authorized defect and regression-risk evidence review**, enters the separate reviewer credential, reviews the actual defect register and regression risks, writes notes, and explicitly confirms the review. Select the resulting review and evaluate again. Do not claim an empty defect register unless it was actually reviewed.

| Recommendation | Meaning |
|---|---|
| GO | Required gates passed; human authorization is still needed |
| CONDITIONAL GO | Required gates passed, but remaining conditions need explicit acknowledgement |
| NO-GO | A required gate failed or evidence is missing |

A model cannot override blocking gates. Recording a release decision does not deploy the application.

## What do I need to edit?

**For the Docker demo: nothing in the application code.** Generate the credentials, start the containers, and use the UI.

| What you want to do | Where to configure it | What to change |
|---|---|---|
| Enter a different requirement | Requirements screen | Replace the sample text |
| Select demo tests | Executions screen | Choose registered ECOM suites and approve the selection |
| Configure a real AI provider in native mode | `backend/.env` | Set model mode, provider URL, API key and model name as shown below |
| Configure native release review | `backend/.env` | Set reviewer name and a private token of at least 32 characters |
| Change release thresholds | `data/release/policy.json` | Review pass-rate, coverage, defect, freshness and risk thresholds; reassess existing releases after changes |
| Configure Docker services | `docker-compose.yml` and secret files | Follow the [deployment guide](docs/deployment.md); Docker does not automatically read `backend/.env` |

Keep `.env`, `.secrets`, customer documents and runtime reports out of Git. Never place a private key inside frontend code or a `VITE_` environment variable.

## Optional: native development

Use this setup when you want to edit the application or configure your own AI provider. It runs the backend and frontend in **two separate terminals**.

### Terminal 1: backend

From the project root:

```powershell
cd backend
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock.txt

# Create .env only if it does not already exist
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

.venv/Scripts/python.exe -m playwright install chromium
```

Open `backend/.env` in your editor. Leave `QA_MODEL_MODE=demo` and `QA_EMBEDDING_MODE=demo` for an offline demo. Before using release-review actions, replace `QA_RELEASE_REVIEW_TOKEN` with your own randomly generated private value of at least 32 characters. The default reviewer name is `local-reviewer`.

To use a real AI provider, configure:

```dotenv
QA_MODEL_MODE=llm
QA_LLM_BASE_URL=https://your-provider.example/v1
QA_LLM_API_KEY=replace_with_your_private_key
QA_LLM_MODEL=replace_with_your_provider_model_id
```

These are placeholders. Use your provider's OpenAI-compatible API base URL and model identifier. Real AI mode sends submitted requirements to that provider and may incur charges. Embeddings are configured separately; leave them in demo mode unless you also configure an embedding provider.

Start the backend from the backend folder:

```powershell
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Keep this terminal running. After editing backend/.env, stop the backend with Ctrl+C and start it again.

### Terminal 2: frontend

Open another PowerShell terminal in the project root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open **http://127.0.0.1:5174**. Native mode has no browser login and must remain on loopback. Its default workflow checkpoints are in memory; restarting the backend loses pending workflow checkpoints. Docker mode uses PostgreSQL and preserves them.

## Troubleshooting

| Problem | What to check |
|---|---|
| `py`, Git or Docker is not recognized | Install the missing prerequisite, then reopen PowerShell |
| Docker cannot connect to its engine | Start Docker Desktop and wait until its Linux engine is running |
| Setup says bcrypt is missing | Use `.tools/Scripts/python.exe` and install bcrypt with that same interpreter |
| Docker startup times out or a service is unhealthy | Run `docker compose ps` and `docker compose logs --tail 50`; check the failing service before retrying startup |
| A port is already in use | Stop the previous app using that port; Docker uses 8080, native backend 8001 and frontend 5174 |
| Browser login fails | Use the username/password from `.secrets/demo-login.json`, not the reviewer token |
| Release review returns 403 | Check reviewer name and the separate token: Docker uses `.secrets/reviewer_token`, native mode uses `QA_RELEASE_REVIEW_TOKEN` in backend/.env |
| Release recommendation is NO-GO | Read the failed/unknown gates; supply fresh execution and reviewed defect/risk evidence rather than trying to override them |
| A native workflow disappears after restarting | Native default checkpoints are in memory; start a fresh workflow or use Docker persistence |
| CI dependency checks fail for Chroma | This is an unresolved security blocker, not a setup mistake; do not suppress it to deploy publicly |

## Optional checks

For a native setup, run backend tests from the backend folder:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

Run frontend checks from the frontend folder:

```powershell
npm.cmd test
npm.cmd run build
```

For Docker, run this from the project root after startup:

```powershell
.tools/Scripts/python.exe scripts/smoke.py --restart
```

The smoke check restarts the API and Chroma to verify persistence, then executes the registered synthetic suites. Run it when no other demo work is in progress.

## Architecture and limitations

The six specialized agents cover requirements analysis, test design, synthetic data, registered automation, defect analysis and release readiness. React provides the UI; FastAPI validates requests; LangGraph coordinates reviewed workflows. PostgreSQL, Chroma and artifact volumes provide Docker persistence. A separate worker runs approved tests, and scoped read-only MCP tools expose evidence.

[Architecture and decisions](docs/architecture.md) · [Deployment details](docs/deployment.md) · [Security review](docs/security.md)

This is a single-operator controlled demonstration. Enterprise user roles, tenant isolation, multi-replica audit handling and automated backup restore are future work. Production promotion remains blocked by the documented dependency advisories. Synthetic benchmark results are limited fixture measurements, not production AI accuracy claims.

## Public repository data policy

The repository includes synthetic app/test fixtures, release policies and aggregate benchmark summaries needed by the product. Personal notes, private reports, interview material, demo captures, private credentials and generated runtime reports are excluded. Do not contribute real customer data.
