import datetime
import requests
import logging
import json



def announce_reminder(message, data, client, bot, config):
    """schreibt reminder in einen raum"""
    logging.info("reacting to space/reminder")

    payload = message.payload.decode('utf8')
    data = json.loads(payload)
    summary = data['summary']
    desc = data['description']
    if desc is None:
        desc = ''
    if 'Mozilla Standardbeschreibung' in desc:
        desc = ''
    if 'Tonne' in desc:
        desc = ''
    if 'Orgatreffen' in summary:
        desc = 'Agenda/Protokoll: https://pads.eigenbaukombinat.de/EBK-Orgatreffen'
    time_left = data['time_left_to_event']
    event_start = data['event_start']
    #TODO:
    # event_start in zeitzone anzeigen (momentan utc)
    # event_start formatieren dd.mm.yyyy hh:mm
    msg = '<b>Erinnerung: %s</b> (%s)<br/>%s<br/><i>(noch %s)</i>' % (summary, desc, event_start, time_left)
    for room in list(bot.client.rooms.values()):
        # XXX move to module configuration, allow multiple room names
        if room.display_name in ('spacemaster',) and 'Tonne' not in msg:
            bot.send_html(room, msg)
        if room.display_name in ('Muell',) and 'Tonne' in msg:
            bot.send_html(room, msg)
        if room.display_name in ('sozialraum',) and 'Orgatreffen' in msg:
            bot.send_html(room, msg)

MSGS = { 'space/reminder': announce_reminder } 
