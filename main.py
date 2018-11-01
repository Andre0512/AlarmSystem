import logging
import sys
from datetime import datetime
from time import sleep

import requests
from pymongo import MongoClient

from secrets import API_KEY, GATEWAY, MONGO

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


def get_last(db):
    return db.logs.aggregate(
        [
            {'$sort': {'mac': 1, 'timestamp': 1}},
            {
                '$group':
                    {
                        '_id': '$mac',
                        'last': {'$last': '$$ROOT'}
                    }
            }
        ]
    )


def get_last_state(db, new):
    x = {}
    for sensor in get_last(db):
        x[sensor['_id']] = {}
        x[sensor['_id']]['state'] = sensor['last']['state']
    for sensor, value in new.items():
        if sensor not in x:
            if not db.sensors.count_documents({"_id": sensor}):
                db.sensors.insert_one({"_id": sensor})
            x[sensor] = value
    return x


def get_db():
    client = MongoClient(MONGO['HOST'], MONGO['PORT'])
    return client.alarm_system


def main():
    magnet = Magnet()
    magnets = magnet.get_list()
    db = get_db()
    old = get_last_state(db, magnets)
    while True:
        sleep(0.5)
        magnets = magnet.get_list()
        for sensor in magnets:
            if not magnets[sensor]['state'] == old[sensor]['state']:
                db.logs.insert_one({'mac': sensor, 'state': magnets[sensor]['state'],
                                    'timestamp': datetime.strptime(magnets[sensor]['lastupdated'],
                                                                   "%Y-%m-%dT%H:%M:%S")})
                logging.info("{} - {} - {}".format(magnets[sensor]['lastupdated'], sensor,
                                                   "geöffnet" if magnets[sensor]["state"] else "geschlossen"))
        old = magnets


if __name__ == "__main__":
    main()
