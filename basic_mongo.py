import logging

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
        result = db.sensors.find({})
        return {r['_id']: r['name'] for r in result}

    @staticmethod
    def get_db():
        client = MongoClient(MONGO['HOST'], MONGO['PORT'])
        return client.alarm_system

    @staticmethod
    def update_name(db, d_id, new):
        try:
            db.sensors.update_one({"deconz_id": d_id}, {"$set": {"name": new}})
            return True
        except Exception as e:
            logger.error(e)
            return False
