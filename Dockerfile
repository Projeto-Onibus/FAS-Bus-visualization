FROM python:3.7 AS development

RUN python3 -m pip install psycopg2 numpy bokeh flask uwsgi redis python-redis-cache

RUN python3 -m pip install cerberus

COPY ./app /app

WORKDIR /app

RUN export FLASK_APP=api.py

# Start server
CMD [ "uwsgi", "app.ini" ]