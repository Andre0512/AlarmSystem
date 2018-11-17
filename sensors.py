import logging

import requests

from secrets import GATEWAY, API_KEY

URL = "http://{}/api/{}/sensors"

logger = logging.getLogger(__name__)


class Sensor:
    def __init__(self, sensor_type):
        self.__type = sensor_type

    def __get_sensors(self, sensor=""):
        r = requests.get(URL.format(GATEWAY, API_KEY) + sensor)
        logger.debug(r.text)
        return r.json()

    def __get_models(self):
        return {k: v for k, v in self.__get_sensors().items() if v["modelid"] in self.__type}

    def __get_state(self):
        return {
            v['uniqueid']: {'state': v['state']['open'], 'lastupdated': v['state']['lastupdated']}
            for
            k, v in self.__get_models().items()}

    def __get_full_state(self):
        return {v['uniqueid']: {**v, 'id': k} for k, v in self.__get_models().items()}

    def get_list(self):
        return self.__get_state()

    def get_full_list(self):
        return self.__get_full_state()

    def get_sensor(self, sid):
        logger.debug('Sensor ID - ' + sid)
        return self.__get_sensors("/" + sid)

    @staticmethod
    def update_name(sid, new):
        r = requests.put("{}/{}".format(URL.format(GATEWAY, API_KEY), sid), json={"name": new})
        return r.status_code == 200


class Magnet(Sensor):
    def __init__(self):
        super().__init__(["lumi.sensor_magnet.aq2"])
