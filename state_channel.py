import logging
import os
import sys
from datetime import datetime, timedelta
from pprint import pprint

import fhem as fhem
from telegram.bot import Bot
from telegram.ext.callbackqueryhandler import CallbackQueryHandler
from telegram.ext.updater import Updater
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.parsemode import ParseMode

from basic_mongo import BasicMongo as mongo
from secrets import TELEGRAM, DEBUG, FHEM2, FHEM_DEVICES

if DEBUG:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format='%(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        filename="{}/{}".format(os.path.dirname(os.path.realpath(__file__)), 'log/state_channel.log'))
logger = logging.getLogger(__name__)


def parse_message():
    text = []
    db = mongo.get_db()
    fh = fhem.Fhem(FHEM2['server'], port=FHEM2['port'], protocol=FHEM2['protocol'], loglevel=99,
                   username=FHEM2['username'], password=FHEM2['password'])
    state = {state['_id']: [state['last']['state'], state['last']['timestamp']] for state in mongo.get_last(db)}
    for idx, v in enumerate(fh.get_readings('state', filters={'subType': 'threeStateSensor'}).values()):
        state['schuppen-{}'.format(idx)] = [True if v['Value'] == 'open' else False, v['Time']]
    now = datetime.utcnow()
    groups = mongo.get_names(db)
    groups.update(FHEM_DEVICES)
    for group, x in sorted(groups.items()):
        text.append("\n*{}*".format(group))
        for s_id, name in sorted(x.items(), key=lambda x: x[1][0]):
            name = "*{}*".format(name[0]) if (state[s_id][1] + timedelta(minutes=1)) > now else name[0]
            text.append("{} {}".format("🔴" if state[s_id][0] else "🔵", name))
    text.append("\n_Aktualisiert: {}_".format(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")))
    return "\n".join(text)


def get_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Aktualisieren", callback_data="refresh")]])


def send(bot=None):
    if not bot:
        bot = Bot(TELEGRAM["token"])
    bot.edit_message_text(chat_id=TELEGRAM["chat_id"], message_id=TELEGRAM["msg_id"], text=parse_message(),
                          parse_mode=ParseMode.MARKDOWN, reply_markup=get_keyboard())


def answer_callback(bot, update):
    update.callback_query.answer()
    if update.callback_query.data == "refresh":
        send(bot)
        logger.info(
            "Update - {} - {}".format(update.callback_query.from_user.first_name, update.callback_query.from_user.id))


def main():
    updater = Updater(TELEGRAM["token"])
    dp = updater.dispatcher

    dp.add_handler(CallbackQueryHandler(answer_callback))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    if True:
        if len(sys.argv) > 1 and sys.argv[1] == "1":
            send()
        else:
            main()
    try:
        pass
    except Exception as e:
        logger.error(e)
