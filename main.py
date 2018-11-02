import logging
import os
import sys
from datetime import datetime
from time import sleep

import requests
from pymongo import MongoClient

from secrets import API_KEY, GATEWAY, MONGO, DEBUG

URL = "http://{}/api/{}/sensors"

if DEBUG:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format='%(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        filename="{}/{}".format(os.path.dirname(os.path.realpath(__file__)), 'AlarmSystem.log'))


class Sensor:
    def __init__(self, sensor_type):
        self.__type = sensor_type

    def __get_sensors(self):
        r = requests.get(URL.format(GATEWAY, API_KEY))
        logging.debug(r.text)
        return r.json()

    def __get_models(self):
        return {k: v for k, v in self.__get_sensors().items() if v["modelid"] in self.__type}

    def __get_state(self):
        return {
            v['uniqueid']: {'state': v['state']['open'], 'lastupdated': v['state']['lastupdated']}
            for
            k, v in self.__get_models().items()}

    def __get_full_state(self):
        return {v['uniqueid']: v for k, v in self.__get_models().items()}

    def get_list(self):
        return self.__get_state()

    def get_full_list(self):
        return self.__get_full_state()


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
    x, names = {}, {}
    # Try to read state from Database
    for sensor in get_last(db):
        x[sensor['_id']] = {}
        x[sensor['_id']]['state'] = sensor['last']['state']
    # Read data from current request
    for sensor, value in new.items():
        if sensor not in x:
            if not db.sensors.count_documents({"_id": sensor}):
                logging.info("Create new sensor " + sensor)
                db.sensors.insert_one({"_id": sensor, 'name': value['name']})
            x[sensor] = {'state': value['state']['open']}
        names.update({sensor: value['name']})
    return names, x


def get_db():
    client = MongoClient(MONGO['HOST'], MONGO['PORT'])
    return client.alarm_system


def main():
    logging.info("Programm started")
    magnet = Magnet()
    magnets = magnet.get_full_list()
    db = get_db()
    names, old = get_last_state(db, magnets)
    while True:
        try:
            sleep(0.5)
            magnets = magnet.get_list()
            for sensor in magnets:
                if not magnets[sensor]['state'] == old[sensor]['state']:
                    db.logs.insert_one({'mac': sensor, 'state': magnets[sensor]['state'],
                                        'timestamp': datetime.strptime(magnets[sensor]['lastupdated'],
                                                                       "%Y-%m-%dT%H:%M:%S")})
                    logging.info("{} - {} - {}".format(magnets[sensor]['lastupdated'], names[sensor],
                                                       "geöffnet" if magnets[sensor]["state"] else "geschlossen"))
            old = magnets
        except Exception as e:
            logging.error(e)


if __name__ == "__main__":
    main()
