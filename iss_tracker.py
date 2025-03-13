#!/usr/bin/env python3
import requests
import logging
import xmltodict
import time
from typing import Tuple, List
import math
from flask import Flask, request
import json
import redis
from geopy.geocoders import Nominatim
from astropy import coordinates
from astropy import units
from astropy.time import Time

app = Flask(__name__)

def get_redis_client():
    return redis.Redis(host='redis-db', port=6379, db=0)

rd = get_redis_client()
geocoder = Nominatim(user_agent='iss_tracker')

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
                    return None 
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

def convert_to_dict_with_epoch_keys(data):
    """
    This function takes in some data and converts it into a dict with the epochs as the key that can uploaded into the redis database
    
    Args:
        data (List): some list of data in the format of epoch, x, y, z, xdot, ydot, zdot
        
    Returns:
        a list of json objects with the epochs as keys
    """
    retList = []
    for i in data:
        tempJson = {i["EPOCH"] : {
            "X" : i["X"]["#text"],
            "Y" : i["Y"]["#text"],
            "Z" : i["Z"]["#text"],
            "X_DOT" : i["X_DOT"]["#text"],
            "Y_DOT" : i["Y_DOT"]["#text"],
            "Z_DOT" : i["Z_DOT"]["#text"]
        }}
        retList.append(tempJson)
        
    return retList

def check_and_update_redis_data():
    """
    The following function attempts to check the redis database for data, and will either update it with the newest data or add the data in
    
    Args:
        None
    
    Returns:
        None
    """
    
    try:
        existing_data = rd.get("k")
        
        new_data = pull_data("https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml")
        state_vectors = find_data_point(new_data, "ndm", "oem", "body", "segment", "data", "stateVector")
        
        if not state_vectors:
            logging.error("Failed to retrieve state vectors from NASA API")
            return
            
        formatted_data = convert_to_dict_with_epoch_keys(state_vectors)
        
        if not existing_data:
            rd.set("k", json.dumps(formatted_data))
            logging.info("Added initial data to Redis")
            return
            
        try:
            existing_data_list = json.loads(existing_data)
            latest_epoch = list(existing_data_list[-1].keys())[0]
            
            for i, item in enumerate(state_vectors):
                if item["EPOCH"] == latest_epoch and (i < len(state_vectors) - 1):
                    new_entries = convert_to_dict_with_epoch_keys(state_vectors[i+1:])
                    updated_data = existing_data_list + new_entries
                    rd.set("k", json.dumps(updated_data))
                    logging.info(f"Updated Redis with {len(new_entries)} new entries")
                    return
                    
            logging.info("No new data to add")
            
        except Exception as e:
            logging.error(f"Error updating data: {str(e)}")
            rd.set("k", json.dumps(formatted_data))
            
    except Exception as e:
        logging.error(f"Error in check_and_update_redis_data: {str(e)}")

@app.route('/epochs', methods=['GET'])
def get_all_data():
    """
    The following function gets all the data points in the epochs section
    
    Args:
        None
    
    Returns:
        A list of all the data
    """
    try:
        data_json = rd.get('k')
        if not data_json:
            return "No data found in Redis"
            
        list_of_data = json.loads(data_json)
        
        limit = int(request.args.get('limit', len(list_of_data)))
        offset = int(request.args.get('offset', 0))
        
        if offset >= len(list_of_data):
            return "Offset exceeds data length"
            
        end_index = min(offset + limit, len(list_of_data))
        return json.dumps(list_of_data[offset:end_index])
        
    except Exception as e:
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
    try:
        data_json = rd.get('k')
        if not data_json:
            return "No data found in Redis"
            
        list_of_data = json.loads(data_json)
        
        for item in list_of_data:
            for key, value in item.items():
                if key == epoch:
                    return value
        
        return "Epoch not found"
        
    except Exception as e:
        return str(e)


@app.route('/epochs/<epoch>/speed', methods=['GET'])
def get_specific_data_speed(epoch):
    """
    This function returns the instant speed at a specific datapoint
    
    Args:
        epoch (str): the epoch as a string
        
    Returns:
        either a string that documents that the epoch cannot be found, or the int instant speed
    """
    list_of_data = rd.get('k')
    for key, value in list_of_data:
        if key == epoch:
            return instantaneous_speed(float(value["X_DOT"]), float(value["Y_DOT"]), float(value["Z_DOT"])) 
    return "error, epoch not found"

def convert_xyz_loc(epoch:str, x:float,y:float,z:float):
    """
    This function takes some xyz and converts it to a latitude and longitude
    
    Args:
        epoch (str): the string with the date-time
        x, y, z (float): the x, y, z, position values
    
    Returns:
        lat, lon, height (floats): the latitude, longitude, height of the iss
    """
    
    this_epoch=time.strftime('%Y-%m-%d %H:%m:%S', time.strptime(epoch[:-5], '%Y-%jT%H:%M:%S'))

    cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
    gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
    itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
    loc = coordinates.EarthLocation(*itrs.cartesian.xyz)
    
    return loc.lat.value, loc.lon.value, loc.height.value

@app.route('/epochs/<epoch>/location', methods=['GET'])
def get_specific_data_location(epoch):
    """
    This function returns the location at a specific datapoint
    
    Args:
        epoch (str): the epoch as a string
        
    Returns:
        either a string that documents that the epoch cannot be found, or the string location
    """
    list_of_data = rd.get('k')
    for key, value in list_of_data:
        if key == epoch:
            lat,lon, height = convert_xyz_loc(key, float(value["X"]), float(value["Y"]), float(value["Z"]))
            geoloc = geocoder.reverse((lat, lon), zoom=15, language='en')
            return geoloc 
    return "error, epoch not found"

@app.route('/now', methods=['GET'])
def get_now_info():
    """
    This function returns the datapoint latest to the current time point
    
    Args:
        None
        
    Returns:
        A dictionary with the stateVectors, the instantaneous speed, and the location
    """
    list_of_data = rd.get("k")
    n = len(list_of_data)
    now = time.mktime(time.gmtime())
    mindisance = -1
    minindex = 0
    i = 0
    minepoch = "-1"
    for key, value in list_of_data:
        currepochtime = time.mktime(time.strptime(key, '%Y-%jT%H:%M:%S.%fZ'))
        
        if (now - currepochtime) < mindisance:
            minindex = i
            minepoch = currepochtime
        
        i += 1
    
    latestdatapoint = list_of_data[minindex][minepoch]
    inst_speed= instantaneous_speed(float(latestdatapoint["X_DOT"]), float(latestdatapoint["Y_DOT"]), float(latestdatapoint["Z_DOT"]))
    lat,lon, height = convert_xyz_loc(key, float(latestdatapoint["X"]), float(latestdatapoint["Y"]), float(latestdatapoint["Z"]))
    geoloc = geocoder.reverse((lat, lon), zoom=15, language='en')
    ret_dict = {
        "stateVectors": latestdatapoint,
        "inst_speed": inst_speed,
        "location" : geoloc
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
    check_and_update_redis_data()
    print("Checked and added data")


    
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)