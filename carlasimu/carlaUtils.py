'''
Creat 15.09.2022
@autor: Mohamad Mofeed Chaar
'''
from . import config
from numpy import random

import glob
import os
import sys
import time
import logging
try:
	sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
		sys.version_info.major,
		sys.version_info.minor,
		'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
	print('carla not found')
	pass

import carla

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

class CarlaEnvironment(object):

	def __init__(self,host=None,port=None,maps=None,set_timeout=None):
		self.host = host
		self.port = port
		self.set_timeout = set_timeout
		
		self.carla = carla
		self.args = config.config('data.yaml')
		if self.host is None:
			self.host = self.args.host
		if self.port is None:
			self.port = self.args.port
		self.client = carla.Client(self.host,self.port)
		if set_timeout is None:
			self.set_timeout = self.args.set_timeout

		self.client.set_timeout(self.set_timeout)
		if maps is None:
			self.world = self.client.get_world()
		else:
			self.world = self.client.load_world(maps)

		self.synchronous_master = False



		# sitting of traffic manager
		self.traffic_manager = self.client.get_trafficmanager(self.args.tm_port)
		self.traffic_manager.set_global_distance_to_leading_vehicle(self.args.global_distance_to_leading_vehicle)

		if self.args.synchronous:
			self.synchronous()

		self.vehicles_name = config.config('vehicles_name.yaml')
		self.mapLayer = config.config('mapLayer.yaml')
		self.set_mapLayer()



		


	def get_client(self):
		return self.client

	def get_walker_points(self,number_of_points=0):


		'''
		To get random spawn_points form the map
		num = int:number of spawn_points
		# random spawn_points for the walkers

		return:
			list:spawn_points

		'''

		spawn_points = []
		for i in range(number_of_points):

			spawn = self.carla.Transform()
			position = self.world.get_random_location_from_navigation()
			#spawn.location.z +=1 #up the z axis to avoid the collision
			if (position !=None):
				spawn.location = position
				spawn.location.z +=5
				spawn_points.append(spawn)


		return spawn_points

	def get_vehicles_points(self,number_of_vehicles=None):

		#get point for the vehicles
		if number_of_vehicles is None:
			number_of_vehicles=self.args.number_of_vehicles
		spawn_points = self.world.get_map().get_spawn_points()
		number_of_spawn_points = len(spawn_points)
		if number_of_vehicles < number_of_spawn_points:
			random.shuffle(spawn_points)
		elif number_of_vehicles > number_of_spawn_points:
			msg = 'requested %d vehicles, but could only find %d spawn points'
			logging.warning(msg, number_of_vehicles, number_of_spawn_points)
			self.args.number_of_vehicles = number_of_spawn_points

		return spawn_points




	def set_client(self,client=None):
		self.client=client


	def activate_actors(self,actors):
		all_actors,walker_speed,all_id,_ = actors
		for i in range(0, len(all_id), 2):
			# start walker
			all_actors[i].start()
			# set walk to random point
			all_actors[i].go_to_location(self.world.get_random_location_from_navigation())
			# max speed
			all_actors[i].set_max_speed(float(walker_speed[int(i/2)]))
		self.traffic_manager.global_percentage_speed_difference(30.0)



	def wait(self,synchronous_master=True,wait_for_tick=None):
		if wait_for_tick is None:
			wait_for_tick=self.args.wait_for_tick



		
		print('press Ctrl+C to exit')
		try:
			while True:
				if not self.args.asynch and synchronous_master:
					self.world.tick()
					#controller.update_light_state(vehicle,light_state)
				
				else:
					self.world.wait_for_tick(wait_for_tick)
				
		except KeyboardInterrupt:
			print('You Interrupt the simulation, the program will be normally exit.')
		
		
	def close_env(self,vehicles_list=None,walkers=None,nonvehicles_list=[]):
		settings = self.world.get_settings()
		settings.synchronous_mode = False
		settings.fixed_delta_seconds = None
		for sensor in nonvehicles_list:
			sensor.stop()
		if vehicles_list is None:
			vehicles_list=self.world.get_actors().filter('vehicle.*')

		self.world.apply_settings(settings)
		print('\ndestroying %d vehicles' % len(vehicles_list))
		self.client.apply_batch([self.carla.command.DestroyActor(x) for x in vehicles_list])
		print('destroying %d sensors' % len(nonvehicles_list))
		self.client.apply_batch([self.carla.command.DestroyActor(x) for x in nonvehicles_list])
		all_id=[] # id of walkers
		if walkers is None:
			walkers=self.world.get_actors().filter('walker.pedestrian.*')
			
			for walker in walkers:
				all_id.append(walker.id)



		else:
			all_actors,_,all_id,walkers_list = walkers
			for i in range(0, len(all_actors), 2):
				all_actors[i].stop()

		print('\ndestroying %d walkers' % len(all_id))
		self.client.apply_batch([self.carla.command.DestroyActor(x) for x in all_id])
		time.sleep(0.5)
		print('\ndone')


	def synchronous(self,apply_settings=None):
		# if apply_settings is True, the environment movment will be more speed
		# if apply_settings is False, the environment movment will be more reality
		if apply_settings is None:
			apply_settings = self.args.apply_settings
		print('\nRUNNING in synchronous mode\n')
		if self.args.respawn:
			self.traffic_manager.set_respawn_dormant_vehicles(self.args.respawn)
		if self.args.hybrid:
			self.traffic_manager.set_hybrid_physics_mode(True)
			self.traffic_manager.set_hybrid_physics_radius(70.0)
		if self.args.seed is not None:
			self.traffic_manager.set_random_device_seed(self.args.seed)

		settings = self.world.get_settings()
		
		if not self.args.asynch:
			self.traffic_manager.set_synchronous_mode(True)
			if not settings.synchronous_mode:
				self.synchronous_master = True
				settings.synchronous_mode = True
				settings.fixed_delta_seconds = self.args.fixed_delta_seconds
			else:
				self.synchronous_master = False
		else:
			print("You are currently in asynchronous mode. If this is a traffic simulation, \
			you could experience some issues. If it's not working correctly, switch to synchronous \
			mode by using traffic_manager.set_synchronous_mode(True)")

		if self.args.no_rendering:
			settings.no_rendering_mode = True
		if apply_settings:
			self.world.apply_settings(settings)
			
		return self.synchronous_master


	def get_actor_blueprints(self, filter, generation='all'):
		# we copy some of codes in this function from the calrla simulation examples generate_traffic.py
		bps = self.world.get_blueprint_library().filter(filter)


		if generation.lower() == "all":
			return bps

		# If the filter returns only one bp, we assume that this one needed
		# and therefore, we ignore the generation
		if len(bps) == 1:
			return bps

		try:
			int_generation = int(generation)
			# Check if generation is in available generations
			if int_generation in [1, 2]:
				bps = [x for x in bps if int(x.get_attribute('generation')) == int_generation]
				return bps
			else:
				print("Warning! Actor Generation is not valid. No actor will be spawned.")
				return []
		except:
			print("Warning! Actor Generation is not valid. No actor will be spawned.")
			return []

	


	def set_mapLayer(self):
		if not self.mapLayer.buliding:
			self.world.unload_map_layer(carla.MapLayer.Buildings)
		if not self.mapLayer.ParkedVehicles:
			self.world.unload_map_layer(carla.MapLayer.ParkedVehicles)

	def exit_program(self):
		print("Exiting the program...")
		sys.exit()

	



if __name__=='__main__':
	env = CarlaEnvironment()

