import importlib
import traceback
import sys
import zuullogger
import storage
import threading

class Messenger(object):

	def __init__(self, messenger_name, messenger_token, access_manager): 
		try:
			self.messenger_name=messenger_name
			self.messenger_token=messenger_token
			self.access_manager=access_manager
			myModule=importlib.import_module("m_" + messenger_name.lower())
			self.my_messenger_class=getattr(myModule,"ZuulMessengerPlugin")
			# Create a Thread with a function without any arguments
			self.th = threading.Thread(target=self.run_thread)
			# Start the thread
			self.th.setDaemon(True) 
			self.th.start()
		except:
			print("Can't load plugin "+messenger_name)
			self.plugin=None
			traceback.print_exc(file=sys.stdout)

	def run_thread(self):
		self.messenger=self.my_messenger_class(self.messenger_token,self.access_manager)



if __name__ == '__main__':

	# https://inventwithpython.com/blog/2014/12/20/translate-your-python-3-program-with-the-gettext-module/
	'''
	import gettext
	localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locale')
	translate = gettext.translation('guess', localedir, fallback=True)
	_ = translate.gettext
	'''
	_ = lambda s: s



	logger = zuullogger.getLogger(__name__)

	messenger_token=storage.read_config_value("messenger_token")
	messenger_type=storage.read_config_value("messenger_type")
	print(messenger_token,messenger_type )
	if messenger_token and messenger_type:
		messenger= Messenger(messenger_type,messenger_token)
	else:
		logger.error(_("Config incomplete: No messenger_token or messenger_type"))
	
