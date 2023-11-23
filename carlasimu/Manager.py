'''
Creat 16.09.2022
@autor: Mohamad Mofeed Chaar
'''
from .ActorController import Controller
from .weather import Weather
from .Actors import *
from .BoundingBox import *
from .sensors import sensors


from . import config as config



class CarlaManager(object):
	def __init__(self,CarlaEnvironment=None):
		self.env=CarlaEnvironment


	def ActorController(self):
		return Controller(self.env)

	def weather(self):
		return Weather(self.env)

	def vehicles(self):
		return vehicles(self.env)

	def walkers(self):
		return walkers(self.env)

	def BoundingBox(self):
		return BoundingBox(self.env)

	def sensors(self):
		return sensors(self.env)
	











		 