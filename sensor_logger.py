import logging
import os
import sys
from datetime import datetime
from time import sleep

from basic_mongo import BasicMongo as mongo
from secrets import DEBUG
from sensors import Magnet

if DEBUG:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format='%(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        filename="{}/{}".format(os.path.dirname(os.path.realpath(__file__)), 'log/sensor_logger.log'))
logger = logging.getLogger(__name__)


def get_last_state(db, new):
    x, names = {}, {}
    # Try to read state from Database
    for sensor in mongo.get_last(db):
        x[sensor['_id']] = {}
        x[sensor['_id']]['state'] = sensor['last']['state']
    # Read data from current request
    for sensor, value in new.items():
        if sensor not in x:
            if not db.sensors.count_documents({"_id": sensor}):
                logger.info("Create new sensor {} ({})".format(sensor, value['name']))
                db.sensors.insert_one({"_id": sensor, 'name': value['name']})
            x[sensor] = {'state': value['state']['open']}
        names.update({sensor: value['name']})
    return names, x


def main():
    logger.info("Programm started")
    magnet = Magnet()
    magnets = magnet.get_full_list()
    db = mongo.get_db()
    names, old = get_last_state(db, magnets)
    while True:
        sleep(0.5)
        magnets = magnet.get_list()
        for sensor in magnets:
            if not magnets[sensor]['state'] == old[sensor]['state']:
                db.logs.insert_one({'mac': sensor, 'state': magnets[sensor]['state'],
                                    'timestamp': datetime.strptime(magnets[sensor]['lastupdated'],
                                                                   "%Y-%m-%dT%H:%M:%S")})
                logger.info("{} - {}".format(names[sensor], "geöffnet" if magnets[sensor]["state"] else "geschlossen"))
        old = magnets


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logger.error(e)
