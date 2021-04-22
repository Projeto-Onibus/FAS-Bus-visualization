FROM python:3.7

RUN python3 -m pip install psycopg2 numpy bokeh flask 

RUN python3 -m pip install cerberus

COPY ./app /app

WORKDIR /app

RUN export FLASK_APP=/app/api.py

CMD [ "flask","run"]