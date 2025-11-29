import time
from zuulworker import ZuulWorker

def otp_request(requestdata):
    # Here you can implement your logic to handle the OTP request
    # for details see https://github.com/stko/zuul-ac/wiki/en_backend#user-allowance-request
    # For demonstration, we will just approve the request with a fixed response
    #print("OTP request received:", requestdata)
    response = {
        "type": "ac_otprequest",
        "config": {
            "result": True,
            "msg": "This pin {1} is valid for {0} seconds",
            "type": "text",
            "keypadchars": "abcd",
            "length": 4,
            "valid_time": 30
        }
    }
    return response

def get_input()->str:
    """In which ever way you want to get the user input, e.g. from a keypad, QRCode-Reader etc."""
    user_input = input("Enter the Pin: ")
    print()
    return user_input.strip()

def open_door(allow_open:bool):
    """ this function is called when zuul detects a valid user attempt """
    if allow_open:
        print ("Open the door")
        # door opening mechanism here
        time.sleep(2)  # simulate door open time
        print ("Close the door")
    else:
        print ("Do not open the door")

if __name__ == "__main__":
    #zuw=ZuulWorker(url="ws://rpi-z-zuul:8000",otp_request=otp_request,get_input=get_input, open_door=open_door)
    zuw=ZuulWorker(otp_request=otp_request,get_input=get_input, open_door=open_door)

