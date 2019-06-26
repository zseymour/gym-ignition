# Copyright (C) 2019 Istituto Italiano di Tecnologia (IIT). All rights reserved.
# This software may be modified and distributed under the terms of the
# GNU Lesser General Public License v2.1 or any later version.

import gym
import gym_ignition
from gym_ignition.utils import logger
from gym_ignition.utils.typing import *


class CartPoleContinuous(gym_ignition.Task):
    def __init__(self, robot: gym_ignition.Robot, reward_cart_at_center: bool = None) -> None:
        super().__init__(robot=robot)

        # Private attributes
        self._steps_beyond_done = None
        self._reward_cart_at_center = reward_cart_at_center

        # Configure action space
        max_force = 50
        self.action_space = gym.spaces.Box(np.array([-max_force]),
                                           np.array([max_force]),
                                           dtype=np.float32)

        # Variables limits
        self._x_threshold = 2.5
        self._x_threshold_reset = 2.4

        # Configure observation limits
        high = np.array([
            self._x_threshold,        # x
            np.finfo(np.float32).max, # x_dot
            np.finfo(np.float32).max, # theta
            np.finfo(np.float32).max  # theta_dot
        ])

        # Configure the observation space
        self.observation_space = gym.spaces.Box(-high, high, dtype=np.float32)

        # Seed the environment
        self.seed()

    def _set_action(self, action: Action) -> bool:
        assert self.action_space.contains(action), \
            "%r (%s) invalid" % (action, type(action))

        # Get the robot object
        robot = self.robot

        # Read the action and send the force to the cart
        force = action.tolist()[0]
        ok = robot.set_joint_force("linear", force)

        if not ok:
            raise Exception("Failed to set the force to the cart")

        return True

    def _get_observation(self) -> Observation:
        # Get the robot object
        robot = self.robot

        # Get the new joint positions
        x = robot.joint_position("linear")
        theta = np.rad2deg(robot.joint_position("pivot"))

        # Get the new joint velocities
        x_dot = robot.joint_velocity("linear")
        theta_dot = np.rad2deg(robot.joint_velocity("pivot"))

        # Create the observation object
        observation = Observation(np.array([x, x_dot, theta, theta_dot]))

        # Validate the observation
        assert self.observation_space.contains(observation), \
            "%r (%s) invalid" % (observation, type(observation))

        # Return the observation
        return observation

    def _get_reward(self) -> Reward:
        # Initialize the reward
        reward = None

        # Calculate the reward
        if not self._is_done():
            reward = 1.0
        else:
            if self._steps_beyond_done is None:
                # Pole just fell
                self._steps_beyond_done = 0
                reward = 1.0
            else:
                self._steps_beyond_done += 1
                reward = 0.0

                # Warn the user to call reset
                if self._steps_beyond_done == 1:
                    logger.warn("You are calling 'step()' even though this environment "
                                "has already returned done = True. You should always "
                                "call 'reset()' once you receive 'done = True' -- any "
                                "further steps are undefined behavior.")

        if self._reward_cart_at_center:
            # Get the observation
            observation = self._get_observation()
            x = observation[0]
            x_dot = observation[1]

            reward = reward \
                - 0.10 * np.abs(x) \
                - 0.10 * np.abs(x_dot) \
                - 10.0 * (x >= self._x_threshold_reset)

        return reward

    def _is_done(self) -> bool:
        # Get the observation
        observation = self._get_observation()

        # Get x and theta
        x = observation[0]

        # Calculate if the environment reached its termination
        done = np.abs(x) >= self._x_threshold_reset

        return done

    def _reset(self) -> bool:
        new_state = self._np_random.uniform(low=-0.05, high=0.05, size=(4,))
        new_state[2] += np.pi

        ok1 = self.robot.reset_joint("linear", new_state[0], new_state[1])
        ok2 = self.robot.reset_joint("pivot", new_state[2], new_state[3])

        if not (ok1 and ok2):
            raise Exception("Failed to reset robot state")

        # Reset the flag that assures reset is properly called
        self._steps_beyond_done = None

        return ok1 and ok2