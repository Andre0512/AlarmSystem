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
SENSOR_KB = {"sensor_rename": "✏️ Umbenennen",
             "sensor_manage_group": "👥 Gruppen verwalten", "sensor_back": "⬅ ️Zurück"}
NEW_NAME = "Bitte neuen Namen für *{}* eingeben:"
NEW_GROUP = "Wie soll die neue Gruppe heißen?"
ALARM_MODE = {"arm_mode.1": "1️⃣ Totaler Alarm", "arm_mode.2": "2️⃣ Innen Alarm", "arm_mode.3": "3️⃣ Stummer Alarm",
              "arm_back.": "⬅️ Zurück"}
CHOOSE_GROUPS = "Wähle Gruppen für *{}* aus"
db = mongo.get_db()


def get_sensor_keyboard(data):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(v, callback_data="{}.{}".format(k, data))] for k, v in SENSOR_KB.items()])


def get_alarm_mode_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton(v, callback_data=k)] for k, v in ALARM_MODE.items()])


def get_group_keyboard(sensor):
    db = mongo.get_db()
    groups = mongo.get_groups(db)
    current = mongo.get_one_sensor(db, sensor)['groups']
    groups = {"group." + k: "{}️⃣ {}".format(str(current.index(v) + 1), v) if v in current else v for k, v in
              groups.items()}
    groups['group_add.'] = "➕ Gruppe erstellen"
    groups['group_manage_back.{}'.format(sensor)] = "⬅️ Zurück"
    return InlineKeyboardMarkup([[InlineKeyboardButton(v, callback_data=k)] for k, v in groups.items()])


def get_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton(button)] for button in KB], resize_keyboard=True)


def start(bot, update):
    update.message.reply_text('Hi!', reply_markup=get_keyboard())


def help(bot, update):
    update.message.reply_text('Help!')


def get_sensor_list(data="sensor.", chat_data=None):
    chat_data = {} if not chat_data else chat_data
    result = []
    for v in mongo.get_sensors(mongo.get_db()):
        group = v['groups'][0] + " - " if v['groups'] else ""
        text = ("❌ " if "activate" in chat_data and v['deconz_id'] in chat_data["activate"] else "") + group + v['name']
        if v['type'] == 'ZHAOpenClose':
            text += ' 🚪'
        elif v['type'] == 'ZHAPresence':
            text += ' 🚶‍♀️'
        result += [[InlineKeyboardButton(text, callback_data=data + v['deconz_id'])]]
    if data == "arm.":
        for i, n in mongo.get_groups(mongo.get_db()).items():
            if 'activate_group' in chat_data:
                print(chat_data["activate_group"])
            text = ("❌ " if "activate_group" in chat_data and i in chat_data[
                "activate_group"] else "") + "👥 {}".format(n)
            result += [[InlineKeyboardButton(text, callback_data="{}group{}".format(data, i))]]
    result += [[InlineKeyboardButton(text="Weiter ➡️", callback_data="arm_next.")]] if "activate" in chat_data and \
                                                                                       chat_data["activate"] else []
    return InlineKeyboardMarkup(result)


def get_sensors_text(chat_data):
    mongo_sensors = mongo.get_sensors(mongo.get_db())
    text = "*Alarm für diese Sensoren aktivieren*\n"
    motion = []
    openclose = []
    for sensor in mongo_sensors:
        if sensor['deconz_id'] in chat_data['activate']:
            sensor_text = "- " + (sensor['groups'][0] + ": " if sensor['groups'] else "") + sensor['name']
            if sensor['type'] == "ZHAOpenClose":
                openclose.append(sensor_text)
            elif sensor['type'] == "ZHAPresence":
                motion.append(sensor_text)
    if motion:
        text += "\nBewegungsmelder:\n" + "\n".join(motion) + "\n"
    if openclose:
        text += "\nTür- und Fenstersensoren:\n" + "\n".join(openclose) + "\n"
    return text


def get_sensor_info(sensor, chat_data):
    magnet = Magnet()
    s = magnet.get_sensor(sensor)
    chat_data['name'] = s['name']
    m = mongo.get_one_sensor(mongo.get_db(), sensor)
    groups = m['groups']
    unit = m['unit']
    status = ['geschlossen', 'offen ⚠️']
    battery = "{}%{}".format(int(s['config']['battery']), "" if int(s['config']['battery']) > 20 else " ⚠️")
    txt = "*{}*\nStatus: {}\nErreichbar: {}\nLetzter Kontakt: _{}_\nBatterie: {}\nTemperatur: {}°C\nTyp: _{}_\nID: `{}`"
    txt += "\nHauptgruppe: _{}_"
    return txt.format(s['name'], status[int(s['state'][unit])], "✔️" if s['config']['reachable'] else "❌",
                      get_local_time(s['state']['lastupdated']), battery, s['config']['temperature'] / 100,
                      s['type'], s['uniqueid'], groups[0] if groups else "➖")


def send_sensor_info(update, chat_data, sensor=None):
    sensor = str(update.data.split(".")[-1] if not sensor else sensor)
    try:
        update.message.edit_text(get_sensor_info(sensor, chat_data), parse_mode=ParseMode.MARKDOWN,
                                 reply_markup=get_sensor_keyboard(sensor))
    except TelegramError:
        update.message.reply_text(get_sensor_info(sensor, chat_data), parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=get_sensor_keyboard(sensor))


