#!/usr/bin/python3
import json
from configparser import ConfigParser

import psycopg2
import cerberus
from flask import Flask, request

from GatheringInfo import statistics
# Valores globais e constantes

app = Flask(__name__)

ApiFunctions = {"MapTrajectory":statistics.MapTrajectory}


@app.route("/api/v1/<requestType>",methods=['GET'])
def DoRequest(requestType):
    
    if not request.is_json:
        return {"message":'"Content-Type" MUST be set to "application/json"'}, 400
    
    request.on_json_loading_failed(lambda: {} )
    userInput = request.json

    # Adquirindo configs do script
    try:
        userOptions = json.loads(userInput)
    except json.decoder.JSONDecodeError:
        return {"message":"json string is not valid"}, 400

    # Conectar-se ao BD
    database = psycopg2.connect(**CONFIGS['database'])

    if not requestType in ApiFunctions.keys():
        return "DEU MERDA",400

    
    #Selecionar entre diferentes requisicoes
    text, graph = ApiFunctions[requestType](userOptions)

    print(f"Content-Type: application/json\r\n\r\n{json.dumps(userRequest)}")





# EXCEPTIONS DECLARATION
class InvalidJsonDecodingError(Exception):
    def __init__(self):
        self.message = "The post input given is not valid json"

class InvalidJsonValidationError(Exception):
    def __init__(self,ValidationError):
        self.message = f"The json input does not match schema ({ValidationError})"

class InvalidJsonRequestError(Exception):
    def __init__(self,message):
        self.message = f"the request '{message}' does not match current suported requests"