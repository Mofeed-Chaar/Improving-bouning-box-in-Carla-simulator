
from .config import config




class sensors(object):
	def __init__(self,env):
		self.env = env
		self.sensors_param = config('sensors.yaml')

	def __set_sensor(self,attributes,sensor_name):

		transform = self.env.carla.Transform(self.env.carla.Location(x=attributes['location'][0], 
																			z=attributes['location'][1])) 
		bp = self.env.world.get_blueprint_library().find(sensor_name)
		items = list(attributes.items())
		for i in range(len(items)-1): # -1 because the last item about lcaction not attribute
			attribute , value = items[i]
			if value is None:
				continue
			bp.set_attribute(attribute, str(value))

		return bp,transform

	def set_rgb_camera(self,attributes=None):
		# attributes is dic (attribute:value of the attribute)
		if attributes is None:
			attributes = self.sensors_param.rgb_camera
		cam_bp,cam_transform = self.__set_sensor(attributes=attributes,sensor_name='sensor.camera.rgb')
		return cam_bp,cam_transform


	def set_seg_camera(self,attributes=None):
		if attributes is None:
			attributes = self.sensors_param.semantic_segmentation_camera
		sig_bp, sig_transform = self.__set_sensor(attributes=attributes,sensor_name='sensor.camera.semantic_segmentation')
		return sig_bp, sig_transform




	def radar_sensor(self,attributes=None):
		if attributes is None:
			attributes = self.sensors_param.radar_sensor
		radar_bp, radar_transform = self.__set_sensor(attributes=attributes,sensor_name='sensor.other.radar')
		return radar_bp, radar_transform


	def lidar_sensor(self,attributes=None):
		if attributes is None:
			attributes = self.sensors_param.lidar_sensor
		lidar_bp, lidar_transform = self.__set_sensor(attributes=attributes,sensor_name='sensor.lidar.ray_cast')
		return lidar_bp, lidar_transform

	def depth_sensor(self,attributes=None):
		if attributes is None:
			attributes = self.sensors_param.depth_camera
		depth_bp, depth_transform = self.__set_sensor(attributes=attributes,sensor_name='sensor.camera.depth')
		return depth_bp, depth_transform



		




