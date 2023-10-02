import datetime
import requests
import logging



def talk(event, message, bot, args, config):
    """Lässt Bernd sprechen."""
    sender = event['sender']
    atuser, server = sender.split(':')
    user = atuser[1:]
    text = '{}'.format(' '.join(args))
    bot.mqtt_client.publish('space/bernd/speak', text)

CMDS = { '!talk': talk }
