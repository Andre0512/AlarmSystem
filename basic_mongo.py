import logging
from datetime import timedelta, datetime

from bson.objectid import ObjectId
from pymongo.mongo_client import MongoClient

from secrets import MONGO

logger = logging.getLogger(__name__)


class BasicMongo:
    @staticmethod
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

    @staticmethod
    def get_names(db):
        sensors = db.sensors.find({})
        result = {}
        for s in sensors:
            group = s['groups'][0] if s['groups'] else "Sonstige"
            if group not in result:
                result[group] = {}
            result[group][s['_id']] = [s['name'], s['deconz_id']]
        return result

    @staticmethod
    def get_sensors(db):
        return sorted(db.sensors.find({}), key=lambda x: (x['groups'][0] if x['groups'] else x['name'], x['name']))

    @staticmethod
    def get_groups(db):
        groups = db.groups.find({})
        result = {str(r['_id']): r['name'] for r in groups}
        logger.debug(result)
        return result

    @staticmethod
    def get_group_sensors(db):
        result = {}
        groups = db.groups.find({})
        for group in groups:
            print(group['name'])
            result[str(group['_id'])] = [x['deconz_id'] for x in db.sensors.find({'groups': group['name']})]
        logger.debug(result)
        return result

    @staticmethod
    def add_group(db, group):
        try:
            db.groups.insert_one({'name': group})
            return True
        except Exception as e:
            logger.error(e)
            return False

    @staticmethod
    def check_groups(db):
        groups = list(set([l for g in [v['groups'] for v in db.sensors.find({})] for l in g]))
        logger.debug(groups)
        [db.groups.remove({'name': g['name']}) and logger.debug('Delete group ' + g['name']) for g in db.groups.find({})
         if g['name'] not in groups]

    @staticmethod
    def get_db():
        client = MongoClient(MONGO['HOST'], MONGO['PORT'])
        return client.alarm_system

    @staticmethod
    def key_exists(db, d_id, k):
        return k in db.sensors.find_one({'deconz_id': d_id})

    @staticmethod
    def get_one_sensor(db, d_id):
        return db.sensors.find_one({'deconz_id': d_id})

    @staticmethod
    def update_name(db, d_id, new):
        try:
            db.sensors.update_one({"deconz_id": d_id}, {"$set": {"name": new}})
            return True
        except Exception as e:
            logger.error(e)
            return False

    @staticmethod
    def add_sensor_group(db, sensor, id_new):
        print(id_new)
        new = db.groups.find_one({'_id': ObjectId(id_new)})['name']
        action = "$pull" if new in db.sensors.find_one({"deconz_id": sensor})['groups'] else "$addToSet"
        db.sensors.update_one({"deconz_id": sensor}, {action: {"groups": new}})

    @staticmethod
    def get_day_value(db, day, state=None):
        if not state:
            state = {"$exists": True}
        today = (datetime.now() + timedelta(days=day)).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return db.logs.find({"state": state, "timestamp": {"$gte": today, "$lt": tomorrow}})
