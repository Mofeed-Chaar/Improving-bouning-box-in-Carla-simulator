from .ActorController import  Controller
from .exceptions import lightStateNotCorrect
from .exceptions import NumberOfWheels
from .config import config
from numpy import random

import numpy as np
import logging


logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)


class vehicles(Controller):
	def __init__(self, env):
		self.vehicles_list = []
		self.vehicles_name = config('vehicles_name.yaml')
		
		super().__init__(env)



	def set_vehicles(self,blueprints=None,number_of_vehicles=None, number_of_wheels=None,same_number=False,hero=None,main_function=True):
		if number_of_wheels is None:
			number_of_wheels = self.env.args.number_of_wheels
		if number_of_vehicles is None:
			number_of_vehicles = self.env.args.number_of_vehicles
		if hero is None:
			hero = self.env.args.hero
		if blueprints is None:
			blueprints = self.env.get_actor_blueprints(filter=self.env.args.filterv, generation =self.env.args.generationv)
		blueprints = self.blueprints_safe(blueprints,safe=self.env.args.safe)
		blueprints = sorted(blueprints, key=lambda bp: bp.id)
		spawn_points = self.env.get_vehicles_points(number_of_vehicles)
		batch = []
		
		#hero = self.env.args.hero

		for n, transform in enumerate(spawn_points):

			if n >= number_of_vehicles:
				break
			blueprint = random.choice(blueprints)
			if number_of_wheels=='4':
				if (int(blueprint.get_attribute('number_of_wheels')) == 2):#-------------------------------------filter 4 wheels---------------------------
					continue
			elif number_of_wheels=='2':
				if (int(blueprint.get_attribute('number_of_wheels')) == 4):#-------------------------------------filter 2 wheels---------------------------
					continue
			elif not (number_of_wheels.lower() == 'all'):
				message = 'The number of wheels is not correct please choes "1","2", or "ALL" in the env.args.number_of_wheels or in data.yaml'
				raise NumberOfWheels(message)

			if blueprint.has_attribute('color'):
				color = random.choice(blueprint.get_attribute('color').recommended_values)
				blueprint.set_attribute('color', color)
			if blueprint.has_attribute('driver_id'):
				driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
				blueprint.set_attribute('driver_id', driver_id)
			if self.env.args.hero:
				blueprint.set_attribute('role_name', 'hero')
				print('there is hero now')
				self.env.args.hero = False
			else:
				blueprint.set_attribute('role_name', 'autopilot')
			


			# spawn the cars and set their autopilot and light state all together

			batch.append(self.SpawnActor(blueprint, transform).then(self.SetAutopilot(self.FutureActor, True, self.env.traffic_manager.get_port())))

		for response in self.env.client.apply_batch_sync(batch, self.env.synchronous_master):
			if response.error:
				logging.error(response.error)
			else:
				self.vehicles_list.append(response.actor_id)
			# Set automatic vehicle lights update if specified
		if self.env.args.car_lights_on:
			all_vehicle_actors = self.env.world.get_actors(self.vehicles_list)
			for actor in all_vehicle_actors:
				self.env.traffic_manager.update_vehicle_lights(actor, True)
				#vehicles(self,blueprints,number_of_wheels=None)

		if same_number:
			if len(self.vehicles_list)<number_of_vehicles:
				self.vehicles_list2=self.set_vehicles(blueprints=blueprints,number_of_vehicles=(number_of_vehicles-len(self.vehicles_list)),
				 number_of_wheels=number_of_wheels,same_number=same_number,hero=hero,main_function=False)
				self.vehicles_list.extend(self.vehicles_list2)
		
		if (main_function) and (self.is_the_light_state_update_true()):
			light_state = self.get_ture_light_state()
			vehicles = self.env.world.get_actors().filter('vehicle.*')
			self.update_light_state(vehicles,light_state)


		return self.vehicles_list



	def get_ego(self):
		ego = None
		for actor in self.env.world.get_actors().filter('vehicle.*'):
			if actor.attributes.get('role_name') == 'hero':
				ego = actor
				break
		return ego



	def __len__(self):
		return len(self.vehicles_list)





