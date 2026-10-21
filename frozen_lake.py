import argparse

import gymnasium as gym
import torch
from torch import nn

from skrl.agents.torch.q_learning import Q_LEARNING, Q_LEARNING_CFG
from skrl.envs.wrappers.torch import wrap_env
from skrl.models.torch import Model, TabularMixin
from skrl.trainers.torch import SequentialTrainer


class EpsilonGreedyPolicy(TabularMixin, Model):
    def __init__(self, observation_space, action_space, device, epsilon=0.1):
        Model.__init__(self, observation_space=observation_space, action_space=action_space, device=device)
        TabularMixin.__init__(self)
        self.epsilon = epsilon
        self.q_table = nn.Parameter(
            torch.ones((self.num_observations, self.num_actions), device=self.device),
            requires_grad=False,
        )

    def compute(self, inputs, role):
        observations = inputs["observations"]
        actions = torch.argmax(self.q_table[observations], dim=-1)
        explore = torch.rand(observations.shape[0], device=self.device) < self.epsilon
        actions[explore] = torch.randint(self.num_actions, (int(explore.sum()), 1), device=self.device)
        return actions, {}


def main():
    parser = argparse.ArgumentParser(description="Q-learning tabular en FrozenLake con skrl")
    parser.add_argument("--timesteps", type=int, default=20000)
    args = parser.parse_args()

    torch.manual_seed(42)
    environment = wrap_env(gym.make("FrozenLake-v1", is_slippery=False))
    policy = EpsilonGreedyPolicy(environment.observation_space, environment.action_space, environment.device)
    configuration = Q_LEARNING_CFG(learning_rate=0.1, discount_factor=0.99)
    agent = Q_LEARNING(
        models={"policy": policy},
        memory=None,
        cfg=configuration,
        observation_space=environment.observation_space,
        action_space=environment.action_space,
        device=environment.device,
    )
    trainer = SequentialTrainer(env=environment, agents=agent, cfg={"timesteps": args.timesteps, "headless": True})
    trainer.train()
    print("Tabla Q aprendida (filas: casillas; columnas: izquierda, abajo, derecha, arriba):")
    print(policy.q_table.detach().cpu().numpy().round(2))

    evaluation = gym.make("FrozenLake-v1", is_slippery=False)
    try:
        observation, _ = evaluation.reset(seed=42)
        for steps in range(1, 101):
            action = int(policy.q_table[observation].argmax().item())
            observation, reward, terminated, truncated, _ = evaluation.step(action)
            if terminated or truncated:
                break
        print(f"Evaluacion sin exploracion: {'meta alcanzada' if reward else 'meta no alcanzada'} en {steps} pasos")
    finally:
        evaluation.close()


if __name__ == "__main__":
    main()