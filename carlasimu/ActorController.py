
import sys
from .exceptions import lightStateNotCorrect
import copy
from .exceptions import NumberOfWheels
class Controller(object):
	def __init__(self,env):
		self.env = env
		self.SpawnActor = self.env.carla.command.SpawnActor
		self.SetAutopilot = self.env.carla.command.SetAutopilot
		self.FutureActor = self.env.carla.command.FutureActor



	def update_light_state(self,vehicles,light_state):
		if self.env.args.car_lights_on:
			
			for actor in vehicles:
				self.env.traffic_manager.update_vehicle_lights(actor, False)
		light_state_list = self.__light_state(light_state)
		for vehicle in vehicles:
			self.__vehicle_light_state(vehicle,light_state_list)





	def __vehicle_light_state(self,vehicle,light_state):
				
		if light_state is None:
			return None
		lights = self.env.carla.VehicleLightState.NONE 


		for light in light_state:
			lights |=light
		vehicle.set_light_state(self.env.carla.VehicleLightState(lights))


	def __light_state(self,state:list): 

	
	#the input: list of light states (look at light_state in data.yaml file and tutorial_vehcles.py)
	

	
		if not isinstance(state, list):

			message = 'The input in light_state should be list: example light_state(["Fog"])' 
			raise lightStateNotCorrect(message)
		light_state = list(self.env.args.light_state.keys())

		if None in state: # if none exist in the list that mean turn off all the lights
			lights = self.env.carla.VehicleLightState.NONE
			return [lights]

		if len(state)==0:
			message = 'The list of light state is empty'
			return None

		# convert all elements to lower
		for m in range(len(light_state)):
			if isinstance(light_state[m],str):
				light_state[m]=light_state[m].lower()
  
		for n in range(len(state)):
			if isinstance(state[n],str):
				state[n]=state[n].lower()

		for i in state:
			if  i not in light_state:
				message=f'The input in light_state is not correct, where ({i}) does not exist in light_state, look at data.yaml'
				raise lightStateNotCorrect(message)

		light_state_list = [] #list of lights

		if 'all' in  state:# ------------------------------------------------------------------------------if you put in input ('ALL'), all lights will open
			#return light_state_list.append(self.env.carla.VehicleLightState.ALL)
			for all_lights in light_state:
				if all_lights in ['all', None]:
					continue
				light = self.__make_light_state(all_lights)
				light_state_list.append(light)
			return light_state_list

		for i in state:
			light = self.__make_light_state(i)
			light_state_list.append(light)

		return light_state_list




	def __make_light_state(self,light: str):
		states = {'position':self.env.carla.VehicleLightState.Position,
				'lowbeam':self.env.carla.VehicleLightState.LowBeam,
				'highbeam':self.env.carla.VehicleLightState.HighBeam,
				'brake':self.env.carla.VehicleLightState.Brake,
				'rightblinker':self.env.carla.VehicleLightState.RightBlinker,
				'leftblinker':self.env.carla.VehicleLightState.LeftBlinker,
				'reverse':self.env.carla.VehicleLightState.Reverse,
				'fog':self.env.carla.VehicleLightState.Fog,
				'interior':self.env.carla.VehicleLightState.Interior,
				'special1':self.env.carla.VehicleLightState.Special1,
				'special2':self.env.carla.VehicleLightState.Special2
				}
		return states[light]


	def blueprints_safe(self,blueprints,safe=None):
		if safe is None:
			save = self.env.args.safe
		'''# this for carla 9.14
		if safe:
			blueprints = [x for x in blueprints if x.get_attribute('base_type') == 'car']
		'''
		if safe:
			#blueprints = [x for x in blueprints if not x.id.endswith('microlino')]
			blueprints = [x for x in blueprints if not x.id.endswith('carlacola')]
			#blueprints = [x for x in blueprints if not x.id.endswith('cybertruck')]
			#blueprints = [x for x in blueprints if not x.id.endswith('t2')]
			#blueprints = [x for x in blueprints if not x.id.endswith('sprinter')]
			blueprints = [x for x in blueprints if not x.id.endswith('firetruck')]
			#blueprints = [x for x in blueprints if not x.id.endswith('ambulance')]
		
		blueprints = sorted(blueprints, key=lambda bp: bp.id)

		return blueprints


	

	def is_the_light_state_update_true(self):
		for k,v in self.env.args.light_state.items():
			if v:

				return True

		return False

	def get_ture_light_state(self):
		list_true = []
		for k,v in self.env.args.light_state.items():

			if v:
				list_true.append(k)
		if len(list_true)==0:
			return None
		return list_true




			
		
			






