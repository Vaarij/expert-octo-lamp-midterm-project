# Flask API ISS Dataset Tracking Interpreter

## Introduction
This folder is an extension to add a web component to the iss_tracker.py, allowing users to access formatted data from anywhere once the API is running.
This folder should contain two python files, iss_tracker.py: the file to read and interpret information about the ISS dataset, and test_iss_tracker.py: a file to test the functions in iss_tracker.py. In addition to this, the folder should contain a docker file which builds a container to build a container that contains the required libraries

## Downloading the data:
The data should be accessible through the requests folder, which GETS from "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml". If this does not work, the user should download the data from the link, add it to the root of homework04/ folder, then use the read_data_from_xml() with the filepath to the local xml file.

### Notes
Outside of the standard libraries this file needs to import Flask, typing, logging, requests, pytest using:
```pip3 install --user Flask typing logging requests pytest```

Output from the iss_tracker.py:
The Flask API can be setup with ```docker run --rm -v $PWD:/data broccolisoup/flask_iss_tracker:1.3 python3 /code/iss_tracker.py``` or, if the Docker won't run, ```flask --app iss_tracker --debug runpy```. 
Output from the iss_tracker will indicate key information about the file, including the time range, which should be 15 days, the start date and end dates of the tracking data, information about the latest recorded timestamp, the average speed from the past 15 days

Accessing specific routes:
1. "/epochs", "GET". The following function gets all the data points in the Epochs section. The route also allows for limits and offsets. which can be added after /epochs/.
2. "/epochs/'epoch'", "GET". The following function gets the data for a specific id, which should be in epoch.
3. "/epochs/'epoch'/speed", "GET". This function gets the instant speed at a specific id.
4. "/now", "GET". The function gets the latest data point, including the time and the instantaneous speed.

The user can access this data by running the following command, it is good practice to run this in another terminal. 

```curl 127.0.0.0.0:5000/```, and adding the routes after the backslash. 


### Building the DockerFile:
The docker image can be built with the command: ```docker run --rm -v $PWD:/data broccolisoup/flask_iss_tracker:1.3 python3 /code/iss_tracker.py```
To rebuild the docker image, we can use the commnd ```docker build -t broccolisoup/flask_iss_tracker:1.3 -f DockerFile-gen ./```

### Note on AI within the project:
The following parts within the project was written with Claude 3.5:
- get_time_range in iss_tracker.py was written with the following prompt: "how would I write a function to convert two times in the format of: 2025-048T12:00:00.000Z, to find the range of dates?" Claude was used to simplify the use of the time library. (Note, I could not find the instructions on how to implement the time library in the notes before coding, so I used Claude. I did modify the function using the FAQ directions, but I am keeping the citation because I have not modified all of the code written by Claude)
- The find data point was also edited using Claude 3.7, which was able to identify more errors that can be raised. 

### Additional Information
No tests were written for the read_data_from_xml(), as it is a rudimentary file written as a fail-safe without too much.