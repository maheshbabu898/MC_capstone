import argparse
from collections import Counter
import json
import os
from pathlib import Path
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from ai_engine.dqn_agent import DQNAgent
from ai_engine.environment import ACTION_NAMES, OffloadingEnvironment, estimate_outcome


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
POLICIES = ("dqn", "local_only", "edge_only", "cloud_only", "greedy", "random")


def evaluate(tasks: int = 250, seed: int = 42) -> dict[str, object]:
    if tasks < 1:
        raise ValueError("tasks must be at least one")
    rng = np.random.default_rng(seed)
    random_policy = random.Random(seed)
    env = OffloadingEnvironment(seed)
    scenarios = [env.sample_scenario() for _ in range(tasks)]
    model_path = Path(os.getenv("MEC_MODEL_PATH", str(ROOT / "ai_engine" / "models" / "dqn.pt")))
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    agent = DQNAgent.load(model_path) if model_path.is_file() else None
    records: list[dict[str, object]] = []
    for index, scenario in enumerate(scenarios):
        success_sample = float(rng.random())
        for policy in POLICIES:
            if policy == "dqn" and agent:
                action = agent.select_action(scenario.state(), explore=False)
            elif policy in ("dqn", "greedy"):
                action = max(
                    range(3), key=lambda value: float(estimate_outcome(scenario, value)["reward"])
                )
            elif policy.endswith("_only"):
                action = ACTION_NAMES.index(policy.removesuffix("_only"))
            else:
                action = random_policy.randrange(3)
            outcome = estimate_outcome(scenario, action, success_sample)
            records.append({
                "task_index": index,
                "policy": policy,
                "action": action,
                "location": ACTION_NAMES[action],
                "latency_seconds": float(outcome["delay_seconds"]),
                "energy_joules": float(outcome["energy_joules"]),
                "reward": float(outcome["reward"]),
                "success": bool(outcome["success"]),
            })
    frame = pd.DataFrame.from_records(records)
    report_dir = ROOT / "results" / "reports"
    graph_dir = ROOT / "results" / "graphs"
    report_dir.mkdir(parents=True, exist_ok=True)
    graph_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(report_dir / "benchmark_results.csv", index=False)
    summary = frame.groupby("policy", sort=False).agg(
        average_latency_seconds=("latency_seconds", "mean"),
        average_energy_joules=("energy_joules", "mean"),
        success_rate=("success", "mean"),
        average_reward=("reward", "mean"),
    ).reset_index()
    summary.to_csv(report_dir / "benchmark_summary.csv", index=False)
    (report_dir / "benchmark_summary.json").write_text(
        json.dumps(summary.to_dict(orient="records"), indent=2), encoding="utf-8"
    )
    for column, filename, title, ylabel in (
        ("average_latency_seconds", "latency_comparison.png", "Average simulated latency", "Seconds"),
        ("average_energy_joules", "energy_comparison.png", "Average estimated energy", "Joules"),
        ("success_rate", "success_rate_comparison.png", "Simulated task success rate", "Success rate"),
        ("average_reward", "reward_comparison.png", "Average policy reward", "Reward"),
        ("average_latency_seconds", "execution_time_comparison.png", "Execution time comparison", "Seconds"),
    ):
        ax = summary.set_index("policy")[column].plot(kind="bar", figsize=(9, 4.5), legend=False)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=25)
        plt.tight_layout()
        plt.savefig(graph_dir / filename, dpi=140)
        plt.close()
    distribution = frame.groupby(["policy", "location"]).size().unstack(fill_value=0)
    ax = distribution.plot(kind="bar", stacked=True, figsize=(9, 4.5))
    ax.set_title("Execution-location distribution by policy")
    ax.set_ylabel("Tasks")
    ax.tick_params(axis="x", rotation=25)
    plt.tight_layout()
    plt.savefig(graph_dir / "location_distribution.png", dpi=140)
    plt.close()
    return {
        "tasks_per_policy": tasks,
        "total_simulated_decisions": len(records),
        "seed": seed,
        "results_are_simulated": True,
        "dqn_model_loaded": agent is not None,
        "comparison": summary.to_dict(orient="records"),
        "locations": {policy: dict(Counter(frame.loc[frame.policy == policy, "location"]))
                      for policy in POLICIES},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare MEC offloading policies")
    parser.add_argument("--tasks", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    arguments = parser.parse_args()
    print(json.dumps(evaluate(arguments.tasks, arguments.seed), indent=2))
