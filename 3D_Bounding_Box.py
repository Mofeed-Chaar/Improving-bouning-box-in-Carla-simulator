# for testing all oop


import numpy as np
from carlasimu.carlaUtils import CarlaEnvironment
import time
import random
import queue
import argparse
import logging
import carlasimu.config as config
import cv2
import copy
from carlasimu.Manager import CarlaManager

from PIL import Image
import os
import numpy as np 
import queue

env = CarlaEnvironment()
client = env.client 
world = env.world
carla = env.carla
manager = CarlaManager(env)
cam = None
vehicles_list=[]
weather = None
nonvehicles_list= []

world = env.world
client = env.client
carla = env.carla
vehicle = manager.vehicles()
walker = manager.walkers()

bbtools = manager.BoundingBox()

def make_dir(dir_paths : list): # make dircets for all the pathes in the list
    for path in dir_paths:
        if not os.path.isdir(path):
            os.makedirs(path)




def build_projection_matrix(w, h, fov):
    focal = w / (2.0 * np.tan(fov * np.pi / 360.0))
    K = np.identity(3)
    K[0, 0] = K[1, 1] = focal
    K[0, 2] = w / 2.0
    K[1, 2] = h / 2.0
    return K

def get_image_point(loc, K, w2c):
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


vehicles_list = vehicle.set_vehicles(same_number=True)
print(f'the number of vehicles {len(vehicles_list)}')
    
walkers = walker.set_walkers(same_number=True,activate_actors=True)
ego = vehicle.get_ego()


camera_bp, cam_transform = manager.sensors().set_rgb_camera()
camera = world.spawn_actor(camera_bp, cam_transform, attach_to=ego)

# Spawn the depth sensor at the same location as the camera
image_queue = queue.Queue()

camera.listen(image_queue.put)
nonvehicles_list.append(camera)

# Image segmentation camera
seg_bp, seg_transform =  manager.sensors().set_seg_camera()
segmentation = world.spawn_actor(seg_bp, seg_transform, attach_to=ego)
seg_queue = queue.Queue()
segmentation.listen(seg_queue.put)
nonvehicles_list.append(segmentation)

print('Segmentation sensor is ready')


world_2_camera = np.array(camera.get_transform().get_inverse_matrix())
image_w = camera_bp.get_attribute("image_size_x").as_int()
image_h = camera_bp.get_attribute("image_size_y").as_int()
fov = camera_bp.get_attribute("fov").as_float()
K = build_projection_matrix(image_w, image_h, fov)



edges = [[0,1], [1,3], [3,2], [2,0], [0,4], [4,5], [5,1], [5,7], [7,6], [6,4], [6,2], [7,3]]

# Filter the list to extract bounding boxes within a 50m radius


world.tick()
image = image_queue.get()
file_name = '%08d.png' % image.frame
print(file_name)
img = np.reshape(np.copy(image.raw_data), (image.height, image.width, 4)) 
# Display the image in an OpenCV display window
cv2.namedWindow('ImageWindowName', cv2.WINDOW_AUTOSIZE)
cv2.imshow('ImageWindowName',img)
cv2.waitKey(1)
dir_paths={'img_3d':os.path.join('samples','img'),'img_2d':os.path.join('samples','img_2d'),'labels':os.path.join('samples','label'),
            'img_3d_filtered':os.path.join('samples','img_3d_filtered'),'img_2d_filtered':os.path.join('samples','img_2d_filtered')}

