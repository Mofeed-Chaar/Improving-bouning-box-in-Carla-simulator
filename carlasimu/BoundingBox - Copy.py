from .Actors import vehicles
from .exceptions import NoSensorsInstalled
from . import config
import matplotlib.pyplot as plt

import numpy as np
import time
from PIL import Image
import copy
import cv2
import os
class BoundingBox(object):
	def __init__(self,env):
		self.boundingBoxParameter = config.config('BoundingBox.yaml')
		self.sensors_param = config.config('sensors.yaml')
		self.env = env
		self.img = None

		self.start_time = int(time.time()%60)
		self.time_tick= self.boundingBoxParameter.cam_rgb['time_screen_shot']
		#self.cv2 = cv2


	def IOU(self,box1, box2):
		'''
	    Calculate intersection over union (IoU) of two bounding boxes.
	
 	   	Parameters:
	    box1 (list or tuple): bounding box 1 with format [x1, y1, x2, y2]
	    box2 (list or tuple): bounding box 2 with format [x1, y1, x2, y2]
	
 	   	Returns:
	    float: iou value

		'''

    	# Determine the coordinates of the intersection rectangle
		x1 = max(box1[0], box2[0])
		y1 = max(box1[1], box2[1])
		x2 = min(box1[2], box2[2])
		y2 = min(box1[3], box2[3])
	
 	    # Compute the area of intersection rectangle
		intersection = np.max(0,(x2 - x1)) * np.max(0,(y2 - y1))
	
 	    # Compute the area of both the prediction and ground-truth rectangles
		box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
		box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
	
 	    # Compute the intersection over union by taking the intersection
	    # area and dividing it by the sum of prediction + ground-truth
	    # areas - the intersection area
		iou = intersection / float(box1_area + box2_area - intersection)
	
 	    # return the intersection over union value
		return iou

	def build_projection_matrix(self, w, h, fov): 
	    focal = w / (2.0 * np.tan(fov * np.pi / 360.0))
	    K = np.identity(3)
	    K[0, 0] = K[1, 1] = focal
	    K[0, 2] = w / 2.0
	    K[1, 2] = h / 2.0
	    return K
	

	def get_image_point(self,loc, K, w2c):
		# Calculate 2D projection of 3D coordinate
		# Format the input coordinate (loc is a carla.Position object)
		point = np.array([loc.x, loc.y, loc.z, 1])
		# transform to camera coordinates
		point_camera = np.dot(w2c, point)
		# New we must change from UE4's coordinate system to an "standard"
		# (x, y ,z) -> (y, -z, x)
		# and we remove the fourth componebonent also
		point_camera = [point_camera[1], -point_camera[2], point_camera[0]]
		# now project 3D->2D using the camera matrix
		point_img = np.dot(K, point_camera)
		# normalize
		point_img[0] /= point_img[2]
		point_img[1] /= point_img[2]
		return point_img[0:2]


	def calucate_visible_object(self,box1,box2,visibility_threshold=1.0):
			# this function to check if the box1 is inside of the box2
			# the box is corner [x1,y1,x2,y2] where The top-left corner (x1, y1) and The bottom-right corner (x2, y2)
		x1 = max(box1[0], box2[0])
		y1 = max(box1[1], box2[1])
		x2 = min(box1[2], box2[2])
		y2 = min(box1[3], box2[3])
		intersection = np.max(0,(x2 - x1)) * np.max(0,(y2 - y1))
		box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
		if intersection==0:
			return True
		hidden_visibility = box1_area/float(intersection)
		if hidden_visibility>visibility_threshold:
			return False
		return True



	def camera_callback_save_file(self,image):
		'''for cam
	    i = np.array(image.raw_data)
	    i2 = i.reshape((image.height, image.width, 4))
	    i3 = i2[:, :, :3]
	    img = Image.fromarray(i3, 'RGB')
	    img.save('_out/%08d.png' % image.frame)
	    '''
		    #for 
		time_end = int(time.time()%60)
		#self.env.world.tick()
		if (time_end - self.start_time)>=self.time_tick:
			print('i am cam')
			self.start_time = time_end
			
			world_2_camera = np.array(self.cam.get_transform().get_inverse_matrix())
			img = np.reshape(np.copy(image.raw_data), (image.height, image.width, 4))
			image.convert(self.env.carla.ColorConverter.Raw)
			i = np.array(image.raw_data)
			i2 = i.reshape((image.height, image.width, 4))
			i3 = np.zeros((image.height,image.width,3))
			i3[:,:,0] = i2[:,:,2]
			i3[:,:,1] = i2[:,:,1]
			i3[:,:,2] = i2[:,:,0]
			i3 = np.uint8(i3)

			pil_img = Image.fromarray(i3, 'RGB')
			#self.env.world.tick()
			print('check4')




			if self.boundingBoxParameter.cam_rgb['actors']['vehicles']:  # if you want to put bounding box on the vehicles
				vehicles=(self.env.world.get_actors().filter(self.env.args.filterv))
				print('check1')
				for npc in vehicles:
					if npc.id != self.ego.id:
						bb = npc.bounding_box
						dist = npc.get_transform().location.distance(self.ego.get_transform().location)
						if dist <= self.boundingBoxParameter.cam_rgb['max_distance']: # Filter for the vehicles within specific distance(to update look into boundingBox.yaml file the parameter max_distance )
							forward_vec = self.ego.get_transform().get_forward_vector()
							ray = npc.get_transform().location - self.ego.get_transform().location
							if forward_vec.dot(ray) > self.boundingBoxParameter.cam_rgb['min_distance']:
								p1 = self.get_image_point(bb.location, self.K, world_2_camera)
								verts = [v for v in bb.get_world_vertices(npc.get_transform())]
								x_max = -10000
								x_min = 10000
								y_max = -10000
								y_min = 10000
								box = None
								for vert in verts:
									p = self.get_image_point(vert, self.K, world_2_camera)
									# Find the rightmost vertex
									if p[0] > x_max:
										x_max = p[0]
									# Find the leftmost vertex
									if p[0] < x_min:
										x_min = p[0]
									# Find the highest vertex
									if p[1] > y_max:
										y_max = p[1]
									# Find the lowest  vertex
									if p[1] < y_min:
										y_min = p[1]
									box = (int(x_min),int(y_min),int(x_max),int(y_max))  # corner box
								
								#cv2.line(img, (int(x_min),int(y_min)), (int(x_max),int(y_min)), (0,0,255, 255), 1)
								#cv2.line(img, (int(x_min),int(y_max)), (int(x_max),int(y_max)), (0,0,255, 255), 1)
								#cv2.line(img, (int(x_min),int(y_min)), (int(x_min),int(y_max)), (0,0,255, 255), 1)
								#cv2.line(img, (int(x_max),int(y_min)), (int(x_max),int(y_max)), (0,0,255, 255), 1)
								print(box)
								print(npc.type_id)

								#self.waitKey(1)
			
			#plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
			print('check2')
			file_name = '%08d.png' % image.frame
			path = os.path.join(self.save_dir,file_name)
			print(path)
			pil_img.save(path)
			print('check3')
			#cv2.imwrite(path, img)
			#cv2.namedWindow('ImageWindowName', cv2.WINDOW_AUTOSIZE)
			#cv2.imshow('ImageWindowName',img)
			#cv2.waitKey(1)
			#img=None
			#cv2.destroyAllWindows()
			#plt.show()								
				





			if self.boundingBoxParameter.cam_rgb['actors']['walkers']:
				pass


			


	def camera_callback_imgshow(self,image):
		'''for cam
	    i = np.array(image.raw_data)
	    i2 = i.reshape((image.height, image.width, 4))
	    i3 = i2[:, :, :3]
	    img = Image.fromarray(i3, 'RGB')
	    img.save('_out/%08d.png' % image.frame)
	    '''
	    #for 
		#self.env.world.tick()



		img = np.reshape(np.copy(image.raw_data), (image.height, image.width, 4))
		#self.img = self.img[:,:,:3]
		print('check 1')
		#self.cv2.namedWindow('ImageWindowName', cv2.WINDOW_AUTOSIZE)
		
		#print(self.img.shape)
		if img is not None:
			print(img.shape)
			print('check4')

			cv2.imshow('ImageWindowName',img)
			cv2.waitKey(1)
			print('check 3')
			print('check 2')
		
		
				
					
		
		
		
		if (cv2.waitKey(1) == ord('q')):
			cv2.destroyAllWindows()

	

		 

		#if self.cv2 is not None: # if it is none that mean the figure_in_window is boundingBox.yaml is false
			#pass
			# Display the image in an OpenCV display window
		
		

		
		#for detection in image:
			#print(detection)
	
		#image.save_to_disk(image,'_out/%06d.png' % image.frame, carla.ColorConverter.CityScapesPalette)
	
		#image.save_to_disk('_out/%06d.png' % image.frame, carla.ColorConverter.CityScapesPalette)
	



