import datetime
import requests


SPACESTATUS_URL = 'https://eigenbaukombinat.de/status/status.json'


def get_status(event, message, bot, args):
    """Erfahre, ob das Eigenbaukombinat gerade geöffnet ist."""
    timestamp = datetime.datetime.now().isoformat()
    st = requests.get('{}?{}'.format(SPACESTATUS_URL, timestamp)).json()

    if st['state']['open']:
        status = '<span style="color:green">offen</span>'
    else:
        status = '<span style="color:red">zu</span>'

    bot.reply(event, "<h2>Der Space ist {}.</h2>".format(status), html=True)


def set_status(event, message, bot, args):
    """Setze den Space-Status falls jemand vergessen hat den Schalter
    zu benutzen. (Noch nicht implementiert.)"""
    which = ''
    if len(args):
        which = args[0]
    bot.reply(event, "Setze status auf %s. Nicht." % which)


CMDS = { '!status': get_status,
         '!setstatus': set_status, }
