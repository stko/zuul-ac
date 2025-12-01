"""Standalone ZUULAC worker for Raspberry Pi with serial connected QR code reader on /dev/serial0
and GPIO controlled door relay on GPIO2."""

import time
import serial
import RPi.GPIO as GPIO

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
            "type": "qrcode",
            "keypadchars": "1234567890",
            "length": 10,
            "valid_time": 30
        }
    }
    return response

GPIO.setmode(GPIO.BCM)
GPIO.setup(2,GPIO.OUT) #led

# Initialize serial connection to QR code reader
# maybe there's some trouble with permissions, run 'sudo usermod -a -G dialout $USER' and reboot if you have issues
# also see in case of trouble: https://forums.raspberrypi.com/viewtopic.php?t=299548
ser = serial.Serial('/dev/serial0', 9600, timeout=1)
ser.flush()

def get_input()->str:
    """In which ever way you want to get the user input, e.g. from a keypad, QRCode-Reader etc."""
    # Example for reading from a serial connected QR-Code reader

    while True:
        qr_code_value = ser.readline().decode("utf-8", errors="ignore").strip()
        if qr_code_value:
           print("QR Code detected:", qr_code_value)
           return qr_code_value
        time.sleep(0.1)


def open_door(allow_open:bool):
    """ this function is called when zuul detects a valid user attempt """
    if allow_open:
        print ("Open the door")
        # door opening mechanism here
        GPIO.output(2, GPIO.HIGH)  # activate relay to open door
        time.sleep(3)  # simulate door open time
        print ("Close the door")
        GPIO.output(2, GPIO.LOW)  # de activate relay to open door

    else:
        print ("Do not open the door")

if __name__ == "__main__":
    #zuw=ZuulWorker(url="ws://rpi-z-zuulac:8000",otp_request=otp_request,get_input=get_input, open_door=open_door)
    zuw=ZuulWorker(otp_request=otp_request,get_input=get_input, open_door=open_door)

