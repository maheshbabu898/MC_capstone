import numpy as np
import pytest

from ai_engine.dqn_agent import DQNAgent
from ai_engine.environment import OffloadingEnvironment
from ai_engine.evaluate import evaluate


def test_dqn_selects_available_actions_and_rejects_invalid_state():
    agent = DQNAgent(seed=4)
    state = OffloadingEnvironment(seed=4).reset()
    assert agent.select_action(state, explore=False, available_actions=[2]) == 2
    with pytest.raises(ValueError):
        agent.select_action(np.zeros(6, dtype=np.float32))


def test_replay_training_and_model_round_trip(tmp_path):
    agent = DQNAgent(seed=3)
    environment = OffloadingEnvironment(seed=3)
    state = environment.reset()
    for _ in range(8):
        next_state, reward, done, _ = environment.step(0)
        agent.remember(state, 0, reward, next_state, done)
        state = next_state
    assert agent.train_step(batch_size=4) is not None
    destination = tmp_path / "model.pt"
    agent.save(destination)
    restored = DQNAgent.load(destination)
    assert restored.select_action(state, explore=False) in range(3)


def test_benchmark_generates_results_from_environment(monkeypatch, tmp_path):
    monkeypatch.setattr("ai_engine.evaluate.ROOT", tmp_path)
    summary = evaluate(tasks=3, seed=2)
    assert summary["total_simulated_decisions"] == 18
    assert summary["results_are_simulated"] is True
    assert (tmp_path / "results" / "reports" / "benchmark_results.csv").is_file()
    assert (tmp_path / "results" / "graphs" / "location_distribution.png").is_file()
