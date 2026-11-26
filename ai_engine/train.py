import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv

from ai_engine.dqn_agent import DQNAgent
from ai_engine.environment import OffloadingEnvironment


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def train(episodes: int = 800, seed: int = 7) -> dict[str, object]:
    if episodes < 1:
        raise ValueError("episodes must be at least one")
    env = OffloadingEnvironment(seed)
    agent = DQNAgent(seed=seed)
    episode_rewards: list[float] = []
    episode_losses: list[float] = []
    for episode in range(episodes):
        state = env.reset()
        action = agent.select_action(state)
        _, reward, done, _ = env.step(action)
        next_state = env.scenario.state() if env.scenario is not None else state
        agent.remember(state, action, reward, next_state, done)
        loss = agent.train_step()
        if loss is not None:
            episode_losses.append(loss)
        episode_rewards.append(reward)
        agent.decay_exploration()
        if (episode + 1) % 25 == 0:
            agent.update_target()
    model_path = Path(os.getenv("MEC_MODEL_PATH", str(ROOT / "ai_engine" / "models" / "dqn.pt")))
    if not model_path.is_absolute():
        model_path = ROOT / model_path
    agent.save(model_path)
    report_dir = ROOT / "results" / "reports"
    graph_dir = ROOT / "results" / "graphs"
    report_dir.mkdir(parents=True, exist_ok=True)
    graph_dir.mkdir(parents=True, exist_ok=True)
    window = min(50, episodes)
    smoothed = np.convolve(episode_rewards, np.ones(window) / window, mode="valid")
    plt.figure(figsize=(9, 4.5))
    plt.plot(episode_rewards, alpha=0.25, label="Episode reward")
    plt.plot(np.arange(window - 1, episodes), smoothed, label=f"{window}-episode mean")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.title("DQN training reward")
    plt.legend()
    plt.tight_layout()
    plt.savefig(graph_dir / "training_reward.png", dpi=140)
    plt.close()
    report = {
        "episodes": episodes,
        "seed": seed,
        "initial_mean_reward": float(np.mean(episode_rewards[:window])),
        "final_mean_reward": float(np.mean(episode_rewards[-window:])),
        "final_epsilon": agent.epsilon,
        "mean_training_loss": float(np.mean(episode_losses)) if episode_losses else None,
        "model_path": str(model_path),
        "results_are_simulated": True,
    }
    (report_dir / "training.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the MEC DQN offloading agent")
    parser.add_argument("--episodes", type=int, default=800)
    parser.add_argument("--seed", type=int, default=7)
    arguments = parser.parse_args()
    print(json.dumps(train(arguments.episodes, arguments.seed), indent=2))
