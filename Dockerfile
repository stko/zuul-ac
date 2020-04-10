FROM python:3

ADD my_script.py /

RUN pip install qrcode[pil] python-telegram-bot 

CMD [ "python", "./my_script.py" ]
