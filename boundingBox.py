from carlasimu.carlaUtils import CarlaEnvironment
from carlasimu.Manager import CarlaManager
from tqdm import tqdm
import open3d as o3d
import numpy as np
import pandas as pd
import time
import random
import queue
import argparse
import logging
import carlasimu.config as config
import cv2
import os
import copy
from PIL import Image
import os
import numpy as np 
import queue
import json
import time



map_name = 'Town10HD_Opt'
env = CarlaEnvironment(maps = map_name)
client = env.client 
world = env.world
carla = env.carla
manager = CarlaManager(env)
cc_depth_log= None
world = env.world
client = env.client
carla = env.carla
weather=manager.weather()
weather.set_weather()

queue_list = []
nonvehicles_list= []
sensor_id=0
vehicle = manager.vehicles()
walker = manager.walkers()
bbtools = manager.BoundingBox()
point_cloud = o3d.t.geometry.PointCloud()
readme_file = {}
readme_file['classes'] = bbtools.label_classes_name
readme_file['box'] = '[x_center,y_center,width,hight]'
readme_file['weather'] = str(env.world.get_weather())
readme_file['img_size'] = {'width': bbtools.img_w,'hight': bbtools.img_h}
readme_file['distance'] = {'max_distance': [50,100,150,200],'min_distance': bbtools.bboxParameter.cam_rgb['min_distance']}
readme_file['map'] = map_name
readme_file['number_of_vehicles'] = env.args.number_of_vehicles
readme_file['number_of_walkers'] = env.args.number_of_walkers
if bbtools.bboxParameter.radar_sensor['save_to_file']:
    readme_file['radar'] = 'the point cloud of the radar is [positions:(altitude,azimuth,depth), velocity]'

vehicles_name_carla = env.vehicles_name

number_img = int(bbtools.bboxParameter.cam_rgb['num_image'])

def make_dir(dir_paths : list): # make dircets for all the pathes in the list
    for path in dir_paths:
        if not os.path.isdir(path):
            os.makedirs(path)

    
    


vehicles_list = vehicle.set_vehicles(same_number=True)
bp_lib = world.get_blueprint_library()


walkers = walker.set_walkers(same_number=True,activate_actors=True)
ego = vehicle.get_ego()

# RGB Camera
camera_bp, cam_transform = manager.sensors().set_rgb_camera()
camera = world.spawn_actor(camera_bp, cam_transform, attach_to=ego)
image_queue = queue.Queue()
camera.listen(image_queue.put)
nonvehicles_list.append(camera)
queue_list.append(image_queue)
cam_id = sensor_id
sensor_id +=1
path_rgb = bbtools.bboxParameter.cam_rgb['save_dir']

print('Camera is ready')

# Radar sensor
radar_id=None
if bbtools.bboxParameter.radar_sensor['save_to_file'] or bbtools.bboxParameter.radar_sensor['figure_in_window']:
    radar_bp, radar_transform = manager.sensors().radar_sensor()
    radar = world.spawn_actor(radar_bp, radar_transform, attach_to=ego)
    radar_queue = queue.Queue()
    radar.listen(radar_queue.put)
    nonvehicles_list.append(radar)
    queue_list.append(radar_queue)
    radar_id = sensor_id
    sensor_id +=1
    print('Radar is ready')

lidar_id=None
if bbtools.bboxParameter.lidar_sensor['save_to_file'] or bbtools.bboxParameter.lidar_sensor['figure_in_window']:
    lidar_bp, lidar_transform = manager.sensors().lidar_sensor()
    lidar = world.spawn_actor(lidar_bp, lidar_transform, attach_to=ego)
    lidar_queue = queue.Queue()
    lidar.listen(lidar_queue.put)
    nonvehicles_list.append(lidar)
    queue_list.append(lidar_queue)
    lidar_id = sensor_id
    sensor_id +=1
    print('lidar is ready')

