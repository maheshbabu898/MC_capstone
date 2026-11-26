from dataclasses import dataclass

import numpy as np


STATE_DIM = 7
ACTION_NAMES = ("local", "edge", "cloud")


@dataclass(frozen=True)
class TaskScenario:
    input_size_mb: float
    cpu_cycles_giga: float
    network_latency_ms: float
    mobile_cpu_available: float
    edge_cpu_utilization: float
    cloud_cpu_utilization: float
    bandwidth_mbps: float

    def state(self) -> np.ndarray:
        return np.asarray(
            [
                np.clip(self.input_size_mb / 20.0, 0.0, 1.0),
                np.clip(self.cpu_cycles_giga / 2.0, 0.0, 1.0),
                np.clip(self.network_latency_ms / 300.0, 0.0, 1.0),
                np.clip(self.mobile_cpu_available, 0.0, 1.0),
                np.clip(self.edge_cpu_utilization, 0.0, 1.0),
                np.clip(self.cloud_cpu_utilization, 0.0, 1.0),
                np.clip(self.bandwidth_mbps / 100.0, 0.0, 1.0),
            ],
            dtype=np.float32,
        )


def estimate_outcome(
    scenario: TaskScenario, action: int, uniform_sample: float = 1.0
) -> dict[str, float | bool]:
    if action not in range(len(ACTION_NAMES)):
        raise ValueError("Action must be 0 (local), 1 (edge), or 2 (cloud)")
    bandwidth = max(scenario.bandwidth_mbps, 0.25)
    if action == 0:
        compute_seconds = scenario.cpu_cycles_giga / max(
            0.25 + 2.5 * scenario.mobile_cpu_available, 0.25
        )
        transfer_seconds = 0.0
        utilization = 1.0 - scenario.mobile_cpu_available
        energy_joules = compute_seconds * 2.0
    else:
        utilization = (
            scenario.edge_cpu_utilization if action == 1 else scenario.cloud_cpu_utilization
        )
        compute_capacity = (12.0 if action == 1 else 24.0) * max(0.08, 1.0 - utilization)
        compute_seconds = scenario.cpu_cycles_giga / compute_capacity
        hop_count = 1.0 if action == 1 else 2.0
        transfer_seconds = (
            hop_count * scenario.network_latency_ms / 1000.0
            + scenario.input_size_mb * 8.0 / bandwidth
        )
        energy_joules = (
            scenario.input_size_mb * (0.05 if action == 1 else 0.07)
            + transfer_seconds * (0.25 if action == 1 else 0.35)
        )
    delay_seconds = compute_seconds + transfer_seconds
    overload_penalty = max(0.0, utilization - 0.85) * 2.0
    failure_probability = (
        max(0.0, utilization - 0.8) * 0.8
        + (0.12 if action > 0 and bandwidth < 1.0 else 0.0)
    )
    succeeded = uniform_sample >= failure_probability
    reward = (
        -(0.65 * delay_seconds + 0.35 * energy_joules + overload_penalty)
        if succeeded
        else -(25.0 + 0.65 * delay_seconds + 0.35 * energy_joules + overload_penalty)
    )
    return {
        "delay_seconds": delay_seconds,
        "energy_joules": energy_joules,
        "reward": reward,
        "success": succeeded,
        "overload_penalty": overload_penalty,
    }


class OffloadingEnvironment:
    def __init__(self, seed: int | None = None) -> None:
        self.random = np.random.default_rng(seed)
        self.scenario: TaskScenario | None = None

    def sample_scenario(self) -> TaskScenario:
        return TaskScenario(
            input_size_mb=float(self.random.uniform(0.05, 20.0)),
            cpu_cycles_giga=float(self.random.uniform(0.01, 2.0)),
            network_latency_ms=float(self.random.uniform(8.0, 260.0)),
            mobile_cpu_available=float(self.random.uniform(0.1, 1.0)),
            edge_cpu_utilization=float(self.random.uniform(0.05, 0.98)),
            cloud_cpu_utilization=float(self.random.uniform(0.02, 0.95)),
            bandwidth_mbps=float(self.random.uniform(0.5, 100.0)),
        )

    def reset(self) -> np.ndarray:
        self.scenario = self.sample_scenario()
        return self.scenario.state()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict[str, float | bool]]:
        if self.scenario is None:
            raise RuntimeError("Call reset before step")
        outcome = estimate_outcome(
            self.scenario, action, float(self.random.random())
        )
        next_state = self.reset()
        return next_state, float(outcome["reward"]), True, outcome
