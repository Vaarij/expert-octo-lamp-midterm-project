import pytest
import requests
from iss_tracker import pull_data, find_data_point, instantaneous_speed

response_general_epoch = requests.get('http://127.0.0.1:5000/epochs')
limit_general_epoch = requests.get('http://127.0.0.1:5000/epochs?limit=10')
response_epoch_now = requests.get('http://127.0.0.1:5000/now')
specific_epoch = "2025-074T11:34:54.000Z"
response_specific_epoch = requests.get('http://127.0.0.1:5000/epochs/'+specific_epoch)
response_specific_epoch_speed = requests.get('http://127.0.0.1:5000/epochs/'+specific_epoch+"/speed")

def test_pull_data():
    url = "https://github.com/aqw1Z9463"
    with pytest.raises(ValueError):
        pull_data(url)
    

def test_find_data_point():
    data = {
        "name": "xQXxLHuVI",
        "preferences": {
            "color": "purple",
            "likes": [
            "7Fu"
            ]
        },
        "history": [
            {
            "date": "2014-02-07",
            "action": "login"
            },
            {
            "date": "2021-07-24",
            "action": "delete"
            },
            {
            "date": "2023-04-04",
            "action": "delete"
            }
        ]
    }
    
    assert find_data_point(data, "name") == "xQXxLHuVI"
    assert find_data_point(data, "preferences", "color") == "purple"
    
    with pytest.raises(AttributeError):
        find_data_point(data, "name", "id")
    
    
def test_instant_speed():
    velocities = [(-2.5, 3.1, 1.7), (4.8, -2.2, 0.9), (1.2, 1.2, -3.4), (-3.7, 0.0, 2.1), (5.0, -1.8, -2.3)]
    speeds = [4.330127018922194, 5.3563046963368315, 3.8, 4.254409477236529, 5.790509476721371]
    for i in range(len(velocities)):
        (x,y,z) = velocities[i]
        assert instantaneous_speed(x,y,z) == speeds[i]
        
def test_epoch_gen():
    assert response_general_epoch.status_code == 200
    assert isinstance(response_general_epoch.json(), list) == True

def test_specific_epoch():
    assert response_specific_epoch.status_code == 200
    assert isinstance(response_specific_epoch.json(), dict) == True

def test_now():
    assert response_epoch_now.status_code == 200
    assert isinstance(response_epoch_now.json(), dict) == True
    
def test_limit():
    assert limit_general_epoch.status_code == 200
    assert isinstance(limit_general_epoch.json(), list) == True
    assert len(limit_general_epoch.json()) == 10