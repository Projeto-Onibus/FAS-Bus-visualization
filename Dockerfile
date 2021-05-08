FROM python:3.7 AS development

RUN python3 -m pip install psycopg2 numpy bokeh flask 

RUN python3 -m pip install cerberus

COPY ./app /app

WORKDIR /app

RUN export FLASK_APP=/app/api.py

CMD [ "flask","run"]

FROM nginx:1.19-alpine

COPY ./www/conf/nginx.conf /etc/nginx/nginx.conf

# Pass static site

# Pass API
COPY --from=development /app/* /www/

