from io import BytesIO
import sqlite3

import httpx
from fastapi.testclient import TestClient
from PIL import Image

from cloud_server.cloud import app as cloud_app
from backend.config import settings
from backend.database import initialize_database
from backend.main import app
from backend.routes import offloading as offloading_routes
from edge_server.edge import app as edge_app


def test_health_and_task_lifecycle(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "test.sqlite3")
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "edge_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "cloud_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "model_path", tmp_path / "missing-model.pt")
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/health").json()["status"] == "healthy"
        created = client.post(
            "/api/tasks/create",
            json={"task_type": "compute", "name": "API workload", "cpu_cycles_giga": 0.01},
        )
        assert created.status_code == 201
        task_id = created.json()["id"]
        decision = client.post("/api/offloading/decide", json={"task_id": task_id})
        assert decision.status_code == 200
        assert decision.json()["location"] == "local"
        result = client.post("/api/offloading/execute", json={"task_id": task_id})
        assert result.status_code == 200
        assert result.json()["result"]["digest"]
        assert client.get(f"/api/tasks/{task_id}").json()["status"] == "completed"
        assert client.get("/api/analytics/performance").json()["completed"] == 1


def test_image_upload_validation_and_listing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "upload.sqlite3")
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    image = Image.new("RGB", (8, 8), color=(200, 30, 20))
    content = BytesIO()
    image.save(content, format="PNG")
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks/upload",
            data={"task_type": "image", "cpu_cycles_giga": "0.01"},
            files={"file": ("sample.png", content.getvalue(), "image/png")},
        )
        assert response.status_code == 201
        task = response.json()
        assert task["task_type"] == "image"
        assert "file_path" not in task
        assert (settings.upload_dir / f"{task['id']}.png").is_file()
        listing = client.get("/api/tasks")
        assert listing.status_code == 200
        assert listing.json()["count"] == 1


def test_upload_rejects_mismatched_or_unsupported_files(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "invalid.sqlite3")
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks/upload",
            data={"task_type": "image"},
            files={"file": ("payload.exe", b"not an image", "application/octet-stream")},
        )
        assert response.status_code == 415


def test_document_upload_and_text_extraction(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "document.sqlite3")
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "edge_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "cloud_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "model_path", tmp_path / "missing-model.pt")
    with TestClient(app) as client:
        uploaded = client.post(
            "/api/tasks/upload",
            data={"task_type": "document", "cpu_cycles_giga": "0.01"},
            files={"file": ("notes.txt", "Actual extracted content".encode(), "text/plain")},
        )
        assert uploaded.status_code == 201
        execution = client.post(
            "/api/offloading/execute", json={"task_id": uploaded.json()["id"]}
        )
        assert execution.status_code == 200
        assert execution.json()["result"]["text"] == "Actual extracted content"


def test_mobile_local_result_is_recorded_and_measured(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "mobile.sqlite3")
    monkeypatch.setattr(settings, "edge_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "cloud_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "model_path", tmp_path / "missing-model.pt")
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks/create",
            json={"task_type": "compute", "name": "Phone workload", "cpu_cycles_giga": 0.01},
        ).json()
        client.post("/api/offloading/decide", json={"task_id": created["id"]})
        result = client.post(
            "/api/offloading/execute",
            json={
                "task_id": created["id"],
                "client_execution_seconds": 0.125,
                "client_result": {"checksum": "local-result"},
            },
        )
        assert result.status_code == 200
        assert result.json()["execution_seconds"] == 0.125
        assert result.json()["result"]["checksum"] == "local-result"


def test_offloaded_execution_routes_to_selected_edge_or_cloud(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "remote.sqlite3")
    monkeypatch.setattr(settings, "edge_url", "http://edge.test")
    monkeypatch.setattr(settings, "cloud_url", "http://cloud.test")
    snapshot = {
        "mobile": {"cpu_utilization": 0.2},
        "edge": {"available": True, "cpu_utilization": 0.2},
        "cloud": {"available": True, "cpu_utilization": 0.3},
        "network": {"latency_ms": 40, "bandwidth_mbps": 50},
    }

    async def resources_snapshot():
        return snapshot

    monkeypatch.setattr(offloading_routes, "resources", resources_snapshot)
    for action, expected_url in ((1, settings.edge_url), (2, settings.cloud_url)):
        monkeypatch.setattr(
            offloading_routes,
            "select_policy_action",
            lambda state, model, available, chosen=action: (chosen, "trained_dqn"),
        )
        visited = []

        async def execute_remotely(task, url):
            visited.append(url)
            return {"worker": url}, 0.025, 0.015, {"server": url}

        monkeypatch.setattr(offloading_routes, "_execute_remotely", execute_remotely)
        with TestClient(app) as client:
            created = client.post(
                "/api/tasks/create",
                json={"task_type": "compute", "name": "Remote task", "cpu_cycles_giga": 0.01},
            ).json()
            decision = client.post(
                "/api/offloading/decide", json={"task_id": created["id"]}
            )
            assert decision.status_code == 200
            assert decision.json()["location"] == ("edge" if action == 1 else "cloud")
            execution = client.post(
                "/api/offloading/execute", json={"task_id": created["id"]}
            )
            assert execution.status_code == 200
            assert execution.json()["result"]["worker"] == expected_url
            assert execution.json()["network_seconds"] == 0.015
            assert client.get(f"/api/tasks/{created['id']}").json()["server_metrics"] == {
                "server": expected_url
            }
        assert visited == [expected_url]


