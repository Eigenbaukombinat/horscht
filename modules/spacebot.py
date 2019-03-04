import datetime
import requests


SPACESTATUS_URL = 'https://eigenbaukombinat.de/status/status.json'


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
    status = 'offen' if payload == 'true' else 'zu'
    msg = '<b>Der Space ist jetzt {}.</b>'.format(status)
    for room in bot.client.rooms.values():
        # write to 1:1 chats with me
        if len(room._members) == 2:
            room.send_html(msg)
        # XXX move to module configuration, allow multiple room names
        if room.display_name == 'sozialraum':
            room.send_html(msg)


CMDS = {'!status': get_status,
        '!setstatus': set_status, }

MSGS = {'space/status/open': announce_status, }
