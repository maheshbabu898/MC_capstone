# AI-Driven Mobile Edge Computing

A runnable academic MEC system with a FastAPI/SQLite backend, a PyTorch DQN task-offloading agent, separate edge/cloud execution services, a Flutter client, and a React analytics dashboard. The benchmark environment is explicitly **simulated**; processing time for an executed workload is measured on its execution server.

## What works

- Create, list, inspect, and upload bounded-size computation, image, PDF, DOCX, and UTF-8 text tasks. Uploaded files are validated and stored outside the API response.
- Run configurable repeated-SHA-256 compute workloads, extract text from PDF/DOCX/TXT, and classify images with pretrained torchvision MobileNetV2. The first image classification downloads torchvision's pretrained weights if they are not cached.
- Produce seven-feature resource states and learn a DQN policy with a replay buffer, target network, epsilon-greedy exploration, and saved PyTorch weights. When no checkpoint exists, the API reports `greedy_estimate_fallback` and selects a feasible action by minimizing the simulator's delay/energy cost model.
- Execute tasks locally or send their inputs to separately runnable edge/cloud HTTP services. Unavailable remote servers are excluded from new decisions. Failed processing is recorded as failed, not reported as successful.
- Export repeatable, seeded **simulated** strategy comparisons, CSVs, and graphs for DQN, local-only, edge-only, cloud-only, greedy, and random policies.
- Serve interactive API docs at `/docs`; configure the API's allowed browser origins with `MEC_ALLOWED_ORIGINS`.

Estimated network latency/bandwidth, offloading delay, and energy are **simulation estimates**, not device-level measurements. `execution_seconds` is elapsed processing time measured on the executing device or server; remote `network_seconds` is an HTTP round-trip residual estimate.

The Flutter client's local **compute** workload executes on the phone and reports its measured duration and checksum back to the API. Local image/document processing currently runs through the backend's Python processor; this Flutter package does not bundle an on-device MobileNetV2 or PDF/DOCX runtime. Edge and cloud decisions execute in their corresponding remote services.

## Requirements and setup (Windows PowerShell)

Python 3.13, Node.js 20+, and Flutter with Android toolchains are recommended. Use Python 3.11–3.13 for the backend. Docker is optional. This workspace has Python 3.13 and Node.js; Flutter, Android tooling, and Docker were not installed when this project was created.

```powershell
cd C:\Users\bmahe\AI-Mobile-Edge-Computing
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The virtual environment already present in this workspace can be reused. PyTorch/torchvision wheels and the pretrained MobileNetV2 weights are substantial downloads. If PowerShell blocks activation, use `venv\Scripts\python.exe -m pip install -r requirements.txt` without activating.

## Run without Docker

Open **four PowerShell terminals** at the project root. Activate the existing virtual environment in each:

```powershell
cd C:\Users\bmahe\AI-Mobile-Edge-Computing
.\venv\Scripts\Activate.ps1
```

In the four terminals, start one process per terminal:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
python -m uvicorn edge_server.edge:app --host 0.0.0.0 --port 8001
python -m uvicorn cloud_server.cloud:app --host 0.0.0.0 --port 8002
cd C:\Users\bmahe\AI-Mobile-Edge-Computing\dashboard; npm run dev
```

The three API processes expose `/health`; edge/cloud additionally expose `/resources` and `/execute`. Check `http://127.0.0.1:8001/health`, `http://127.0.0.1:8002/health`, and backend `http://127.0.0.1:8000/api/monitoring/resources`. Remote actions are omitted from DQN decisions until their `/resources` endpoint responds. When a selected server becomes unavailable during execution, the backend marks that task `failed` in SQLite and returns HTTP 502; the failed task can be retried after service recovery. Backend interactive API docs: <http://127.0.0.1:8000/docs>.

Each successful remote execution includes actual workload output, measured `execution_seconds`, HTTP round-trip residual `network_seconds`, and `server_metrics`. Edge/cloud metrics include sampled host `cpu_utilization` and `memory_utilization`, service-process `process_cpu_percent` and `process_cpu_seconds`, process RSS bytes/utilization, and a UTC sampling time. Host CPU/memory describe the shared host; service-process CPU is aggregate across its concurrent tasks. Metrics and workload output are returned by `/api/offloading/execute` and persisted with the task; inspect them with `GET /api/tasks/{task_id}`.

If activating scripts is disabled by PowerShell policy, use `.\venv\Scripts\python.exe -m uvicorn ...` in each terminal instead. The dashboard starts with `cd C:\Users\bmahe\AI-Mobile-Edge-Computing\dashboard; npm run dev` and uses the API at `http://127.0.0.1:8000`.

## Train, benchmark, and test

```powershell
python -m ai_engine.train --episodes 5000 --seed 7
python -m ai_engine.evaluate --tasks 250 --seed 42
python -m pytest -q
```

