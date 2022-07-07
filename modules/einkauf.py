import logging


def announce_nachkauf(message, data, client, bot, config):
    """schreibt nachrichten vom nachkaufomat3000 in einen raum"""
    logging.error("reacting to space/nachkaufen")

    payload = message.payload.decode('utf8')
    for room in list(bot.client.rooms.values()):
        if room.display_name.lower() in ('einkauf',):
            bot.send_html(room, payload)

MSGS = { 'space/nachkaufen': announce_nachkauf } 
