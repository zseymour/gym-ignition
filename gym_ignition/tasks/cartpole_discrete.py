# Copyright (C) 2019 Istituto Italiano di Tecnologia (IIT). All rights reserved.
# This software may be modified and distributed under the terms of the
# GNU Lesser General Public License v2.1 or any later version.

import abc
import gym
import numpy as np
from typing import Tuple
from gym_ignition.base import task
from gym_ignition.utils import logger
from gym_ignition.utils.typing import Action, Reward, Observation
from gym_ignition.utils.typing import ActionSpace, ObservationSpace
from gym_ignition.base.robot import robot_abc, feature_detector, robot_joints


@feature_detector
class RobotFeatures(robot_abc.RobotABC,
                    robot_joints.RobotJoints,
                    abc.ABC):
    pass


class CartPoleDiscrete(task.Task, abc.ABC):

    def __init__(self, reward_cart_at_center: bool = False) -> None:
        super().__init__()

        # Store the requested robot features for this task
        self.robot_features = RobotFeatures

        # Private attributes
        self._force_mag = 20.0
        self._steps_beyond_done = None
        self._reward_cart_at_center = reward_cart_at_center

        # Variables limits
        self._x_threshold = 2.4
        self._theta_threshold_radians = np.deg2rad(12)

        # Create the spaces
        self.action_space, self.observation_space = self.create_spaces()

        # Seed the environment
        self.seed()

    def create_spaces(self) -> Tuple[ActionSpace, ObservationSpace]:
        # Configure action space
        action_space = gym.spaces.Discrete(2)

        # Configure observation limits
        high = np.array([
            self._x_threshold * 2,                          # x
            np.finfo(np.float32).max,                       # x_dot
            np.rad2deg(self._theta_threshold_radians * 2),  # theta
            np.finfo(np.float32).max                        # theta_dot
        ])

        # Configure the observation space
        observation_space = gym.spaces.Box(-high, high, dtype=np.float32)

        return action_space, observation_space

    def set_action(self, action: Action) -> bool:
        assert self.action_space.contains(action), \
            "%r (%s) invalid" % (action, type(action))

        # Get the robot object
        robot = self.robot

        # Read the action and send the force to the cart
        force = self._force_mag if action == 1 else -self._force_mag
        ok = robot.set_joint_force("linear", force)

        if not ok:
            raise Exception("Failed to set the force to the cart")

        return True

    def get_observation(self) -> Observation:
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

        # Return the observation
        return observation

    def get_reward(self) -> Reward:
        # Calculate the reward
        if not self.is_done():
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
            observation = self.get_observation()
            x = observation[0]
            x_dot = observation[1]

            # Update the reward
            reward = reward \
                - np.abs(x) \
                - np.abs(x_dot) \
                - 10 * (x >= self._x_threshold)

        return reward

    def is_done(self) -> bool:
        # Get the observation
        observation = self.get_observation()

        # Get x and theta
        x = observation[0]
        theta = observation[2]

        # Calculate if the environment reached its termination
        done = \
            np.abs(x) > self._x_threshold or \
            np.abs(theta) > np.rad2deg(self._theta_threshold_radians)

        return done

    def reset_task(self) -> bool:
        # Initialize the environment with a new random state using the random number
        # generator provided by the Task.
        new_state = self.np_random.uniform(low=-0.05, high=0.05, size=(4,))
        new_state[2] = self.np_random.uniform(low=-np.deg2rad(10),
                                              high=np.deg2rad(10))

        # Set the joints in torque control mode
        for joint in {"linear", "pivot"}:
            desired_control_mode = robot_joints.JointControlMode.TORQUE

            # TODO: temporary workaround for robot implementation without this method,
            #       e.g. FactoryRobot, which does not need to call it at the moment.
            try:
                if self.robot.joint_control_mode(joint) != desired_control_mode:
                    ok_mode = self.robot.set_joint_control_mode(joint,
                                                                desired_control_mode)
                    assert ok_mode, f"Failed to set control mode for joint '{joint}'"
            except Exception:
                logger.warn("This runtime does not support setting the control mode")
                pass

        # Reset position and velocity
        ok1 = self.robot.reset_joint("linear", new_state[0], new_state[1])
        ok2 = self.robot.reset_joint("pivot", new_state[2], new_state[3])

        # Reset the flag that assures reset is properly called
        self._steps_beyond_done = None

        return ok1 and ok2