Training writes `ai_engine\models\dqn.pt`, `results\graphs\training_reward.png`, and a JSON training report. Evaluation runs all six policies against the same seeded task scenarios and writes the per-task dataset, grouped summary, and four graphs under `results\reports` and `results\graphs`. DQN benchmark results are marked `dqn_model_loaded`; if the checkpoint does not exist, the DQN entry is the disclosed greedy-estimate fallback. `GET /api/analytics/comparison?tasks=100&seed=42` runs a fresh seeded simulation and returns its comparison; `/api/analytics/performance` summarizes real tasks persisted in SQLite.

The generated seed-42 comparison used 250 scenarios per policy. Mean simulated latency / estimated energy / success rate / mean reward were: DQN **0.647 s / 0.982 J / 100% / -0.767**; local-only **0.658 s / 1.315 J / 99.6% / -0.989**; edge-only **4.826 s / 1.637 J / 99.2% / -3.933**; cloud-only **4.789 s / 2.341 J / 100% / -3.942**; greedy **0.643 s / 0.978 J / 100% / -0.762**; random **2.939 s / 1.649 J / 99.2% / -2.701**. In this repeatable run, the learned DQN chose all three execution locations and performed close to the cost-model greedy baseline. All figures are simulated, not physical-device measurements.


## Dashboard

```powershell
cd dashboard
npm install
npm run dev
```

Set `VITE_API_URL` in `dashboard\.env.local` (for example `VITE_API_URL=http://127.0.0.1:8000`) when the API is not at its default. Vite serves the dashboard at <http://localhost:5173>. `npm run build` makes a production build.

## Flutter Android application

Install Flutter and the Android SDK. Because Flutter was not installed while this project was assembled, its generated Android/Gradle platform scaffold is not included; generate it once from the existing Flutter package directory without passing `--overwrite`, which preserves the checked-in Dart application:

```powershell
cd mobile_app
flutter create --platforms=android --project-name mec_intelligent_offloading .
flutter pub get
flutter run --dart-define=MEC_API_BASE_URL=http://10.0.2.2:8000
```

The Android emulator reaches the host computer using `10.0.2.2`, not `localhost`. For a physical phone, provide the computer's reachable LAN address, for example `--dart-define=MEC_API_BASE_URL=http://192.168.1.20:8000`, and allow inbound port 8000 in the Windows firewall. The app also includes a backend-URL settings screen. API CORS allows browser origins only; mobile HTTP requests do not use browser CORS.

The Android manifest allows cleartext HTTP for local development against emulator/LAN servers. Do not expose this development configuration on an untrusted network; use HTTPS for production deployments.

## Docker Compose (optional)

Install and start Docker Desktop first. From the project root:

```powershell
Copy-Item .env.example .env
docker compose up --build
docker compose down
```

Services listen on ports 8000 (API), 8001 (edge), and 8002 (cloud). SQLite and uploaded files persist in a named volume. Compose builds separate Python images; model weights are shared from `ai_engine\models`. The host-generated DQN checkpoint should be trained before starting Compose if the container should use it.

## API examples

```powershell
$task = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/tasks/create `
  -ContentType 'application/json' `
  -Body '{"task_type":"compute","name":"CPU workload","cpu_cycles_giga":0.1}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/offloading/decide `
  -ContentType 'application/json' -Body (@{task_id=$task.id} | ConvertTo-Json)
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/offloading/execute `
  -ContentType 'application/json' -Body (@{task_id=$task.id} | ConvertTo-Json)
```

Upload an image or supported document as `multipart/form-data` to `/api/tasks/upload` with `file`, `task_type=image|document`, and optional `cpu_cycles_giga`. Configure upload limits, service URLs, network simulation values, CORS origins, database, and model paths with the variables in `.env.example`.

## Layout

```text
backend/             FastAPI API, SQLite persistence, task routes
ai_engine/           DQN, replay memory, simulation, training, evaluation
execution/           Shared actual compute/image/document processing
edge_server/         Edge service and Dockerfile
cloud_server/        Cloud service and Dockerfile
mobile_app/          Flutter Android client source
dashboard/           React/Vite dashboard
tests/               API, offloading, DQN, and benchmark tests
results/              Generated graphs and experimental reports
```

## Notes

- Image inference requires downloading MobileNetV2 ImageNet weights on the first run; it does not silently substitute random predictions if model setup fails.
- Uploaded image classification needs sufficient RAM for the PyTorch runtime. The CPU workload and upload size are bounded at the API boundary.
- `MEC_MODEL_PATH`, `MEC_DATABASE_PATH`, `MEC_UPLOAD_DIR`, `MEC_EDGE_URL`, `MEC_CLOUD_URL`, `MEC_NETWORK_LATENCY_MS`, `MEC_BANDWIDTH_MBPS`, `MEC_MAX_UPLOAD_BYTES`, and `MEC_ALLOWED_ORIGINS` are configurable.
