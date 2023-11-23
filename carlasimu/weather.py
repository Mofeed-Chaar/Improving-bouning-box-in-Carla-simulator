
from .config import config
class Weather(object):
	def __init__(self,env):
		self.env = env
		self.default_weather = self.env.world.get_weather()



	def set_weather(self,weather=None):
		if weather is None:

			weather = self.env.world.get_weather()
			param = self.get_weather_parameter()
	
			if param.sun_azimuth_angle is not None:
				weather.sun_azimuth_angle = param.sun_azimuth_angle
			if param.sun_altitude_angle is not None:
				weather.sun_altitude_angle = param.sun_altitude_angle
			if param.cloudiness is not None:
				weather.cloudiness = param.cloudiness
			if param.precipitation is not None:
				weather.precipitation = param.precipitation
			if param.precipitation_deposits is not None:
				weather.precipitation_deposits = param.precipitation_deposits
			if param.wind_intensity is not None:
				weather.wind_intensity = param.wind_intensity
			if param.fog_density is not None:
				weather.fog_density = param.fog_density
			if param.fog_distance is not None:
				weather.fog_distance = param.fog_distance
			if param.fog_falloff is not None:
				weather.fog_falloff = param.fog_falloff
			if param.wetness is not None:
				weather.wetness = param.wetness
			if param.scattering_intensity is not None:
				weather.scattering_intensity = param.scattering_intensity
			if param.mie_scattering_scale is not None:
				weather.mie_scattering_scale = param.mie_scattering_scale
			if param.rayleigh_scattering_scale is not None:
				weather.rayleigh_scattering_scale = param.rayleigh_scattering_scale
			if param.dust_storm is not None:
				weather.dust_storm = param.dust_storm



		self.env.world.set_weather(weather)
		print('Weahter has been updated')


	def get_weather_parameter(self):
		parameter = config('weather.yaml')
		return parameter

	def set_default_weather(self):
		self.env.world.set_weather(self.default_weather)

	def get_weather(self):
		return self.env.world.get_weather()