class BoundingBox2D(BoundingBox):
	def __init__(self,env):

		super().__init__(env)



	def camera_bbox_actors(self,camera_bp=None, ego=None, save_image_time=1):
		if camera_bp is None:
			raise NoSensorsInstalled

		#self.env.world.tick()


		if ego is None:
			print('there is no ego vehicle')
			return None

		self.ego = ego

		cam_transform = self.env.carla.Transform(self.env.carla.Location(x=self.sensors_param.rgb_camera['location'][0], 
																			z=self.sensors_param.rgb_camera['location'][1])) 

		self.cam = self.env.world.spawn_actor(camera_bp, cam_transform, attach_to=self.ego)

		print('RGB camera is ready to calucate 2D bounding Box')
		self.save_dir = self.boundingBoxParameter.cam_rgb['save_dir']
		if not os.path.isdir(self.save_dir):
			os.makedirs(self.save_dir)
		
		self.image_w = camera_bp.get_attribute("image_size_x").as_int()
		self.image_h = camera_bp.get_attribute("image_size_y").as_int()
		self.fov = camera_bp.get_attribute("fov").as_float()
		self.K = self.build_projection_matrix(self.image_w, self.image_h, self.fov)
		#self.cv2.namedWindow('ImageWindowName', self.cv2.WINDOW_AUTOSIZE)
		

		self.cam.listen(self.camera_callback_save_file)
				

				

				
				



			#sensor.listen(self.camera_callback_save_file)

		#except NoSensorsInstalled