def test_backend_dispatches_real_requests_to_edge_and_cloud(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "integration.sqlite3")
    monkeypatch.setattr(settings, "edge_url", "http://edge.integration")
    monkeypatch.setattr(settings, "cloud_url", "http://cloud.integration")
    services = {
        "edge.integration": edge_app,
        "cloud.integration": cloud_app,
    }

    class ServiceRouter(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            service = services.get(request.url.host)
            if service is None:
                return httpx.Response(503, request=request, json={"detail": "Server unavailable"})
            return await httpx.ASGITransport(app=service).handle_async_request(request)

        async def aclose(self):
            return None

    real_async_client = httpx.AsyncClient

    def service_client(**kwargs):
        return real_async_client(
            timeout=kwargs.get("timeout"),
            transport=ServiceRouter(),
        )

    monkeypatch.setattr(offloading_routes.httpx, "AsyncClient", service_client)

    for action, location, service_url in (
        (1, "edge", settings.edge_url),
        (2, "cloud", settings.cloud_url),
    ):
        monkeypatch.setattr(
            offloading_routes,
            "select_policy_action",
            lambda state, model, available, selected=action: (selected, "trained_dqn"),
        )
        with TestClient(app) as client:
            created = client.post(
                "/api/tasks/create",
                json={
                    "task_type": "compute",
                    "name": f"{location.title()} integration workload",
                    "cpu_cycles_giga": 0.01,
                },
            )
            assert created.status_code == 201
            task_id = created.json()["id"]
            decision = client.post("/api/offloading/decide", json={"task_id": task_id})
            assert decision.status_code == 200
            assert decision.json()["location"] == location

            executed = client.post("/api/offloading/execute", json={"task_id": task_id})
            assert executed.status_code == 200
            response = executed.json()
            assert response["status"] == "completed"
            assert response["location"] == location
            assert response["execution_seconds"] >= 0
            assert response["result"]["digest"]
            assert response["server_metrics"]["server"] == location
            assert 0 <= response["server_metrics"]["cpu_utilization"] <= 1
            assert 0 <= response["server_metrics"]["memory_utilization"] <= 1
            assert response["server_metrics"]["process_memory_bytes"] > 0

            persisted = client.get(f"/api/tasks/{task_id}").json()
            assert persisted["status"] == "completed"
            assert persisted["execution_location"] == location
            assert persisted["result"]["digest"] == response["result"]["digest"]
            assert persisted["server_metrics"]["server"] == location
            assert persisted["execution_seconds"] == response["execution_seconds"]
            assert persisted["network_seconds"] >= 0

            uploaded = client.post(
                "/api/tasks/upload",
                data={"task_type": "document", "cpu_cycles_giga": "0.01"},
                files={
                    "file": (
                        "worker-notes.txt",
                        f"Executed independently on {location}.".encode(),
                        "text/plain",
                    )
                },
            )
            assert uploaded.status_code == 201
            document_id = uploaded.json()["id"]
            document_decision = client.post(
                "/api/offloading/decide", json={"task_id": document_id}
            )
            assert document_decision.status_code == 200
            assert document_decision.json()["location"] == location
            document_execution = client.post(
                "/api/offloading/execute", json={"task_id": document_id}
            )
            assert document_execution.status_code == 200
            assert document_execution.json()["result"]["text"] == (
                f"Executed independently on {location}."
            )
            assert document_execution.json()["server_metrics"]["server"] == location


def test_remote_failure_is_recorded_and_unavailable_cloud_is_excluded(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "database_path", tmp_path / "failure.sqlite3")
    monkeypatch.setattr(settings, "edge_url", "http://edge.integration")
    monkeypatch.setattr(settings, "cloud_url", "http://unavailable.integration")

    class ServiceRouter(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            if request.url.path == "/resources" and request.url.host == "edge.integration":
                return httpx.Response(
                    200,
                    request=request,
                    json={"cpu_utilization": 0.1, "memory_utilization": 0.1},
                )
            if request.url.path == "/resources":
                raise httpx.ConnectError("service unavailable", request=request)
            return httpx.Response(
                503, request=request, json={"detail": "edge unavailable"}
            )

        async def aclose(self):
            return None

    real_async_client = httpx.AsyncClient

    def service_client(**kwargs):
        return real_async_client(timeout=kwargs.get("timeout"), transport=ServiceRouter())

    monkeypatch.setattr(offloading_routes.httpx, "AsyncClient", service_client)
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks/create",
            json={"task_type": "compute", "name": "Unavailable edge", "cpu_cycles_giga": 0.01},
        ).json()
        decision = client.post("/api/offloading/decide", json={"task_id": created["id"]})
        assert decision.status_code == 200
        assert decision.json()["location"] == "local"

        monkeypatch.setattr(
            offloading_routes,
            "select_policy_action",
            lambda state, model, available: (1, "trained_dqn"),
        )
        retry = client.post("/api/offloading/decide", json={"task_id": created["id"]})
        assert retry.status_code == 200
        assert retry.json()["location"] == "edge"
        failed = client.post("/api/offloading/execute", json={"task_id": created["id"]})
        assert failed.status_code == 502
        persisted = client.get(f"/api/tasks/{created['id']}").json()
        assert persisted["status"] == "failed"
        assert "failed" in persisted["error_message"]


def test_existing_sqlite_database_migrates_for_server_metrics(tmp_path, monkeypatch):
    database_path = tmp_path / "existing.sqlite3"
    monkeypatch.setattr(settings, "database_path", database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                name TEXT NOT NULL,
                input_size_mb REAL NOT NULL,
                cpu_cycles_giga REAL NOT NULL,
                file_path TEXT,
                status TEXT NOT NULL,
                execution_location TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                execution_seconds REAL,
                network_seconds REAL,
                estimated_latency_ms REAL,
                estimated_energy_joules REAL,
                estimated_reward REAL,
                state_json TEXT,
                decision_json TEXT,
                result_json TEXT,
                error_message TEXT
            )
            """
        )

    initialize_database()
    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
    assert "server_metrics_json" in columns
