import datetime
import requests
import logging
import os
import shutil
import tempfile
import json


shlog = logging.getLogger('shlog')
shlog.setLevel(logging.DEBUG)
shlog_fh = logging.FileHandler('spacehistory.log')
shlog_formatter = logging.Formatter('%(asctime)s - %(message)s')
shlog_fh.setFormatter(shlog_formatter)
shlog.addHandler(shlog_fh)

SPACESTATUS_URL = 'https://eigenbaukombinat.de/status/status.json'
SPACEOPEN_URL = 'https://eigenbaukombinat.de/status/openuntil.json'
CURRENT_STATUS = 'zu'



def get_last_status():
    with open('.lastst', 'r') as lastst:
        return lastst.read().strip()

def set_last_status(status):
    with open('.lastst', 'w') as lastst:
        lastst.write(status)


def get_status(event, message, bot, args, config):
    """Erfahre, ob das Eigenbaukombinat gerade geöffnet ist."""
    timestamp = datetime.datetime.now().isoformat()
    st = requests.get('{}?{}'.format(SPACESTATUS_URL, timestamp)).json()

    if st['state']['open']:
        howlong = requests.get('{}?{}'.format(SPACEOPEN_URL, timestamp)).json()
        if howlong.get('closetime') is not None:
            status = 'bis mindestens {} Uhr offen'.format(howlong['closetime'])
        else:
            status = 'offen'
    else:
        status = 'zu'

    bot.reply(event, "<b>Der Space ist {}.</b>".format(status), html=True)


def set_status(event, message, bot, args, config):
    """Setze den Space-Status falls jemand vergessen hat den Schalter
    zu benutzen. (Noch nicht implementiert.)"""
    which = ''
    if len(args):
        which = args[0]
    bot.reply(event, "Setze status auf %s. Nicht." % which)


def _announce(bot, topic, msg):
    """Announce a msg of a topic to the subscribed rooms."""
    for room in list(bot.client.rooms.values()):
        if room.room_id in SUBS[topic]:
            bot.send_html(room, msg)


def announce_status(message, data, client, bot, config):
    """Schreibt den spacestatus in alle Räume."""
    payload = message.payload.decode('utf8')
    logging.info("space/status/open contained: {}".format(payload))
    if payload == 'true':
        status = 'offen'
    elif payload == 'false':
        status = 'zu'
    else:
        logging.info("Unknown payload: '{}'".format(payload))
        return
    if status == get_last_status():
        # status did not change, this bug should be fixed in spacemaster...
        # also, this happens every time the door is locked after correctly closing the space via switch. (space close safetybelt)
        logging.info("Received Message, but status did not change. Possibly door the has been locked after switch has been correctly set to closed.")
        return
    set_last_status(status)
    shlog.info(status)

    msg = '<b>Der Space ist jetzt {}.</b>'.format(status)
    _announce(bot, 'space/status/open', msg)



def announce_generic(message, data, client, bot, config):
    """schreibt in einen raum wenn eine mqtt empfangen wurde"""
    logging.info("reacting to {message.topic}")
    shlog.info('klingel')
    _announce(bot, message.topic, ROOM_MSGS[message.topic])


def subscribe(event, message, bot, args, config):
    """Abonniert das angegebene MQTT Thema für einen Raum. Es werden nur die space/status/* Themen unterstützt!"""
    topic = ''
    if len(args):
        topic = args[0]
    if topic not in MSGS:
        bot.reply(event, "Unbekanntes topic.")
        return
    SUBS[topic].append(event['room_id'])
    bot.reply(event, f"Das Thema {topic} wurde in diesem Raum abonniert.")
    save_subscriptions()

def unsubscribe(event, message, bot, args, config):
    """Beendet ein Abo für das angegebene Thema für einen Raum."""
    topic = ''
    if len(args):
        topic = args[0]
    if topic not in MSGS:
        bot.reply(event, "Unbekanntes topic.")
        return
    if event['room_id'] not in SUBS[topic]:
        bot.reply(event, "Abo für das Thema {topic} in diesem Raum nicht gefunden.")
        return
    del SUBS[topic][SUBS[topic].index(event['room_id'])]
    bot.reply(event, f"Das Abo für das Thema {topic} wurde in diesem Raum beendet.")
    save_subscriptions()

def list_subscriptions(event, message, bot, args, config):
    """Zeigt die aktuelle abonnierten Themen in einem Raum an."""
    topics = []
    for topic, rooms in SUBS.items():
        if event['room_id'] in rooms:
            topics.append(topic)
    bot.reply(event, f"In diesem Raum sind folgende Themen abonniert: {', '.join(topics)}")


def save_subscriptions():
    """Saves the subscriptions to a file."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(json.dumps(SUBS).encode())
        temp_file_path = temp_file.name

    shutil.move(temp_file_path, '.subscriptions')


CMDS = {'!status': get_status,
        '!setstatus': set_status,
        '!subscribe': subscribe,
        '!unsubscribe': unsubscribe,
        '!list_subscriptions': list_subscriptions, }

MSGS = { 'space/status/open': announce_status, 
         'space/status/klingel/count-OPEN': announce_generic,
         'space/status/klingel/count-CLOSE': announce_generic,
         'space/status/klingel': announce_generic,
         'space/status/closetime': announce_generic,
         'space/status/error': announce_generic,
         'space/status/door': announce_generic}

ROOM_MSGS = {
         'space/status/klingel/count-OPEN': '<b>Es hat {} mal geklingelt, während der Space geschlossen war.</b>',
         'space/status/klingel/count-CLOSE': '<b>Es hat {} mal geklingelt, während der Space offen war.</b>',
         'space/status/klingel': '<b>Klingelingeling!</b><!-- {} -->',
         'space/status/closetime': '<b>Der Space ist bis mindestens {} Uhr offen.</b>',
         'space/status/error': '<b>FEHLER:</b><br/><i>{}</i>',
         'space/status/door': '<b>Tuerstatus: {}</b>'}



SUBS = { msg: [] for msg in MSGS }

def load_subscriptions():
    if not os.path.isfile('.subscriptions'):
        return
    with open('.subscriptions', 'r') as subfile:
        subs = json.loads(subfile.read())
        for topic, rooms in subs.items():
            if topic in SUBS and isinstance(rooms, list):
                SUBS[topic] = rooms

load_subscriptions()
