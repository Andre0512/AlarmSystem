#!/usr/bin/env python
import logging
import os
import sys

from telegram.ext.callbackqueryhandler import CallbackQueryHandler
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.filters import Filters
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.updater import Updater
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.keyboardbutton import KeyboardButton
from telegram.parsemode import ParseMode
from telegram.replykeyboardmarkup import ReplyKeyboardMarkup

from basic_mongo import BasicMongo as mongo
from secrets import TELEGRAM, DEBUG
from sensors import Magnet
from utils import get_local_time

if DEBUG:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format='%(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                        filename="{}/{}".format(os.path.dirname(os.path.realpath(__file__)), 'state_channel.log'))

logger = logging.getLogger(__name__)

KB = ["Sensoren"]
db = mongo.get_db()


def get_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton(button)] for button in KB], resize_keyboard=True)


def start(bot, update):
    update.message.reply_text('Hi!', reply_markup=get_keyboard())


def help(bot, update):
    update.message.reply_text('Help!')


def get_sensor_list():
    magnet = Magnet()
    magnets = magnet.get_full_list()
    return InlineKeyboardMarkup([[InlineKeyboardButton(v['name'], callback_data=v['id'])] for v in magnets.values()])


def get_sensor_info(update):
    magnet = Magnet()
    s = magnet.get_sensor(update.callback_query.data)
    status = ['geschlossen', 'offen ⚠️']
    battery = "{}%{}".format(s['config']['battery'], "" if s['config']['battery'] > 20 else " ⚠️")
    txt = "*{}*\nStatus: {}\nErreichbar: {}\nLetzter Kontakt: _{}_\nBatterie: {}\nTemperatur: {}°C\nTyp: _{}_\nID: `{}`"
    return txt.format(s['name'], status[int(s['state']['open'])], "✔️" if s['config']['reachable'] else "❌",
                      get_local_time(s['state']['lastupdated']), battery, s['config']['temperature'] / 100,
                      s['type'], s['uniqueid'])


def send_sensor_info(update):
    update.callback_query.message.edit_text(get_sensor_info(update), parse_mode=ParseMode.MARKDOWN)


def send_sensor_list(update):
    update.message.reply_text("Wähle einen Sensor aus:", reply_markup=get_sensor_list())


def echo(bot, update):
    if update.message.text in KB[0]:
        send_sensor_list(update)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def answer_callback(bot, update):
    update.callback_query.answer()
    send_sensor_info(update)


def main():
    updater = Updater(TELEGRAM["token2"])
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(CallbackQueryHandler(answer_callback))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