def rename_sensor(update, value, chat_data, text):
    msg_id = update.callback_query.message.reply_text(text, reply_markup=ForceReply(),
                                                      parse_mode=ParseMode.MARKDOWN)['message_id']
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Abbrechen", callback_data="sensor_rename_abort.{}-{}".format(str(msg_id), value))]])
    if text == NEW_GROUP:
        pass
    else:
        update.callback_query.message.edit_text(get_sensor_info(chat_data['id'], chat_data),
                                                parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


def abort_rename_sensor(bot, update, value, chat_data):
    msg_id, sensor = value.split('-')
    bot.delete_message(chat_id=update.callback_query.message.chat_id, message_id=msg_id)
    send_sensor_info(update.callback_query, chat_data, sensor=sensor)


def send_sensor_list(update, edit=False):
    send = update.message.edit_text if edit else update.message.reply_text
    send("Wähle einen Sensor aus:", reply_markup=get_sensor_list())


def update_sensor_name(sensor, update, chat_data):
    if Magnet.update_name(sensor, update.message.text) and mongo.update_name(db, sensor, update.message.text):
        send_sensor_info(update, chat_data, sensor=sensor)
    else:
        update.message.reply_text("Etwas ist schief gelaufen...")


def arm_system(update):
    update.message.reply_text("Wähle Sensor(en) und/oder Gruppe(n) aus:", reply_markup=get_sensor_list(data="arm."))


def echo(bot, update, chat_data):
    if update.message.reply_to_message:
        if update.message.reply_to_message.text.replace("*", "") == NEW_NAME.format(chat_data['name']).replace("*", ""):
            if len(update.message.text) > 30:
                update.message.reply_text("Zu lang! Der Name muss kürzer sein")
            else:
                update_sensor_name(chat_data["id"], update, chat_data)
        elif update.message.reply_to_message.text == NEW_GROUP:
            if len(update.message.text) > 15:
                update.message.reply_text("Zu lang! Der Name muss kürzer sein")
            else:
                add_group_name(update, chat_data)
    elif update.message.text in KB[0]:
        send_sensor_list(update)
    elif update.message.text in KB[1]:
        arm_system(update)


def add_group_name(update, chat_data):
    if mongo.add_group(mongo.get_db(), update.message.text):
        send_groups(update, chat_data['id'], chat_data['name'])
    else:
        update.message.reply_text("Etwas ist schief gelaufen...")


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def get_active(chat_data, data):
    value = [data] if not data[:5] == 'group' else mongo.get_group_sensors(mongo.get_db())[data[5:]]
    # Wahr wenn einer aus Gruppe noch fehlt
    # remove = not any([x not in chat_data['activate'] for x in value if 'activate' in chat_data])
    # Wahr wenn jeder aus Gruppe vorhanden
    remove = not any([x not in chat_data['activate'] for x in value]) if 'activate' in chat_data else False
    print(chat_data['activate'] if 'activate' in chat_data else "")
    print([x not in chat_data['activate'] for x in value] if 'activate' in chat_data else "")
    if 'activate' in chat_data:
        for v in value:
            if remove:
                chat_data['activate'].remove(v)
                continue
            chat_data["activate"] = list(set(chat_data["activate"] + [v]))
    else:
        chat_data['activate'] = value
    if not data[:5] == 'group':
        return
    elif 'activate_group' in chat_data:
        if remove:
            chat_data['activate_group'].remove(data[5:])
            return
        chat_data["activate_group"] = list(set(chat_data["activate_group"] + [data[5:]]))
        return
    chat_data['activate_group'] = [data[5:]]
    return


def send_groups(update, sensor, name):
    try:
        update.message.edit_text(CHOOSE_GROUPS.format(name), reply_markup=get_group_keyboard(sensor),
                                 parse_mode=ParseMode.MARKDOWN)
    except TelegramError:
        update.message.reply_text(CHOOSE_GROUPS.format(name), reply_markup=get_group_keyboard(sensor),
                                  parse_mode=ParseMode.MARKDOWN)


def add_group(update, sensor, id_new, name):
    mongo.add_sensor_group(mongo.get_db(), sensor, id_new)
    send_groups(update.callback_query, sensor, name)


def answer_callback(bot, update, chat_data):
    update.callback_query.answer()
    cmd, value = update.callback_query.data.split('.')

    if cmd in ["sensor", "group_manage_back"]:
        send_sensor_info(update.callback_query, chat_data)
        chat_data["id"] = value
    elif cmd in ["arm", "arm_back"]:
        get_active(chat_data, value)
        kb = get_sensor_list(data="arm.", chat_data=chat_data)
        update.callback_query.message.edit_text("Wähle Sensor(en) und/oder Gruppe(n) aus:", reply_markup=kb)
    elif cmd in ["arm_next"]:
        update.callback_query.message.edit_text(get_sensors_text(chat_data), reply_markup=get_alarm_mode_kb(),
                                                parse_mode=ParseMode.MARKDOWN)
    elif cmd in ["sensor_back"]:
        send_sensor_list(update.callback_query, edit=True)
    elif cmd in ["sensor_rename"]:
        rename_sensor(update, value, chat_data, NEW_NAME.format(chat_data['name']))
    elif cmd in ["sensor_rename_abort"]:
        abort_rename_sensor(bot, update, value, chat_data)
    elif cmd in ["sensor_manage_group"]:
        mongo.check_groups(mongo.get_db())
        send_groups(update.callback_query, value, chat_data['name'])
    elif cmd in ["group_add"]:
        rename_sensor(update, value, chat_data, NEW_GROUP)
    elif cmd in ["group"]:
        add_group(update, chat_data['id'], value, chat_data['name'])


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
