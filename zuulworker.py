
"""
helper class to run zuul-ac in standalone mode without separate smart home controller
for details see https://github.com/stko/zuul-ac/wiki/en_backend#standalone-usage
"""
import json
import threading

import websocket
import rel

class ZuulWorker:
    def __init__(self,url="ws://localhost:8000/", otp_request=None,get_input=None, open_door=None ):
        #websocket.enableTrace(True)
        self.otp_request=otp_request
        self.get_input=get_input
        self.open_door=open_door
        self.type=type
        self.ws = websocket.WebSocketApp(url,
                                # on_open=self.on_open, ## don't use on_open here, use it with run_forever
                                on_message=self.on_message,
                                on_error=self.on_error,
                                on_close=self.on_close)
        self.read_thread:threading.Thread =None
        self.ws.on_open = self.on_open
        self.ws.run_forever(dispatcher=rel, reconnect=5)  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly
        print("Started ZuulWorker")
        rel.signal(2, rel.abort)  # Keyboard Interrupt
        rel.dispatch()
        self.close_thread()

    def on_message(self, ws, message):
        data=json.loads(message)
        #print("received:", data)
        msg_type=data.get("type","")
        if msg_type=="otprequest" and self.otp_request is not None:
            response=self.otp_request(data)
            #print("sending otp approval...")
            ws.send(json.dumps(response))
        elif msg_type=="tokenstate" and self.open_door is not None:
            allow_open=data['config'].get('valid',False)
            self.open_door(allow_open)
        #print(message)

    def close_thread(self):
        print("Closing input thread...")
        if self.read_thread is not None:
            self.read_thread.do_run = False
            self.read_thread.join()

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        self.close_thread()
        print("### closed ###")

    def on_open(self,ws):
        if self.get_input is not None:
            print("Opened connection")
            def run(*args):
                t = threading.current_thread()
                while getattr(t, "do_run", True):
                    user_input = self.get_input()
                    ws.send(f"""{{
                        "type": "ac_tokenquery",
                        "config":{{
                        "token": "{user_input.strip()}"
                        }}
                        }}""")

            # create and start the input thread
            self.read_thread=threading.Thread(target=run)
            self.read_thread.start()
        else:
            print("Opened connection but no get_input function provided, not starting input thread")
