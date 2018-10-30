import logging
import sys
from datetime import datetime
from time import sleep

import requests
from pymongo import MongoClient

from secrets import API_KEY, GATEWAY

URL = "http://{}/api/{}/sensors"

logging.basicConfig(level=logging.INFO, stream=sys.stdout)


class Sensor:
    def __init__(self, sensor_type):
        self.__type = sensor_type

    def __get_sensors(self):
        r = requests.get(URL.format(GATEWAY, API_KEY))
        return r.json()

    def __get_models(self):
        return {k: v for k, v in self.__get_sensors().items() if v["modelid"] in self.__type}

    def __get_state(self):
        return {
            v['uniqueid']: {'state': v['state']['open'], 'lastupdated': v['state']['lastupdated'], 'name': v['name']}
            for
            k, v in self.__get_models().items()}

    def get_list(self):
        return self.__get_state()


class Magnet(Sensor):
    def __init__(self):
        super().__init__(["lumi.sensor_magnet.aq2"])


def get_last_state(db, new):
    x = {}
    for sensor in db.sensors.find({}):
        x[sensor['_id']] = {}
        if 'current' in sensor:
            x[sensor['_id']]['state'] = sensor['current']
        elif sensor['_id'] in new:
            x[sensor['_id']]['state'] = new[sensor['_id']]['state']
    for sensor, value in new.items():
        if sensor not in x:
            db.sensors.insert_one({"_id": sensor})
            x[sensor] = value
    return x


def get_db():
    client = MongoClient('localhost', 27017)
    return client.alarm_system


y = {
    "xxx": {
        "state": "njnjononokn",
        "timestamp": "7060976-96-8"
    }
}
x = {
    "sensors": [
        {
            "_id": "xxx",
            "current": True,
            "log": [
                {
                    "timestamp": "7060976-96-8",
                    "state": "njnjononokn"
                }
            ]
        }
    ]
}


def main():
    magnet = Magnet()
    magnets = magnet.get_list()
    db = get_db()
    old = get_last_state(db, magnets)
    while True:
        for sensor in magnets:
            if not magnets[sensor]['state'] == old[sensor]['state']:
                db.sensors.update_one({"_id": sensor},
                                      {'$addToSet': {'log': {'state': magnets[sensor]['state'],
                                                             'timestamp': datetime.strptime(
                                                                 magnets[sensor]['lastupdated'],
                                                                 "%Y-%m-%dT%H:%M:%S")}}})
                db.sensors.update_one({"_id": sensor}, {'$set': {'current': magnets[sensor]['state']}})
                logging.info("{} - {} - {}".format(magnets[sensor]['lastupdated'], sensor,
                                                   "geöffnet" if magnets[sensor]["state"] else "geschlossen"))
        old = magnets
        sleep(1)
        magnets = magnet.get_list()


if __name__ == "__main__":
    main()
