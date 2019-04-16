import datetime
import requests
import logging


SPACESTATUS_URL = 'https://eigenbaukombinat.de/status/status.json'
CURRENT_STATUS = 'zu'

def get_last_status():
    with open('.lastst', 'r') as lastst:
        return lastst.read().strip()

def set_last_status(status):
    with open('.lastst', 'w') as lastst:
        lastst.write(status)


def get_status(event, message, bot, args):
    """Erfahre, ob das Eigenbaukombinat gerade geöffnet ist."""
    timestamp = datetime.datetime.now().isoformat()
    st = requests.get('{}?{}'.format(SPACESTATUS_URL, timestamp)).json()

    if st['state']['open']:
        status = 'offen'
    else:
        status = 'zu'

    bot.reply(event, "<b>Der Space ist {}.</b>".format(status), html=True)


def set_status(event, message, bot, args):
    """Setze den Space-Status falls jemand vergessen hat den Schalter
    zu benutzen. (Noch nicht implementiert.)"""
    which = ''
    if len(args):
        which = args[0]
    bot.reply(event, "Setze status auf %s. Nicht." % which)


def announce_status(message, data, client, bot):
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
        logging.info("Received Message, but status did not change. :(")
        return
    set_last_status(status)
    msg = '<b>Der Space ist jetzt {}.</b>'.format(status)
    for room in list(bot.client.rooms.values()):
        # write to 1:1 chats with me
        if len(room._members) == 2:
            room.send_html(msg)
        # XXX move to module configuration, allow multiple room names
        if room.display_name in ['sozialraum', 'spacemaster']:
            room.send_html(msg)

def announce_klingel(message, data, client, bot):
    """schreibt in einen raum wenn es klingelt"""
    logging.info("reacting to space/status/klingel")
    msg = '<b>Klingelingeling!</b>'
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'spacemaster':
            room.send_html(msg)

def announce_count_close(message, data, client, bot):
    """schreibt in einen raum wie oft es geklingelt hat"""
    payload = message.payload.decode('utf8')
    logging.info("space/status/klingel/count-CLOSE contained: {}".format(payload))
    msg = '<b>Es hat {} mal geklingelt, während der Space offen war. :)</b>'.format(payload)
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'spacemaster':
            room.send_html(msg)

def announce_count_open(message, data, client, bot):
    """schreibt in einen raum wie oft es geklingelt hat"""
    payload = message.payload.decode('utf8')
    logging.info("space/status/klingel/count-OPEN contained: {}".format(payload))
    msg = '<b>Es hat {} mal geklingelt, während der Space zu war. :(</b>'.format(payload)
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'spacemaster':
            room.send_html(msg)

def announce_door(message, data, client, bot):
    """schreibt in einen Raum den Türstatus"""
    payload = message.payload.decode('utf8')
    logging.info("space/status/door contained: {}".format(payload))
    msg = '<b>Tuerstatus: {}</b>'.format(payload)
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'spacemaster':
            room.send_html(msg)


CMDS = {'!status': get_status,
        '!setstatus': set_status, }

MSGS = { 'space/status/open': announce_status, 
         'space/status/klingel/count-OPEN': announce_count_open,
         'space/status/klingel/count-CLOSE': announce_count_close,
         'space/status/klingel': announce_klingel ,
         'space/status/door': announce_door}
