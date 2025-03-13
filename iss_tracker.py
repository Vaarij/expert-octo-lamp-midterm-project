#!/usr/bin/env python3
import requests
import logging
import xmltodict
import time
from typing import Tuple, List
import math
from flask import Flask, request
import json

app = Flask(__name__)

def pull_data(url: str):
    """
    The following function takes in a url as a string and returns the data from the request. This ensures that if there is an invalid request, the program can effectively handle the response.
    
    Args:
        URL (string): is the url of the data to read
    
    Returns:
        either null if the request is invalid and will log that
        or the response content if the request is a success
    """
    response = requests.get(url=url)
    
    if response.status_code == 200:
        content = response.content
        return xmltodict.parse(content)
    
    else:
        logging.error(f"Error, request failed with status code {response.status_code}")
        raise ValueError()
    
def read_data_from_xml(filepath: str):
    """
    This function is a fail-safe in case the user cannot import the data through requests
    
    Args:
        filepath (str): the filepath to the xml data
        
    Returns:
        the data as a JSON
    
    (No tests will be written for this function as it's a fail-safe)
    """
    with open(filename, "r") as f:
        data = xmltodict.parse(f.read())
        
    return data

"""
Edited with Claude 3.7, needed some guidance on an Attribute error. Input the Attribute Error as a prompt to see if I could get some help in decoding it.
"""
def find_data_point(data, *keys):
    """
    The following argument will take in some data in the form of a json string, as well as strings that represent the location of the time stamps and epoch times
    
    Args:
        data: a json object
        *args: a list of strings that points to the location of the data within a json datatype
    
    Returns:
        Either the data, or a null return if the data is not found
    """
    
    current = data
    
    try:
        for key in keys:
            if isinstance(current, bytes):
                current = json.loads(current.decode('utf-8'))
            
            if isinstance(current, dict):
                if key in current:
                    current = current[key]
                else:
                    print(f"Key '{key}' not found in data structure")
                    return None  # Or handle the missing key differently
            else:
                print(f"Expected dictionary, got {type(current).__name__}")
                return None
        return current
        
    except KeyError:
        logging.error(f"Key Error at find_data_point")
        raise KeyError()
 
    except IndexError:
        logging.error(f"Index Error at find_data_point")
        raise IndexError()
    
    except ValueError:
        logging.error(f"Value Error at find_data_point")
        raise ValueError()
    
    except AttributeError:
        logging.error(f"Attribute Error at find_data_point")
        raise AttributeError()
    

def instantaneous_speed(x: float, y: float, z: float) -> float:
    """
    This function is a helper function to find the instantaneous speed of an object given it's velocity vectors
    
    Args:
        x, y, z (float): the x, y, z velocity vectors
    
    Returns:
        float: the speed
    """
    return math.sqrt((x**2) + (y**2) + (z**2))


@app.route('/epochs', methods=['GET'])
def get_all_data():
    """
    The following function gets all the data points in the epochs section
    
    Args:
        None
    
    Returns:
        A list of all the data
    """
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = pull_data(url)
    list_of_data = find_data_point(data, "ndm", "oem", "body", "segment", "data", "stateVector")
    try:
        limit = int(request.args.get('limit', '100000000000000'))
        offset = int(request.args.get('offset', '0'))
        
        ret_degree = []
        if limit > len(list_of_data):
            limit = len(list_of_data)
        
        for i in range(offset, limit):
            ret_degree.append(list_of_data[i])
        
        return ret_degree
        
    except ValueError as e:
        return str(e)

@app.route('/epochs/<epoch>', methods=['GET'])
def get_specific_data(epoch):
    """
    This function returns a specific epoch given the time and id for the epoch
    
    Args:
        Epoch (str): an id in the form of the string in the form of a string
    
    Returns:
        Either a string that identifies that the epoch was not in the dataset
        or a dictionary that represents the datapoint
    """
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = pull_data(url)
    list_of_data = find_data_point(data, "ndm", "oem", "body", "segment", "data", "stateVector")
    for i in list_of_data:
        if i["EPOCH"] == epoch:
            return i 
    return "error, epoch not found"


@app.route('/epochs/<epoch>/speed', methods=['GET'])
def get_specific_data_speed(epoch):
    """
    This function returns the instant speed at a specific datapoint
    
    Args:
        epoch (str): the epoch as a string
        
    Returns:
        either a string that documents that the epoch cannot be found, or the int instant speed
    """
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = pull_data(url)
    list_of_data = find_data_point(data, "ndm", "oem", "body", "segment", "data", "stateVector")
    for i in list_of_data:
        if i["EPOCH"] == epoch:
            return instantaneous_speed(float(i["X_DOT"]["#text"]), float(i["Y_DOT"]["#text"]), float(i["Z_DOT"]["#text"])) 
    return "error, epoch not found"

@app.route('/now', methods=['GET'])
def get_now_info():
    """
    This function returns the datapoint latest to the current time point
    
    Args:
        None
        
    Returns:
        A dictionary with the stateVectors and the instantaneous speed
    """
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = pull_data(url)
    list_of_data = find_data_point(data, "ndm", "oem", "body", "segment", "data", "stateVector")
    n = len(list_of_data)
    now = time.mktime(time.gmtime())
    mindisance = -1
    minindex = 0
    for i in range(n):
        latestdata = list_of_data[i]
        currtime = latestdata["EPOCH"]
        currepochtime = time.mktime(time.strptime(currtime, '%Y-%jT%H:%M:%S.%fZ'))
        
        if (now - currepochtime) < mindisance:
            minindex = i
    
    latestdatapoint = list_of_data[minindex]
    inst_speed= instantaneous_speed(float(latestdatapoint["X_DOT"]["#text"]), float(latestdatapoint["Y_DOT"]["#text"]), float(latestdatapoint["Z_DOT"]["#text"]))
    ret_dict = {
        "stateVectors": latestdatapoint,
        "inst_speed": inst_speed
    }
    return ret_dict

"""
Used Claude 3.5 to get the datetime strip function
prompts:
    1: 'how would I write a function to convert two times in the format of: 2025-048T12:00:00.000Z, to find the range of dates?'

Could not find information on how to strip the datetime formats in the XML dataset, so I used Claude to help with that, and ensure I could also add return functions
(Note: did not read the FAQS before running this command)
"""
    
def main():
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    content = pull_data(url)
    data = xmltodict.parse(content)


    
if __name__ == "__main__":
    # main()
    app.run(debug=True, host='0.0.0.0', port=5000)