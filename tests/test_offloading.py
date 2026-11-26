from fastapi.testclient import TestClient

from ai_engine.environment import ACTION_NAMES, OffloadingEnvironment, TaskScenario, estimate_outcome
from ai_engine.dqn_agent import select_policy_action
from edge_server.edge import app as edge_app
from cloud_server.cloud import app as cloud_app


def test_decisions_are_valid_and_respect_server_availability(tmp_path):
    scenario = TaskScenario(4, 0.7, 40, 0.8, 0.4, 0.3, 35)
    action, policy = select_policy_action(scenario.state(), tmp_path / "unavailable.pt", [0])
    assert action == 0
    assert policy == "greedy_estimate_fallback"
    outcome = estimate_outcome(scenario, action)
    assert outcome["success"]
    assert ACTION_NAMES[action] == "local"


def test_environment_generates_normalized_states_and_transitions():
    environment = OffloadingEnvironment(seed=12)
    state = environment.reset()
    assert state.shape == (7,)
    assert (state >= 0).all() and (state <= 1).all()
    next_state, reward, done, info = environment.step(1)
    assert next_state.shape == (7,)
    assert isinstance(reward, float)
    assert done is True
    assert "delay_seconds" in info


def test_failed_tasks_receive_a_strictly_worse_reward():
    scenario = TaskScenario(4, 0.7, 40, 0.8, 0.95, 0.3, 35)
    failed = estimate_outcome(scenario, action=1, uniform_sample=0.0)
    succeeded = estimate_outcome(scenario, action=1, uniform_sample=1.0)
    assert failed["success"] is False
    assert succeeded["success"] is True
    assert failed["reward"] < succeeded["reward"]


def test_giga_cycle_estimates_use_seconds_not_milliseconds():
    scenario = TaskScenario(0.1, 1.0, 10, 1.0, 0.1, 0.1, 100)
    local = estimate_outcome(scenario, action=0)
    assert 0 < local["delay_seconds"] < 1


def test_edge_and_cloud_services_execute_real_compute_workloads():
    for app, server in ((edge_app, "edge"), (cloud_app, "cloud")):
        with TestClient(app) as client:
            assert client.get("/health").json()["server"] == server
            before = client.get("/resources").json()["completed_tasks"]
            response = client.post(
                "/execute",
                data={"task_type": "compute", "cpu_cycles_giga": "0.1"},
            )
            assert response.status_code == 200
            assert response.json()["result"]["digest"]
            metrics = response.json()["server_metrics"]
            assert metrics["server"] == server
            assert metrics["process_cpu_percent"] >= 0
            assert metrics["process_memory_bytes"] > 0
            assert metrics["cpu_utilization"] >= 0
            assert metrics["memory_utilization"] >= 0
            resources = client.get("/resources").json()
            assert resources["completed_tasks"] == before + 1


def test_edge_and_cloud_services_execute_document_workloads():
    for app, server in ((edge_app, "edge"), (cloud_app, "cloud")):
        with TestClient(app) as client:
            response = client.post(
                "/execute",
                data={"task_type": "document", "cpu_cycles_giga": "0.01"},
                files={"file": ("report.txt", b"Offloaded document analysis text.", "text/plain")},
            )
            assert response.status_code == 200
            result = response.json()["result"]
            assert result["characters_extracted"] == len("Offloaded document analysis text.")
            assert result["text"] == "Offloaded document analysis text."
            assert response.json()["server_metrics"]["server"] == server
