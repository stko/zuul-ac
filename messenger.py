import importlib
import traceback
import sys
import zuullogger
import storage
import threading
import asyncio
import nest_asyncio

class Messenger(object):
    """abstract class to load the real used messenger as plugin

    TODO: There is not much wrapping in the moment... In case we'll going to add another messenger, then a lot of wrapping need to be done here
    """

    def __init__(self, messenger_name, messenger_token, access_manager):
        """creates a messenger object by load the wanted plugin

        Args:
        messenger_name (:obj:`str`): name of the messenger to load
        messenger_token (:obj:`str`): API token of the messenger needed to login as bot to the messenger system
        access_manager (:obj:`obj`): the access manager object
        """

        try:
            self.messenger_name = messenger_name
            self.messenger_token = messenger_token
            self.access_manager = access_manager
            myModule = importlib.import_module("m_" + messenger_name.lower())
            self.my_messenger_class = getattr(myModule, "ZuulMessengerPlugin")
            self.messenger = self.my_messenger_class(
                self.messenger_token, self.access_manager
            )

            """
			# Create a Thread with a function without any arguments
			self.th = threading.Thread(target=self.run_thread)
			# Start the thread
			self.th.setDaemon(True)
			self.th.start()
			"""
        except:
            print("Can't load plugin " + messenger_name)
            self.plugin = None
            traceback.print_exc(file=sys.stdout)

    def run_thread(self):
        """starts the messenger"""
        self.messenger = self.my_messenger_class(
            self.messenger_token, self.access_manager
        )

    async def run_async(self):
        """starts the messenger"""
        await self.messenger.run()

    def run_sync(self):
        """starts the messenger"""
        self.messenger.run()

    def shutdown(self):
        """ends the messenger"""
        self.messenger.shutdown()


if __name__ == "__main__":
    # https://inventwithpython.com/blog/2014/12/20/translate-your-python-3-program-with-the-gettext-module/
    """
    import gettext
    localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locale')
    translate = gettext.translation('guess', localedir, fallback=True)
    _ = translate.gettext
    """

    def _(s):
        return s

    logger = zuullogger.getLogger(__name__)

    messenger_token = storage.read_config_value("messenger_token")
    messenger_type = storage.read_config_value("messenger_type")
    print(messenger_token, messenger_type)
    if messenger_token and messenger_type:
        messenger = Messenger(messenger_type, messenger_token)
    else:
        logger.error(_("Config incomplete: No messenger_token or messenger_type"))
