from pprint import pprint

from basic_mongo import BasicMongo as mongo
from utils import utc_to_str


def main():
    db = mongo.get_db()
    log = mongo.get_day_value(db, 0)
    sensor = mongo.get_sensors(db)
    sensor = {s['_id']: s['name'] for s in sensor}
    pprint(["{} - {} - {}".format(utc_to_str(l['timestamp']), sensor[l['mac']], l['state']) for l in log])


if __name__ == '__main__':
    main()
