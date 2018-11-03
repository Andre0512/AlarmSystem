#!/usr/bin/env python
import logging
import os
import sys

from telegram.ext.callbackqueryhandler import CallbackQueryHandler
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.filters import Filters
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.updater import Updater
from telegram.forcereply import ForceReply
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
                        filename="{}/{}".format(os.path.dirname(os.path.realpath(__file__)), 'alarm_bot.log'))

logger = logging.getLogger(__name__)

KB = ["Sensoren"]
SENSOR_KB = {"sensor_rename": "✏️ Umbenennen", "sensor_add_group": "➕ Gruppe hinzufügen",
             "sensor_change_group": "🔄 Gruppe wechseln", "sensor_back": "⬅ ️Zurück"}
db = mongo.get_db()


def get_sensor_keyboard(data):
    stri = SENSOR_KB.copy()
    stri.pop("sensor_add_group" if True else "sensor_change_group", None)
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(v, callback_data="{}.{}".format(k, data))] for k, v in stri.items()])


def get_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton(button)] for button in KB], resize_keyboard=True)


def start(bot, update):
    update.message.reply_text('Hi!', reply_markup=get_keyboard())


def help(bot, update):
    update.message.reply_text('Help!')


def get_sensor_list():
    magnet = Magnet()
    magnets = magnet.get_full_list()
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(v['name'], callback_data="sensor." + v['id'])] for v in magnets.values()])


def get_sensor_info(sensor):
    magnet = Magnet()
    s = magnet.get_sensor(sensor)
    status = ['geschlossen', 'offen ⚠️']
    battery = "{}%{}".format(s['config']['battery'], "" if s['config']['battery'] > 20 else " ⚠️")
    txt = "*{}*\nStatus: {}\nErreichbar: {}\nLetzter Kontakt: _{}_\nBatterie: {}\nTemperatur: {}°C\nTyp: _{}_\nID: `{}`"
    return txt.format(s['name'], status[int(s['state']['open'])], "✔️" if s['config']['reachable'] else "❌",
                      get_local_time(s['state']['lastupdated']), battery, s['config']['temperature'] / 100,
                      s['type'], s['uniqueid'])


def send_sensor_info(update, sensor=None):
    sensor = str(update.callback_query.data.split(".")[-1] if not sensor else sensor)
    print(sensor)
    update.callback_query.message.edit_text(get_sensor_info(sensor), parse_mode=ParseMode.MARKDOWN,
                                            reply_markup=get_sensor_keyboard(sensor))


def rename_sensor(update, value):
    msg_id = update.callback_query.message.reply_text("Bitte neuen Namen eingeben:", reply_markup=ForceReply())[
        'message_id']
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Abbrechen", callback_data="sensor_rename_abort.{}-{}".format(str(msg_id), value))]])
    update.callback_query.message.edit_text(get_sensor_info(value), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


def abort_rename_sensor(bot, update, value):
    msg_id, sensor = value.split('-')
    bot.delete_message(chat_id=update.callback_query.message.chat_id, message_id=msg_id)
    send_sensor_info(update, sensor)


def send_sensor_list(update):
    update.message.reply_text("Wähle einen Sensor aus:", reply_markup=get_sensor_list())


def echo(bot, update):
    if update.message.text in KB[0]:
        send_sensor_list(update)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def answer_callback(bot, update):
    update.callback_query.answer()
    cmd, value = update.callback_query.data.split('.')
    if cmd in ["sensor"]:
        send_sensor_info(update)
    elif cmd in ["sensor_back"]:
        send_sensor_list(update.callback_query)
    elif cmd in ["sensor_rename"]:
        rename_sensor(update, value)
    elif cmd in ["sensor_rename_abort"]:
        abort_rename_sensor(bot, update, value)


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
