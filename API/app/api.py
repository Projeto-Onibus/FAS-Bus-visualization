#!/usr/bin/python3
import json
from configparser import ConfigParser
from pathlib import Path
import datetime

import psycopg2
import cerberus
from flask import Flask, request

import statistics
# Valores globais e constantes

app = Flask(__name__)

# Importing configurations
configPath = Path("/app/") / "main.conf"
CONFIGS = ConfigParser()
CONFIGS.read(configPath)

attemptConnect = datetime.datetime.now()
maxTimeAttempt = datetime.timedelta(minutes=1)


print("Connected to database")
ApiFunctions = {"MapTrajectory":statistics.MapTrajectory,
                "BusAmount":statistics.BusAmount,
                "LinePerformanceDay":statistics.linePerformanceDay
                }

@app.route("/v1/<requestType>",methods=['GET'])
def DoRequest(requestType):
    
    if not request.is_json:
        return {"message":'"Content-Type" MUST be set to "application/json"'}, 400
    
    print(f"sent data:{request.get_json()}")
    # Adquirindo configs do script
    try:
        userOptions = json.loads(request.get_json())
    except Exception as err:
        return {"message":"json string is not valid","details":err.__str__()}, 400

    if not requestType in ApiFunctions.keys():
        return {"Error":"Request not valid"},400

    print(f"useroptions ({type(userOptions)}): {userOptions}")
    #Selecionar entre diferentes requisicoes
    try:
        text, graph = ApiFunctions[requestType](userOptions, dict(CONFIGS['database']))
    except Exception as err:
        return {"message":"could not process this request. Contact administration",
                "details":{"name":err.__str__()}}, 400

    results = {"text":text,"graph":graph}
    return results


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