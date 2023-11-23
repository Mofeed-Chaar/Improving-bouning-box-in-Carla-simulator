import yaml
import os 

class config(object):

	def __init__(self,file_name= None):
		self.file_name=file_name
		dir_path = os.path.dirname(os.path.realpath(__file__))
		dir_path = os.path.join(dir_path,'yaml_files',file_name)

		with open(dir_path, 'r') as file:
			config = yaml.safe_load(file)
		self.args= config['sitting']
		


	def __getattr__(self,attr):
		try:
			return self.args[attr]
		except KeyError:
			raise AttributeError(key)


			
	def get_dic(self):
		return self.args
		