import requests

from secrets import API_KEY, GATEWAY

URL = "http://{}/api/{}/sensors"


class Sensor:
    def __init__(self, sensor_type):
        self.__type = sensor_type
        self.__sensors = self.__get_models()

    def __get_sensors(self):
        r = requests.get(URL.format(GATEWAY, API_KEY))
        return r.json()

    def __get_models(self):
        return {k: v for k, v in self.__get_sensors().items() if v["modelid"] in self.__type}

    def __get_state(self):
        return {v['name']: v['state']['open'] for k, v in self.__sensors.items()}

    def get_list(self):
        return self.__get_state()


class Magnet(Sensor):
    def __init__(self):
        super().__init__(["lumi.sensor_magnet.aq2"])


def main():
    magnet = Magnet()
    print(magnet.get_list())


if __name__ == "__main__":
    main()
