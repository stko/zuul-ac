import importlib
import traceback
import sys
import zuullogger
import storage

class Messenger(object):

	def __init__(self, messenger_name, messenger_token): 
		try:
			self.messenger_name=messenger_name
			myModule=importlib.import_module("m_" + messenger_name.lower())
			my_messenger_class=getattr(myModule,"ZuulMessengerPlugin")
			self.messenger=my_messenger_class(messenger_token)
		except:
			print("Can't load plugin "+messenger_name)
			self.plugin=None
			traceback.print_exc(file=sys.stdout)



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
	