make_dir(list(dir_paths.values()))
try:
    while True:
        # Get the camera sensor data

        world.tick()
        image = image_queue.get()
        image_seg = seg_queue.get()
        image_seg.convert(carla.ColorConverter.CityScapesPalette) #carla.ColorConverter.Raw
        img_seg = np.reshape(np.copy(image_seg.raw_data), (image_seg.height, image_seg.width, 4)) 
        file_name = '%08d.png' % image.frame
        label_name = '%08d.txt' % image.frame

        img = np.reshape(np.copy(image.raw_data), (image.height, image.width, 4)) 
        img_2d = copy.deepcopy(img)
        img_filtered_3d = copy.deepcopy(img)
        img_filtered_2d = copy.deepcopy(img)

        # Display the image in an OpenCV display window
        world_2_camera = np.array(camera.get_transform().get_inverse_matrix())
        data_box = []


        for npc in world.get_actors().filter('*vehicle*'):

        #     Filter out the ego vehicle
            if npc.id != ego.id:
                actor_classification =bbtools.get_actor_classification(npc.type_id)
                bb = npc.bounding_box
                dist = npc.get_transform().location.distance(ego.get_transform().location)
                      # Filter for the vehicles within 50m
                if dist < 100:
 
                      # Calculate the dot product between the forward vector
                # of the vehicle and the vector between the vehicle
                # and the other vehicle. We threshold this dot product
                # to limit to drawing bounding boxes IN FRONT OF THE CAMERA
                    box_color = bbtools.get_color_seg(npc.type_id)
                    box_color = tuple(box_color)
                    forward_vec = ego.get_transform().get_forward_vector()
                    ray = npc.get_transform().location - ego.get_transform().location
                    if forward_vec.dot(ray) > 1:
                        p1 = get_image_point(bb.location, K, world_2_camera)
                        verts = [v for v in bb.get_world_vertices(npc.get_transform())]
                        for edge in edges:
                            p1 = get_image_point(verts[edge[0]], K, world_2_camera)
                            p2 = get_image_point(verts[edge[1]],  K, world_2_camera)
        
                            cv2.line(img, (int(p1[0]),int(p1[1])), (int(p2[0]),int(p2[1])), box_color, 2)
                        x_max = -10000
                        x_min = 10000
                        y_max = -10000
                        y_min = 10000

                        for vert in verts:
                            p = get_image_point(vert, K, world_2_camera)
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
                        
                        cv2.rectangle(img_2d, (int(x_max),int(y_max)), (int(x_min),int(y_min)), box_color, 2)
                        box = {'actor':npc,'box':[x_min,y_min,x_max,y_max],'classification' : actor_classification,'dist':dist}
                        data_box.append(box)

                        # here for filter boxes----------------------------------------
                        x_min,y_min,x_max,y_max = bbtools.box_corrcttion([x_min,y_min,x_max,y_max])

                        if x_min==x_max:
                                continue
                        box['box'] = [x_min,y_min,x_max,y_max]

                        if not (bbtools.filter_box(box=box['box'],actor = npc, img_seg=img_seg)):
                                continue
                        cv2.rectangle(img_filtered_2d, (int(x_max),int(y_max)), (int(x_min),int(y_min)), box_color, 2)
                        for edge in edges:
                            p1 = get_image_point(verts[edge[0]], K, world_2_camera)
                            p2 = get_image_point(verts[edge[1]],  K, world_2_camera)
        
                            cv2.line(img_filtered_3d, (int(p1[0]),int(p1[1])), (int(p2[0]),int(p2[1])), box_color, 2)


                        
                        








        with open(os.path.join(dir_paths['labels'],label_name),'w') as f:
            for actor_box in data_box:
                box = actor_box['box']
 
                f.write(str((box[0]+box[2])/2) + ' ' + str((box[1]+box[3])/2) + ' ' + str(box[2]-box[0]) + ' ' + str(box[3] - box[1]) + '\n')


        # Now draw the image into the OpenCV display window
        cv2.imshow('ImageWindowName',img)
        cv2.imwrite(os.path.join(dir_paths['img_3d'],file_name), img[:,:,:3])
        cv2.imwrite(os.path.join(dir_paths['img_2d'],file_name), img_2d[:,:,:3])
        cv2.imwrite(os.path.join(dir_paths['img_3d_filtered'],file_name), img_filtered_3d[:,:,:3])
        cv2.imwrite(os.path.join(dir_paths['img_2d_filtered'],file_name), img_filtered_2d[:,:,:3])
        # Break the loop if the user presses the Q key
        if cv2.waitKey(1) == ord('q'):
            break
    
# Close the OpenCV display window when the game loop stops
 
finally:
   
    env.close_env(vehicles_list=vehicles_list,walkers=walkers,nonvehicles_list=nonvehicles_list)
    #camera.destroy()
    #vehicle.destroy()
    cv2.destroyAllWindows()
    