depth_id=None
if bbtools.bboxParameter.depth_image_sensor['save_to_file'] or bbtools.bboxParameter.depth_image_sensor['figure_in_window']:
    cc_depth_log = carla.ColorConverter.LogarithmicDepth
    depth_bp, depth_transform = manager.sensors().depth_sensor()
    depth = world.spawn_actor(depth_bp, depth_transform, attach_to=ego)
    depth_queue = queue.Queue()
    depth.listen(depth_queue.put)
    nonvehicles_list.append(depth)
    queue_list.append(depth_queue)
    depth_id = sensor_id
    sensor_id +=1
    print('depth image is ready')
# Image segmentation camera
seg_bp, seg_transform =  manager.sensors().set_seg_camera()
segmentation = world.spawn_actor(seg_bp, seg_transform, attach_to=ego)
seg_queue = queue.Queue()
segmentation.listen(seg_queue.put)
nonvehicles_list.append(segmentation)
queue_list.append(seg_queue)
seg_id=sensor_id
sensor_id +=1

print('Segmentation sensor is ready')


# prarmeters
fov = camera_bp.get_attribute("fov").as_float()
image_w = camera_bp.get_attribute("image_size_x").as_int()
image_h = camera_bp.get_attribute("image_size_y").as_int()
K = bbtools.build_projection_matrix(image_w, image_h, fov)


cv2.namedWindow('ImageWindowName', cv2.WINDOW_AUTOSIZE)
cv2.waitKey(1)

time_sim = 0

settings = world.get_settings()

path_image_filter = os.path.join(path_rgb,'images_bbox_filter') 
path_image = os.path.join(path_rgb,'images') # orginal image without bounding box
path_bbox = os.path.join(path_rgb,'images_bbox') # images boxing with filter
path_label = os.path.join(path_rgb,'labels')


dir_paths = [path_image_filter,path_bbox,path_image]
if bbtools.bboxParameter.image_segmentation['save_to_file']:
    path_seg = bbtools.bboxParameter.image_segmentation['save_dir']
    dir_paths.append(path_seg)
path_radar = None
if bbtools.bboxParameter.radar_sensor['save_to_file']:
    path_radar = bbtools.bboxParameter.radar_sensor['save_dir']
    dir_paths.append(path_radar)
path_lidar = None
if bbtools.bboxParameter.lidar_sensor['save_to_file']:
    path_lidar = bbtools.bboxParameter.lidar_sensor['save_dir']
    dir_paths.append(path_lidar)

path_depth = None
if bbtools.bboxParameter.depth_image_sensor['save_to_file']:
    path_depth = bbtools.bboxParameter.depth_image_sensor['save_dir']
    dir_paths.append(path_depth)

dir_paths.append(os.path.join(path_label,'label50'))
dir_paths.append(os.path.join(path_label,'label100'))
dir_paths.append(os.path.join(path_label,'label150'))
dir_paths.append(os.path.join(path_label,'label200'))

make_dir(dir_paths)

if bbtools.bboxParameter.cam_rgb['save_to_file']:
    with open(os.path.join(path_rgb,'Readme.txt'), "w") as f:
        json.dump(readme_file,f,indent=4)

