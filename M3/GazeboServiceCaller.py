import roslib
import rospy
import rospkg
from std_srvs.srv import Empty
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import GetModelState, SetModelState
import numpy as np


class GazeboServiceCaller:
    def __init__(self, model_name="PenguinPi"):
        """
        Args:
            model_name (str, optional): Name of model you want to call services for. Defaults to "PenguinPi".
        """
        self.model_name = model_name

    def reset_world(self):
        """Reset Gazebo world
        WARNING: This resets the map and models too
        """
        rospy.ServiceProxy("/gazebo/reset_world", Empty)

    def return_model_state(self, entity=None):
        """Call get_model_state service to get latest state from Gazebo
        Args:
            model (string): Name of model
            entity (string, optional): Name of entity i.e. link/joint.
                                        Defaults to None.
        """
        gms = rospy.ServiceProxy("/gazebo/get_model_state", GetModelState)
        result = gms(self.model_name, entity)
        position = result.pose.position
        position = [position.x, position.y, position.z]
        orientation_q = result.pose.orientation
        orientation = [orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w]
        return position, orientation

    def set_model(self, position, orientation, entity=None):
        """Set model to specific position and orientation
        Args:
            position (3x1 List): [x,y,z] coordinates
            orientation (3x1): rotation about [x,y,z] axes (roll, pitch, yaw)
            entity (String, optional): Name of entity i.e. link/joint. Defaults to None.
        """
        rospy.init_node("set_pose")
        state_msg = ModelState()
        state_msg.model_name = self.model_name
        state_msg.pose.position.x = position[0]
        state_msg.pose.position.y = position[1]
        state_msg.pose.position.z = position[2]

        roll = orientation[0]
        pitch = orientation[1]
        yaw = orientation[2]
        state_msg.pose.orientation.x = np.sin(roll / 2) * np.cos(pitch / 2) * np.cos(
            yaw / 2
        ) - np.cos(roll / 2) * np.sin(pitch / 2) * np.sin(yaw / 2)
        state_msg.pose.orientation.y = np.cos(roll / 2) * np.sin(pitch / 2) * np.cos(
            yaw / 2
        ) + np.sin(roll / 2) * np.cos(pitch / 2) * np.sin(yaw / 2)
        state_msg.pose.orientation.z = np.cos(roll / 2) * np.cos(pitch / 2) * np.sin(
            yaw / 2
        ) - np.sin(roll / 2) * np.sin(pitch / 2) * np.cos(yaw / 2)
        state_msg.pose.orientation.w = np.cos(roll / 2) * np.cos(pitch / 2) * np.cos(
            yaw / 2
        ) + np.sin(roll / 2) * np.sin(pitch / 2) * np.sin(yaw / 2)
        try:
            set_state = rospy.ServiceProxy("/gazebo/set_model_state", SetModelState)
            set_state(state_msg)
        except rospy.ServiceException:
            print(f"Service call failed")
