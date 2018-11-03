import logging
import os
import sys
from datetime import datetime

from telegram.bot import Bot
from telegram.ext.callbackqueryhandler import CallbackQueryHandler
from telegram.ext.updater import Updater
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.parsemode import ParseMode

from basic_mongo import BasicMongo as mongo
from secrets import TELEGRAM, DEBUG

if DEBUG:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format='%(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        filename="{}/{}".format(os.path.dirname(os.path.realpath(__file__)), 'log/state_channel.log'))
logger = logging.getLogger(__name__)


def parse_message():
    text = []
    db = mongo.get_db()
    names = mongo.get_names(db)
    for state in mongo.get_last(db):
        text.append("{} {}".format("🔴" if state['last']['state'] else "🔵", names[state['_id']]))
    text.append("_Aktualisiert: {}_".format(datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")))
    return "\n".join(text)


def get_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Aktualisieren", callback_data="refresh")]])


def send(bot=None):
    if not bot:
        bot = Bot(TELEGRAM["token"])
    bot.edit_message_text(chat_id=TELEGRAM["chat_id"], message_id=TELEGRAM["msg_id"], text=parse_message(),
                          parse_mode=ParseMode.MARKDOWN, timeout=60, reply_markup=get_keyboard())


def answer_callback(bot, update):
    if update.callback_query.data == "refresh":
        send(bot)
        logger.info(
            "Update - {} - {}".format(update.callback_query.from_user.first_name, update.callback_query.from_user.id))
    update.callback_query.answer()


def main():
    updater = Updater(TELEGRAM["token"])
    dp = updater.dispatcher

    dp.add_handler(CallbackQueryHandler(answer_callback))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "1":
            send()
        else:
            main()
    except Exception as e:
        logger.error(e)
