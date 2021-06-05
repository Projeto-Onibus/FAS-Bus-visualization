#!/usr/bin/python3
import json
from configparser import ConfigParser

import psycopg2
import cerberus
from flask import Flask, request

import statistics
# Valores globais e constantes

app = Flask(__name__)
CONFIGS = ConfigParser()
CONFIGS.read("DatabaseConfigs.ini")
database = psycopg2.connect(**CONFIGS['database'])


ApiFunctions = {"MapTrajectory":statistics.MapTrajectory,
                "BusAmount":statistics.BusAmount,
                "LinePerformanceDay":statistics.linePerformanceDay
                }

@app.route("/v1/<requestType>",methods=['GET'])
def DoRequest(requestType):
    
    if not request.is_json:
        return {"message":'"Content-Type" MUST be set to "application/json"'}, 400
    
    request.on_json_loading_failed(InvalidJsonDecodingError)
    userInput = request.json

    # Adquirindo configs do script
    try:
        userOptions = json.loads(userInput)
    except json.decoder.JSONDecodeError:
        return {"message":"json string is not valid"}, 400

    if not requestType in ApiFunctions.keys():
        return "Error: Request not valid",400

    
    #Selecionar entre diferentes requisicoes
    text, graph = ApiFunctions[requestType](userOptions, database, CONFIGS)
    
    print("Content-Type: application/json\r\n\r\n")
    return graph


if __name__ == "__main__":
    app.run()


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