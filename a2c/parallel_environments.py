import multiprocessing
import gym
import torch

from a2c.image_utils import save
from a2c.utils import params
from multiprocessing import Process, Pipe
from a2c.environment_wrapper import EnvironmentWrapper


def worker(connection):
    env = make_environment()

    while True:
        command, data = connection.recv()
        if command == 'step':
            state, reward, done = env.step(data)
            connection.send((state, reward, done))
        elif command == 'reset':
            state = env.reset()
            connection.send(state)


def make_environment():
    env = gym.make('CarRacing-v0')
    env_wrapper = EnvironmentWrapper(env, params.stack_size)
    return env_wrapper


class ParallelEnvironments:
    def __init__(self, number_of_processes=multiprocessing.cpu_count()):
        self.number_of_processes = number_of_processes

        # pairs of connections in duplex connection
        self.parents, self.childs = zip(*[Pipe() for _
                                          in range(number_of_processes)])

        self.processes = [Process(target=worker, args=(child,), daemon=True)
                          for child in self.childs]

        for process in self.processes:
            process.start()

    def step(self, actions):
        for action, parent in zip(actions, self.parents):
            parent.send(('step', action))
        results = [parent.recv() for parent in self.parents]
        states, rewards, dones = zip(*results)
        return torch.Tensor(states), torch.Tensor(rewards), torch.Tensor(dones)

    def reset(self):
        for parent in self.parents:
            parent.send(('reset', None))
        results = [parent.recv() for parent in self.parents]
        return torch.Tensor(results)

    def get_state_shape(self):
        return (params.stack_size, 84, 84)


if __name__ == '__main__':
    env = ParallelEnvironments(number_of_processes=2)
    random_env = gym.make('CarRacing-v0')
    res = env.reset()
    for i in range(1000):
        ac = random_env.action_space.sample()
        actions = [ac, ac]
        results = env.step(actions)

        if torch.all(torch.eq(torch.Tensor(results[0][0]), torch.Tensor(results[1][0]))):
            print(i)
    # actions = [[0, 0, 0], [0, 0, 0]]
    # env.step(actions)