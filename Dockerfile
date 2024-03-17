FROM python:3

COPY *.py ./
COPY public ./public
COPY locale ./locale

RUN mkdir config && pip install qrcode[pil] python-telegram-bot ecdsa nest_asyncio

CMD [ "python", "./zuulac.py" ]

EXPOSE 8000