from pathlib import Path
from functools import lru_cache
import random

import numpy as np
import torch
from torch import nn

from ai_engine.environment import ACTION_NAMES, STATE_DIM
from ai_engine.replay_buffer import ReplayBuffer


class QNetwork(nn.Module):
    def __init__(
        self,
        state_dim: int = STATE_DIM,
        action_dim: int = len(ACTION_NAMES),
        hidden_dim: int = 64,
    ) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.layers(state)


class DQNAgent:
    def __init__(
        self,
        state_dim: int = STATE_DIM,
        action_dim: int = len(ACTION_NAMES),
        hidden_dim: int = 64,
        learning_rate: float = 0.001,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.03,
        epsilon_decay: float = 0.995,
        seed: int = 7,
    ) -> None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.policy_network = QNetwork(state_dim, action_dim, hidden_dim)
        self.target_network = QNetwork(state_dim, action_dim, hidden_dim)
        self.target_network.load_state_dict(self.policy_network.state_dict())
        self.target_network.eval()
        self.optimizer = torch.optim.Adam(self.policy_network.parameters(), lr=learning_rate)
        self.loss_function = nn.SmoothL1Loss()
        self.replay_buffer = ReplayBuffer(seed=seed)

    def select_action(
        self, state: np.ndarray, explore: bool = True, available_actions: list[int] | None = None
    ) -> int:
        values = np.asarray(state, dtype=np.float32)
        if values.shape != (self.state_dim,) or not np.isfinite(values).all():
            raise ValueError(f"State must contain {self.state_dim} finite features")
        allowed = list(range(self.action_dim)) if available_actions is None else available_actions
        if not allowed or any(action < 0 or action >= self.action_dim for action in allowed):
            raise ValueError("available_actions must contain valid action indices")
        if explore and random.random() < self.epsilon:
            return random.choice(allowed)
        with torch.no_grad():
            tensor = torch.as_tensor(values, dtype=torch.float32).unsqueeze(0)
            q_values = self.policy_network(tensor)[0]
            return max(allowed, key=lambda action: float(q_values[action].item()))

    def remember(
        self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool
    ) -> None:
        self.replay_buffer.add(state, action, reward, next_state, done)

    def train_step(self, batch_size: int = 64) -> float | None:
        if len(self.replay_buffer) < batch_size:
            return None
        batch = self.replay_buffer.sample(batch_size)
        states = torch.as_tensor(np.stack([item.state for item in batch]), dtype=torch.float32)
        actions = torch.as_tensor([item.action for item in batch], dtype=torch.long)
        rewards = torch.as_tensor([item.reward for item in batch], dtype=torch.float32)
        next_states = torch.as_tensor(
            np.stack([item.next_state for item in batch]), dtype=torch.float32
        )
        dones = torch.as_tensor([item.done for item in batch], dtype=torch.float32)
        predicted = self.policy_network(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            future = self.target_network(next_states).max(dim=1).values
            target = rewards + self.gamma * future * (1.0 - dones)
        loss = self.loss_function(predicted, target)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_network.parameters(), 1.0)
        self.optimizer.step()
        return float(loss.item())

    def update_target(self) -> None:
        self.target_network.load_state_dict(self.policy_network.state_dict())

    def decay_exploration(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dim": self.state_dim,
                "action_dim": self.action_dim,
                "hidden_dim": self.hidden_dim,
                "policy_network": self.policy_network.state_dict(),
            },
            destination,
        )

    @classmethod
    def load(cls, path: str | Path) -> "DQNAgent":
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        hidden_dim = int(checkpoint.get("hidden_dim", 64))
        agent = cls(
            state_dim=int(checkpoint["state_dim"]),
            action_dim=int(checkpoint["action_dim"]),
            hidden_dim=hidden_dim,
            epsilon=0.0,
        )
        agent.policy_network.load_state_dict(checkpoint["policy_network"])
        agent.update_target()
        agent.epsilon = 0.0
        return agent


@lru_cache(maxsize=4)
def _load_cached_agent(path: str, modified_at: int) -> DQNAgent:
    del modified_at
    return DQNAgent.load(path)


def select_policy_action(
    state: np.ndarray, model_path: str | Path, available_actions: list[int] | None = None
) -> tuple[int, str]:
    path = Path(model_path)
    if path.is_file():
        agent = _load_cached_agent(str(path.resolve()), path.stat().st_mtime_ns)
        return agent.select_action(
            state, explore=False, available_actions=available_actions
        ), "trained_dqn"
    # When no trained weights exist, use the same delay/energy model as the simulator.
    from ai_engine.environment import TaskScenario, estimate_outcome

    task = TaskScenario(
        float(state[0] * 20.0),
        float(state[1] * 2.0),
        float(state[2] * 300.0),
        float(state[3]),
        float(state[4]),
        float(state[5]),
        float(state[6] * 100.0),
    )
    candidates = available_actions if available_actions is not None else list(range(len(ACTION_NAMES)))
    action = min(
        candidates,
        key=lambda index: -float(estimate_outcome(task, index)["reward"]),
    )
    return action, "greedy_estimate_fallback"
