from .Actors import vehicles
from .exceptions import NoSensorsInstalled
from . import config
import matplotlib.pyplot as plt
import json
import numpy as np
import time
from PIL import Image
import copy
import cv2
import os
import copy
class BoundingBox(object):
	def __init__(self,env):
		self.bboxParameter = config.config('boundingBox.yaml')
		self.sensors_param = config.config('sensors.yaml')
		self.seg_color = config.config('color_segmentation.yaml')
		self.env = env
		self.img = None

		self.start_time = int(time.time()%60)
		self.time_tick= self.bboxParameter.time_screen_shot
		self.img_w = self.sensors_param.rgb_camera['image_size_x']
		self.img_h = self.sensors_param.rgb_camera['image_size_y']
		self.area_image = self.img_w * self.img_h
		self.label_classes_name = {'car':0,'bus':1,'truck':2,'van':3,'walker':4,'street_light':5}
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


	def calucate_visible_object(self,box1,box2,visibility_threshold=0.95):
			# this function to check if the box1 is inside of the box2
			# the box is corner [x1,y1,x2,y2] where The top-left corner (x1, y1) and The bottom-right corner (x2, y2)

		hidden_visibility = 0.0
		x1 = max(box1[0], box2[0])
		y1 = max(box1[1], box2[1])
		x2 = min(box1[2], box2[2])
		y2 = min(box1[3], box2[3])
		intersection = int(max(0,(x2 - x1)) * max(0,(y2 - y1)))
		box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
		box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
		box_area = int(min(box1_area,box2_area))
		if intersection==0:
			return True


		hidden_visibility = box_area/float(intersection)
		if hidden_visibility>=visibility_threshold:
			
			return False
		print('not hidden')
		return True


	def convert_to_pillow(self,image):
		# we use this function to convert the image to pillow when we use PIL instead of cv2

		image.convert(self.env.carla.ColorConverter.Raw)
		i = np.array(image.raw_data)
		i2 = i.reshape((image.height, image.width, 4))
		i3 = np.zeros((image.height,image.width,3))
		i3[:,:,0] = i2[:,:,2]
		i3[:,:,1] = i2[:,:,1]
		i3[:,:,2] = i2[:,:,0]
		i3 = np.uint8(i3)
		pil_img = Image.fromarray(i3, 'RGB')
		return pil_img

	def retrieve_data(self,sensor_queue, frame, timeout=5):
	    while True:
	        try:
	            data = sensor_queue.get(True,timeout)
	        except queue.Empty:
	            return None
	        if data.frame == frame:
	            return data

	def box_corrcttion(self,box):
		x_min,y_min,x_max,y_max = box
		img_w = self.sensors_param.rgb_camera['image_size_x']
		img_h = self.sensors_param.rgb_camera['image_size_y']

		if x_min>=img_w:
			return [0,0,0,0]
		if x_min<0:
			x_min=0


		if y_min>img_h:
			return [0,0,0,0]
		if y_min<0:
			y_min=0


		if x_max>img_w:
			x_max=img_w
		if x_max<0:
			return [0,0,0,0]


		if y_max>img_h:
			y_max=img_h
		if y_max<0:
			return [0,0,0,0]


		if (x_min>=x_max) or (y_min>=y_max):
			return [0,0,0,0]
		box_area = (x_max - x_min) * (y_max - y_min)
		if (box_area == 0) or (box_area>= img_w*img_h):
			return [0,0,0,0]
		return [x_min,y_min,x_max,y_max]





	def filter_box(self,actor,box,img_seg):
		try:
			actor_type = actor.type_id
		except AttributeError:
			actor_type = 'street_light'
		#print(f'the velocity is {actor.get_velocity()}')
		threshold_filter = self.bboxParameter.threshold_small_box
		threshold_filter_big_box = self.bboxParameter.threshold_big_box
		actor_classification = self.get_actor_classification(actor_type)
		#print(actor_classification)
		if actor_classification is None:
			return False


		color_filter = self.seg_color.get_dic()[actor_classification]


		x_min,y_min,x_max,y_max = box
		box_area = (x_max - x_min) * (y_max - y_min)
		img = img_seg[int(y_min):int(y_max),int(x_min):int(x_max)]
		img = img[:,:,:3]
		countn_pixles = 0
		threshold_big_box = self.bboxParameter.size_big_box
			
		for i in range(img.shape[0]):
			for j in range(img.shape[1]):

				if list(img[i,j])==list(color_filter):
					countn_pixles+=1
					
		if ((countn_pixles/float(box_area))*100)<=threshold_filter:
			return False
		if ((box_area/float(self.area_image))*100)>= threshold_big_box:
			if ((countn_pixles/float(box_area))*100)<=threshold_filter_big_box:
				return False

		return True



	def filter_hidden_boxes(self,data):  
		'''
		The data has the folowing type {'actor': carla.libcarla.Vehicle object, 'box': <list> , classification: 'Class name'.....}
		in the <list> each element is dictionary has tow keyes {'actor': <object of the actor>, 'box':[x_min,y_min,x_max,y_max]}
		img_seg : image segmentation 
		threshold_walkers (percent): the percent of visibility of the walker, if it is more than threshold, the box will be deleted
		threshold_vehickles (percent) : the percent of visibility of the vehicle, if it is more than threshold, the box will be deleted
		return:
		data after the filter
		'''
		delete_boxes = []
		
		# Filter the vehicles
		if data is not None:
			for n,actor in enumerate(data):
				box = actor['box']
				if n == len(data)-1:
					break
				for i in range(n+1,len(data)):
					#print(f'i is {i}')
					second_box = data[i]['box']
					if not (self.calucate_visible_object(box,second_box)): # the object is hidden
						box1_area = (box[2] - box[0]) * (box[3] - box[1])
						box2_area = (second_box[2] - second_box[0]) * (second_box[3] - second_box[1])
						if box1_area<box2_area:
							if not (n in delete_boxes):
								delete_boxes.append(n)
							
						else:
							if not (i in delete_boxes):
								delete_boxes.append(i)
		if len(delete_boxes)==0:
			return data
		for i in delete_boxes:
			del data[i]

		return data



	def get_actor_classification(self,actor_type):
		vehicles_name_dic = self.env.vehicles_name.get_dic()
		#print(actor_type)
		for key in vehicles_name_dic.keys():
			if actor_type in vehicles_name_dic[key]:
				return key
		if 'walker' in actor_type:
			return 'walker'
		if 'street_light' in actor_type:
			return 'street_light'

		return None

	def get_color_seg(self,actor_type):
		'''
		return corlor rgb as a set
		'''
		
		actor_classification= self.get_actor_classification(actor_type)
		color = self.seg_color.get_dic()[actor_classification]
		return color 

	def save_labels(self,data,path):
		json_data = {'class':[],'box':[],}
		with open(path, "w") as f:
			for d in data:
				class_name = d['classification']
				f.write(str(self.label_classes_name[class_name] ) + ' ')
				box = d['box']
				box[0] = box[0]/float(self.img_w)
				box[2] = box[2]/float(self.img_w)
				box[1] = box[1]/float(self.img_h)
				box[3] = box[3]/float(self.img_h)
				f.write(str((box[0]+box[2])/2) + ' ' + str((box[1]+box[3])/2) + ' ' + str(box[2]-box[0]) + ' ' + str(box[3] - box[1]) + '\n')
	def save_multi_labels(self,data,path,name):
		data_50 = []
		data_100= []
		data_150 = []
		data_200=[]


		for d in data:
			if d['dist']<=50:
				data_50.append(d)
				data_100.append(d)
				data_150.append(d)
				data_200.append(d)
				continue
			if d['dist']<=100:
				data_100.append(d)
				data_150.append(d)
				data_200.append(d)
				continue
			if d['dist']<=150:
				data_150.append(d)
				data_200.append(d)
				continue
			if d['dist']<=200:
				data_200.append(d)
		with open(os.path.join(path,'label50',name), "w") as f:
			for d in data_50:
				class_name = d['classification']
				f.write(str(self.label_classes_name[class_name] ) + ' ')
				box = copy.deepcopy(d['box'])
				box[0] = box[0]/float(self.img_w)
				box[2] = box[2]/float(self.img_w)
				box[1] = box[1]/float(self.img_h)
				box[3] = box[3]/float(self.img_h)
				f.write(str((box[0]+box[2])/2) + ' ' + str((box[1]+box[3])/2) + ' ' + str(box[2]-box[0]) + ' ' + str(box[3] - box[1]) + '\n')
		with open(os.path.join(path,'label100',name), "w") as f:
			for d in data_100:
				class_name = d['classification']
				f.write(str(self.label_classes_name[class_name] ) + ' ')
				box = copy.deepcopy(d['box'])
				box[0] = box[0]/float(self.img_w)
				box[2] = box[2]/float(self.img_w)
				box[1] = box[1]/float(self.img_h)
				box[3] = box[3]/float(self.img_h)
				f.write(str((box[0]+box[2])/2) + ' ' + str((box[1]+box[3])/2) + ' ' + str(box[2]-box[0]) + ' ' + str(box[3] - box[1]) + '\n')
		with open(os.path.join(path,'label150',name), "w") as f:
			for d in data_150:
				class_name = d['classification']
				f.write(str(self.label_classes_name[class_name] ) + ' ')
				box = copy.deepcopy(d['box'])
				box[0] = box[0]/float(self.img_w)
				box[2] = box[2]/float(self.img_w)
				box[1] = box[1]/float(self.img_h)
				box[3] = box[3]/float(self.img_h)
				f.write(str((box[0]+box[2])/2) + ' ' + str((box[1]+box[3])/2) + ' ' + str(box[2]-box[0]) + ' ' + str(box[3] - box[1]) + '\n')
		with open(os.path.join(path,'label200',name), "w") as f:
			for d in data_200:
				class_name = d['classification']
				f.write(str(self.label_classes_name[class_name] ) + ' ')
				box = copy.deepcopy(d['box'])
				box[0] = box[0]/float(self.img_w)
				box[2] = box[2]/float(self.img_w)
				box[1] = box[1]/float(self.img_h)
				box[3] = box[3]/float(self.img_h)
				f.write(str((box[0]+box[2])/2) + ' ' + str((box[1]+box[3])/2) + ' ' + str(box[2]-box[0]) + ' ' + str(box[3] - box[1]) + '\n')
		


#class BoundingBox2D( ):
	#def __init__(self,env):

		#super().__init__(env)








	

				
				



			#sensor.listen(self.camera_callback_save_file)

		#except NoSensorsInstalled