class walkers(Controller):
	def __init__(self,env):
		self.all_walkers = None
		super().__init__(env)


	def set_walkers(self,blueprintsWalkers=None,number_walkers=None,same_number=True,activate_actors=True,main_function=True):
		'''
		blueprintWalkers
		number_walkers[tuple](stand,walk,run)
		'''
		if number_walkers is None:
			number_walkers = (self.env.args.number_of_walkers['stand'],self.env.args.number_of_walkers['walk'],self.env.args.number_of_walkers['run'])
		self.all_walkers = np.sum(number_walkers)


		# some settings
		percentagePedestriansWalking = number_walkers[1]
		percentagePedestriansRunning = number_walkers[2]      # how many pedestrians will run
        
		percentagePedestriansCrossing = 0.0     # how many pedestrians will walk through the road
		# 1. take all the random locations to spawn
		if blueprintsWalkers is None:
			blueprintsWalkers = self.env.get_actor_blueprints(filter=self.env.args.filterw, generation =self.env.args.generationw)

		spawn_points = self.env.get_walker_points(self.all_walkers)
		

		batch = []
		walker_speed = []
		walkers_list = []
		all_id = []
		for spawn_point in spawn_points:
			walker_bp = random.choice(blueprintsWalkers)
			# set as not invincible
			if walker_bp.has_attribute('is_invincible'):
				walker_bp.set_attribute('is_invincible', 'false')
			# set the max speed
			if walker_bp.has_attribute('speed'):
				if (percentagePedestriansRunning > 0):
					# running
					walker_speed.append(walker_bp.get_attribute('speed').recommended_values[2])#
					percentagePedestriansRunning -=1
				elif(percentagePedestriansWalking > 0):
					# walking
					walker_speed.append(walker_bp.get_attribute('speed').recommended_values[1])
					percentagePedestriansWalking -=1
				else:
					walker_speed.append(walker_bp.get_attribute('speed').recommended_values[0])

			else:
				print("Walker has no speed")
				walker_speed.append(0.0)
			batch.append(self.SpawnActor(walker_bp, spawn_point))
		results = self.env.client.apply_batch_sync(batch, True)
		walker_speed2 = []
		for i in range(len(results)):
			if results[i].error:
				logging.error(results[i].error)
			else:
				walkers_list.append({"id": results[i].actor_id})
				walker_speed2.append(walker_speed[i])
		walker_speed = walker_speed2
		# 3. we spawn the walker controller
		batch = []
		walker_controller_bp = self.env.world.get_blueprint_library().find('controller.ai.walker')
		for i in range(len(walkers_list)):
			batch.append(self.SpawnActor(walker_controller_bp, self.env.carla.Transform(), walkers_list[i]["id"]))
		results = self.env.client.apply_batch_sync(batch, True)
		for i in range(len(results)):
			if results[i].error:
				logging.error(results[i].error)
			else:
				walkers_list[i]["con"] = results[i].actor_id
		# 4. we put altogether the walkers and controllers id to get the objects from their id
		for i in range(len(walkers_list)):
			all_id.append(walkers_list[i]["con"])
			all_id.append(walkers_list[i]["id"])
		

		# wait for a tick to ensure client receives the last transform of the walkers we have just created
		if self.env.args.asynch or not self.env.synchronous_master:
			self.env.world.wait_for_tick()
		else:
			self.env.world.tick()

		# 5. initialize each controller and set target to walk to (list is [controler, actor, controller, actor ...])
		# set how many pedestrians can cross the road
		self.env.world.set_pedestrians_cross_factor(percentagePedestriansCrossing)

		if same_number:
			run = len([x for x in walker_speed if float(x)>=2])
			walk = len([x for x in walker_speed if (float(x)<2 and float(x)>0)])
			stand = len([x for x in walker_speed if float(x)==0])	
			if not (stand==number_walkers[0] and walk==number_walkers[1] and run==number_walkers[2] ):
				_ , walker_speed2 , all_id2,walkers_list2 = self.set_walkers(blueprintsWalkers,
																		(number_walkers[0]-stand,number_walkers[1]-walk,number_walkers[2]-run),
																		same_number,main_function=False)
				
				walker_speed.extend(walker_speed2)
				all_id.extend(all_id2)
				walkers_list.extend(walkers_list2)


		
		if main_function:
			print(f'now, the number of walkers is {len(walker_speed)}')
			run = len([x for x in walker_speed if float(x)>=2])
			print(f'now, the number of running is {run}')
			walk = len([x for x in walker_speed if (float(x)<2 and float(x)>0)])
			print(f'now, the number of walking is {walk}')	
			stand = len([x for x in walker_speed if float(x)==0])	
			print(f'now, the number of stand is {stand}')
		all_actors = self.env.world.get_actors(all_id)
		actors = [all_actors,walker_speed,all_id,walkers_list]
		if activate_actors:
			self.env.activate_actors(actors)

		return actors
