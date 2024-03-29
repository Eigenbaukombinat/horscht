import datetime
import requests
import logging

shlog = logging.getLogger('shlog')
shlog.setLevel(logging.DEBUG)
shlog_fh = logging.FileHandler('/home/spaceapi/spacehistory.log')
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
    for room in list(bot.client.rooms.values()):
        # write to 1:1 chats with me
        if len(room._members) == 2:
            bot.send_html(room, msg)
        # XXX move to module configuration, allow multiple room names
        if room.display_name in ['sozialraum', 'spacemaster']:
            bot.send_html(room,msg)

def announce_klingel(message, data, client, bot, config):
    """schreibt in einen raum wenn es klingelt"""
    logging.info("reacting to space/status/klingel")
    msg = '<b>Klingelingeling!</b>'
    shlog.info('klingel')
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'spacemaster':
            bot.send_html(room,msg)

def announce_count_close(message, data, client, bot, config):
    """schreibt in einen raum wie oft es geklingelt hat"""
    payload = message.payload.decode('utf8')
    logging.info("space/status/klingel/count-CLOSE contained: {}".format(payload))
    msg = '<b>Es hat {} mal geklingelt, während der Space offen war.</b>'.format(payload)
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'spacemaster':
            bot.send_html(room,msg)

def announce_count_open(message, data, client, bot, config):
    """schreibt in einen raum wie oft es geklingelt hat"""
    payload = message.payload.decode('utf8')
    logging.info("space/status/klingel/count-OPEN contained: {}".format(payload))
    msg = '<b>Es hat {} mal geklingelt, während der Space geschlossen war.</b>'.format(payload)
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'spacemaster':
            bot.send_html(room,msg)

def announce_door(message, data, client, bot, config):
    """schreibt in einen Raum den Türstatus"""
    payload = message.payload.decode('utf8')
    logging.info("space/status/door contained: {}".format(payload))
    msg = '<b>Tuerstatus: {}</b>'.format(payload)
    shlog.info(payload)
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'spacemaster':
            bot.send_html(room,msg)

def announce_closetime(message, data, client, bot, config):
    """Schreibt in sozialraum und spacemaster wenn eine neue Schliesszeit gesetzt wurde."""
    payload = message.payload.decode('utf8')
    logging.info("space/status/closetime contained: {}".format(payload))
    msg = '<b>Der Space ist bis mindestens {} Uhr offen.</b>'.format(payload)
    shlog.info('closetime {}'.format(payload))
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name in ('spacemaster', 'sozialraum'):
            bot.send_html(room,msg)

def announce_error(message, data, client, bot, config):
    """Schreibt Fehlermeldungen in in den Spacemaster Raum."""
    payload = message.payload.decode('utf8')
    logging.info("space/status/error contained: {}".format(payload))
    msg = '<b>FEHLER:</b><br/><i>{}</i>'.format(payload)
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name in ('spacemaster'):
            bot.send_html(room,msg)

CMDS = {'!status': get_status,
        '!setstatus': set_status, }

MSGS = { 'space/status/open': announce_status, 
         'space/status/klingel/count-OPEN': announce_count_open,
         'space/status/klingel/count-CLOSE': announce_count_close,
         'space/status/klingel': announce_klingel,
         'space/status/closetime': announce_closetime,
         'space/status/error': announce_error,
         'space/status/door': announce_door}
