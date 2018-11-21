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
    state = {state['_id']: state['last']['state'] for state in mongo.get_last(db)}
    for group, x in sorted(mongo.get_names(db).items()):
        text.append("\n*{}*".format(group))
        for s_id, name in sorted(x.items(), key=lambda x: x[1][0]):
            text.append("{} {}".format("🔴" if state[s_id] else "🔵", name[0]))
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
