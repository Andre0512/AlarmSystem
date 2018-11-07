#!/usr/bin/env python
import logging
import os
import sys

from telegram.error import TelegramError
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
                        filename="{}/{}".format(os.path.dirname(os.path.realpath(__file__)), 'log/alarm_bot.log'))

logger = logging.getLogger(__name__)

KB = ["Sensoren", "Scharf schalten"]
SENSOR_KB = {"sensor_rename": "✏️ Umbenennen", "sensor_add_group": "➕ Gruppe hinzufügen",
             "sensor_change_group": "🔄 Gruppe wechseln", "sensor_back": "⬅ ️Zurück"}
NEW_NAME = "Bitte neuen Namen für *{}* eingeben:"
ALARM_MODE = ["1️⃣ Totaler Alarm", "2️⃣ Innen Alarm", "3️⃣ Stummer Alarm", "⬅️ Zurück"]
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


def get_sensor_list(data="sensor.", active=None):
    active = [] if not active else active
    magnet = Magnet()
    magnets = magnet.get_full_list()
    result = []
    for v in magnets.values():
        text = ("❌ " if v['id'] in active else "") + v['name']
        result += [[InlineKeyboardButton(text, callback_data=data + v['id'])]]
    result = result + [[InlineKeyboardButton(text="Weiter ➡️", callback_data="arm_next")]] if active else result
    return InlineKeyboardMarkup(result)


def get_sensor_info(sensor, chat_data):
    magnet = Magnet()
    s = magnet.get_sensor(sensor)
    chat_data['name'] = s['name']
    status = ['geschlossen', 'offen ⚠️']
    battery = "{}%{}".format(s['config']['battery'], "" if s['config']['battery'] > 20 else " ⚠️")
    txt = "*{}*\nStatus: {}\nErreichbar: {}\nLetzter Kontakt: _{}_\nBatterie: {}\nTemperatur: {}°C\nTyp: _{}_\nID: `{}`"
    return txt.format(s['name'], status[int(s['state']['open'])], "✔️" if s['config']['reachable'] else "❌",
                      get_local_time(s['state']['lastupdated']), battery, s['config']['temperature'] / 100,
                      s['type'], s['uniqueid'])


def send_sensor_info(update, chat_data, sensor=None):
    sensor = str(update.data.split(".")[-1] if not sensor else sensor)
    try:
        update.message.edit_text(get_sensor_info(sensor, chat_data), parse_mode=ParseMode.MARKDOWN,
                                 reply_markup=get_sensor_keyboard(sensor))
    except TelegramError:
        update.message.reply_text(get_sensor_info(sensor, chat_data), parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=get_sensor_keyboard(sensor))


def rename_sensor(update, value, chat_data):
    msg_id = update.callback_query.message.reply_text(NEW_NAME.format(chat_data['name']), reply_markup=ForceReply(),
                                                      parse_mode=ParseMode.MARKDOWN)['message_id']
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Abbrechen", callback_data="sensor_rename_abort.{}-{}".format(str(msg_id), value))]])
    update.callback_query.message.edit_text(get_sensor_info(value, chat_data), parse_mode=ParseMode.MARKDOWN,
                                            reply_markup=kb)


def abort_rename_sensor(bot, update, value, chat_data):
    msg_id, sensor = value.split('-')
    bot.delete_message(chat_id=update.callback_query.message.chat_id, message_id=msg_id)
    send_sensor_info(update.callback_query, chat_data, sensor=sensor)


def send_sensor_list(update, edit=False):
    send = update.message.edit_text if edit else update.message.reply_text
    send("Wähle einen Sensor aus:", reply_markup=get_sensor_list())


def update_sensor_name(sensor, update, chat_data):
    if Magnet.update_name(sensor, update.message.text) and mongo.update_name(db, chat_data["name"],
                                                                             update.message.text):
        send_sensor_info(update, chat_data, sensor=sensor)
    else:
        update.message.reply_text("Etwas ist schief gelaufen...")


def arm_system(update):
    update.message.reply_text("Wähle Sensor(en) und/oder Gruppe(n) aus:", reply_markup=get_sensor_list(data="arm."))


def echo(bot, update, chat_data):
    if update.message.reply_to_message:
        if update.message.reply_to_message.text == NEW_NAME.format(chat_data['name']):
            update_sensor_name(chat_data["id"], update, chat_data)
    if update.message.text in KB[0]:
        send_sensor_list(update)
    if update.message.text in KB[1]:
        arm_system(update)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def get_active(chat_data, value):
    if 'activate' in chat_data:
        if value in chat_data['activate']:
            chat_data['activate'].remove(value)
            return
        chat_data["activate"] = chat_data["activate"] + [value]
        return
    chat_data['activate'] = [value]
    return


def answer_callback(bot, update, chat_data):
    update.callback_query.answer()
    cmd, value = update.callback_query.data.split('.')
    if cmd in ["sensor"]:
        send_sensor_info(update.callback_query, chat_data)
    elif cmd in ["arm"]:
        get_active(chat_data, value)
        print(chat_data)
        kb = get_sensor_list(data="arm.", active=chat_data["activate"])
        update.callback_query.message.edit_text("Wähle Sensor(en) und/oder Gruppe(n) aus:", reply_markup=kb)
    elif cmd in ["sensor_back"]:
        send_sensor_list(update.callback_query, edit=True)
    elif cmd in ["sensor_rename"]:
        rename_sensor(update, value, chat_data)
        chat_data["id"] = value
    elif cmd in ["sensor_rename_abort"]:
        abort_rename_sensor(bot, update, value, chat_data)


def main():
    updater = Updater(TELEGRAM["token2"])
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(MessageHandler(Filters.text, echo, pass_chat_data=True))
    dp.add_handler(CallbackQueryHandler(answer_callback, pass_chat_data=True))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