#print(client.get_available_maps())
try:
    num = 0
    pbar = tqdm(total = number_img, desc ="Data Generator progress")
 
    while num<number_img:
        
        #last_box= None  # just to test
        # Get the camera sensor data
        data_box = []
        
        
        nowFrame = world.tick()
        if time_sim >= bbtools.bboxParameter.time_screen_shot:
            time_sim=0
            num +=1
            pbar.update(1)

            data = [bbtools.retrieve_data(q,nowFrame) for q in queue_list] # collect the data from all sensors
                        
            world_2_camera = np.array(camera.get_transform().get_inverse_matrix())



            image = data[cam_id]
            image_seg = data[seg_id]
            radar_points=None
            radar_name=None
            if bbtools.bboxParameter.radar_sensor['save_to_file'] or bbtools.bboxParameter.radar_sensor['figure_in_window']:
                radar_data = data[radar_id]
                radar_name = '%08d.ply' % image.frame
                radar_points = np.frombuffer(radar_data.raw_data, dtype=np.dtype('f4'))
                radar_points = np.reshape(radar_points, (len(radar_data), 4))
                position = radar_points[:,0:3]
                velocity =[[i] for i in radar_points[:,3]]
                
                if bbtools.bboxParameter.radar_sensor['save_to_file']:
                    point_cloud.point["positions"] = o3d.core.Tensor(position)
                    point_cloud.point["velocity"] = o3d.core.Tensor(velocity)
                    o3d.t.io.write_point_cloud(os.path.join(path_radar,radar_name), point_cloud)

            if bbtools.bboxParameter.lidar_sensor['save_to_file'] or bbtools.bboxParameter.lidar_sensor['figure_in_window']:
                lidar_data = data[lidar_id]
                lidar_name = '%08d.ply' % image.frame
                if bbtools.bboxParameter.lidar_sensor['save_to_file']:
                    lidar_data.save_to_disk(os.path.join(path_lidar,lidar_name))
                    


            if bbtools.bboxParameter.depth_image_sensor['save_to_file'] or bbtools.bboxParameter.depth_image_sensor['figure_in_window']:
                depth_data = data[depth_id]
                depth_name = '%08d.png' % image.frame
                depth_data.save_to_disk(os.path.join(path_depth,depth_name), cc_depth_log)

            file_name = '%08d.png' % image.frame
            label_name = '%08d.txt' % image.frame
            image_seg.convert(carla.ColorConverter.CityScapesPalette) #carla.ColorConverter.Raw
            img = np.reshape(np.copy(image.raw_data), (image.height, image.width, 4))
            orginal_img = copy.deepcopy(img)
            if (bbtools.bboxParameter.cam_rgb['save_to_file']) or (bbtools.bboxParameter.image_segmentation['save_to_file']):
                cv2.imwrite(os.path.join(path_image,file_name), orginal_img[:,:,:3])


            
            img_seg = np.reshape(np.copy(image_seg.raw_data), (image_seg.height, image_seg.width, 4)) 

            pedestrains=[*world.get_actors().filter(env.args.filterw)]
            actors = [*world.get_actors().filter('vehicle.*')]
            actors.extend(pedestrains)
            bounding_box_set= world.get_level_bbs(carla.CityObjectLabel.TrafficLight)
            if bbtools.bboxParameter.cam_rgb['save_to_file']:
                img2 = copy.deepcopy(img)
                for bb in bounding_box_set:
                    # Filter for distance from ego vehicle
                    dist = bb.location.distance(ego.get_transform().location)
                    if True:
        
                       # Calculate the dot product between the forward vector
                        # of the vehicle and the vector between the vehicle
                        # and the bounding box. We threshold this dot product
                        # to limit to drawing bounding boxes IN FRONT OF THE CAMERA
                        forward_vec = ego.get_transform().get_forward_vector()
                        location = bb.location
    
                        ray = location - ego.get_transform().location
                        if forward_vec.dot(ray) > bbtools.bboxParameter.cam_rgb['min_distance']:
                        # Cycle through the vertices
                            p1 = bbtools.get_image_point(bb.location, K, world_2_camera)
                            verts = [v for v in bb.get_world_vertices(carla.Transform())]
                            #print(f'street light vector is {location}')
                            x_max = -10000
                            x_min = 10000
                            y_max = -10000
                            y_min = 10000
             
                            for vert in verts:
                                p = bbtools.get_image_point(vert, K, world_2_camera)
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
    
                            x_min,y_min,x_max,y_max = bbtools.box_corrcttion([x_min,y_min,x_max,y_max])  # to corrct the boxes if they are out of the image dimentions
                            if x_min==x_max:
                                continue
                            box = {'actor':bb,'box':[x_min,y_min,x_max,y_max],'classification' : 'street_light','dist':dist}

                            data_box.append(box)
        
                    
     
             
                            
                for npc in actors:
                    # Filter out the ego vehicle
                    if npc.id != ego.id:
                        actor_classification =bbtools.get_actor_classification(npc.type_id)
                                
                        bb = npc.bounding_box
                        dist = npc.get_transform().location.distance(ego.get_transform().location)
                                    
                        # Filter for the vehicles within 50m
                        if True:
                                    
                        # Calculate the dot product between the forward vector
                         # of the vehicle and the vector between the vehicle
                         # and the other vehicle. We threshold this dot product
                         # to limit to drawing bounding boxes IN FRONT OF THE CAMERA
                            forward_vec = ego.get_transform().get_forward_vector()
                            #print(npc.get_transform().location)
                            location = npc.get_transform().location
                            ray = location - ego.get_transform().location
                                        
                            if forward_vec.dot(ray) > bbtools.bboxParameter.cam_rgb['min_distance']:
                                p1 = bbtools.get_image_point(bb.location, K, world_2_camera)
                                verts = [v for v in bb.get_world_vertices(npc.get_transform())]
                                x_max = -10000
                                x_min = 10000
                                y_max = -10000
                                y_min = 10000
                                    
                                for vert in verts:
                                    p = bbtools.get_image_point(vert, K, world_2_camera)
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
                                #if (int(x_max)<0) or (int(y_min)<0) and (int(x_mix)<0) or (int(y_min)<0):
                                    #continue
                                x_min,y_min,x_max,y_max = bbtools.box_corrcttion([x_min,y_min,x_max,y_max])  # to corrct the boxes if they are out of the image dimentions
                                if x_min==x_max:
                                    continue
    
                                box = {'actor':npc,'box':[x_min,y_min,x_max,y_max],'classification' : actor_classification,'dist':dist}
                                data_box.append(box)
                                #print(ego.get_velocity())
                data_box_filtered = []
    

    
                                  
               
                if len(data_box) > 0:
                    for actor_box in data_box:
                        box = actor_box['box']
                        actor = actor_box['actor']
                        distance = actor_box['dist']
                        box_color = None
                        if actor_box['classification'] == 'street_light':
                            box_color = bbtools.get_color_seg('street_light')
                        if box_color is None:
                            box_color = bbtools.get_color_seg(actor.type_id)
                        x_min,y_min,x_max,y_max = box
                        #box_color.append(255)
                        box_color = tuple(box_color)
                        if distance <= bbtools.bboxParameter.cam_rgb['max_distance']:
    
                            cv2.rectangle(img2, (int(x_max),int(y_max)), (int(x_min),int(y_min)), box_color, 2)
                            cv2.putText(img2, str(int(distance)), (int(x_max), int(y_max)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
                        if bbtools.bboxParameter.cam_rgb['filter']:
                            if not (bbtools.filter_box(box=box,actor = actor, img_seg=img_seg)):
                                continue
                        if distance <= bbtools.bboxParameter.cam_rgb['max_distance']:
                            cv2.rectangle(img, (int(x_max),int(y_max)), (int(x_min),int(y_min)), box_color, 2)
                            cv2.putText(img, str(int(distance)), (int(x_max), int(y_max)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)
                        data_box_filtered.append(actor_box)
    
                        del box
    
            if bbtools.bboxParameter.cam_rgb['figure_in_window']:
                cv2.imshow('ImageWindowName',orginal_img)
            #print(int(time.time()% 60))
            
            

            if bbtools.bboxParameter.cam_rgb['save_to_file']:
                if bbtools.bboxParameter.cam_rgb['filter']:
                    cv2.imwrite(os.path.join(path_image_filter,file_name), img[:,:,:3])
                cv2.imwrite(os.path.join(path_bbox,file_name), img2[:,:,:3])
                bbtools.save_multi_labels(data_box_filtered , path_label,label_name)
            if bbtools.bboxParameter.image_segmentation['save_to_file']:
                cv2.imwrite(os.path.join(path_seg,file_name), img_seg[:,:,:3])

 
        time_sim = time_sim + settings.fixed_delta_seconds

        if (cv2.waitKey(1) == ord('q')):
            break
    cv2.destroyAllWindows()
    pbar.close()
except Exception as e:
    print(e)
#except KeyboardInterrupt:
    #pass

 

    
 
finally:
   
    env.close_env(vehicles_list=vehicles_list,walkers=walkers,nonvehicles_list=nonvehicles_list)
    #camera.destroy()
    #vehicle.destroy()
    weather.set_default_weather()
    cv2.destroyAllWindows()
    env.exit_program()
    

