from pprint import pprint

import requests

from secrets import API_KEY, GATEWAY

URL = "http://{}/api/{}/sensors"


def get_sensors():
    r = requests.get(URL.format(GATEWAY, API_KEY))
    return r.json()


def get_models(sensors, sensor_type):
    return {k: v for k, v in sensors.items() if v["modelid"] in sensor_type}


def xxx(magnets):
    for k, v in magnets.items():
        print(v['name'], v['state']['open'])


def main():
    sensors = get_sensors()
    pprint(xxx(get_models(sensors, ["lumi.sensor_magnet.aq2"])))


if __name__ == "__main__":
    main()
