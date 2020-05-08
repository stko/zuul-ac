FROM python:3

COPY *.py ./
COPY public ./public
COPY locale ./locale

RUN pip install qrcode[pil] python-telegram-bot 

CMD [ "python", "./zuulac.py" ]

EXPOSE 8000