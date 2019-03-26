from matrix_client.api import MatrixRequestError
from matrix_client.client import MatrixClient
from requests.exceptions import ConnectionError, Timeout
import argparse
import configparser
import importlib
import logging
import os
import paho.mqtt.client as mqtt
import queue
import re
import sys
import time
import traceback
import urllib.parse


COMMAND_REGISTRY = {}
MESSAGES_REGISTRY = {}

ACL_ROOMS = {}
ACL_USERS = {}

COMMANDS = []
HELP = '''{} reagiert auf folgendes:
<ul>
{}
</ul>
{} reagiert auch auf MQTT-Nachrichten:
<ul>
{}
</ul>
'''
HELP_MSGS = []
HELP_CMDS = []


def format_help_entry(cmd, txt):
    return '<li><b>{}</b> – {}</li>\n'.format(cmd, txt)


def sigterm_handler(_signo, _stack_frame):
    """Raises SystemExit(0), causing everything to cleanly shut down."""
    sys.exit(0)


class Bot(object):
    """Handles everything that the bot does."""
    def __init__(self, server, username, password, display_name):
        self.client = None
        self.server = server
        self.username = username
        self.password = password
        self.display_name = display_name
        self.event_queue = queue.Queue()
        self.invite_queue = queue.Queue()

    def login(self):
        """Logs onto the server."""
        client = MatrixClient(self.server)
        client.login_with_password_no_sync(
            self.username, self.password)
        self.client = client

    def get_room(self, event):
        """Returns the room the given event took place in."""
        return self.client.rooms[event['room_id']]

    def command_allowed(self, cmd, user, room):
        # canonical alias not set always, maybe its a private conversation
        # then we check against the room id.
        room_address = room.canonical_alias or room.room_id
        # check if the command is allowed in the room it was spelled
        # if allowed_in_room is not set, the command is public
        allowed_in_room = True
        allowed_rooms = ACL_ROOMS.get(cmd)
        if allowed_rooms is not None and room_address not in allowed_rooms:
            allowed_in_room = False

        # check if the sender is allowed to use the command
        allowed_for_user = False
        allowed_users = ACL_USERS.get(cmd)
        if allowed_users is not None and user in allowed_users:
            allowed_for_user = True

        # allowed users can use the command everywhere!
        if allowed_in_room or allowed_for_user:
            return True
        return False

    def handle_command(self, event, cmd, args):
        """Handles the given command, possibly sending a reply to it."""
        cmd = cmd.lower()
        room = self.get_room(event)
        command = COMMAND_REGISTRY.get(cmd)

        # command not found
        if command is None:
            return

        if self.command_allowed(cmd, event['sender'], room):
            command(event, command, self, args)

    def reply(self, event, message, html=False):
        """Replies to the given event with the provided message."""
        room = self.get_room(event)
        logging.info("Reply: %s" % message)
        if html:
            room.send_html(message)
        else:
            room.send_text(message)

    def is_name_in_message(self, message):
        """Returns whether the message contains the bot's name.

        Considers both display name and username.
        """
        regex = "({}|{})".format(
            self.display_name, self.username)
        return re.search(regex, message, flags=re.IGNORECASE)

    def handle_invite(self, room_id, invite_state):
        # join rooms if invited
        try:
            self.client.join_room(room_id)
            logging.info('Joined room: %s' % room_id)
        except MatrixRequestError as e:
            if e.code == 404:
                # room was deleted after invite or something; ignore it
                logging.info('invited to nonexistent room {}'.format(room_id))
            else:
                raise(e)

    def get_help(self, event):
        user = event['sender']
        room = self.get_room(event)
        help_commands = []
        for cmd, htxt in sorted(HELP_CMDS):
            if self.command_allowed(cmd, event['sender'], room):
                help_commands.append(format_help_entry(cmd, htxt))
        help_messages = []
        for msg, htxt in sorted(HELP_MSGS):
            help_messages.append(format_help_entry(msg, htxt))

        helptxt = HELP.format(
                    self.display_name,
                    '\n'.join(help_commands),
                    self.display_name,
                    '\n'.join(help_messages))
        return helptxt

    def handle_message(self, event, message):
        command_found = False
        for command in COMMANDS:
            match = re.search(command, message, flags=re.IGNORECASE)
            if match and (match.start() == 0 or
                          self.is_name_in_message(message)):
                logging.info("Command found, handling message: %s" % message)
                command_found = True
                args = message[match.start():].split(' ')
                self.handle_command(event, args[0], args[1:])
                break
        if not command_found and message.startswith('!help'):
            self.reply(event, self.get_help(event), html=True)

        return command_found

    def handle_event(self, event):
        """Handles the given event.
        """
        self.send_read_receipt(event)

        # only care about text messages
        if event['type'] != 'm.room.message' or \
                event['content']['msgtype'] != 'm.text':
            return

        # dont care about messages by myself
        if event['sender'] == self.client.user_id:
            return

        message = str(event['content']['body'])
        command_found = self.handle_message(event, message)
        if not command_found and self.display_name in message:
            room = self.get_room(event)
            if self.is_name_in_message(message):
                self.reply(event, "Don't mess with me, buddy. "
                                  "Try !help instead.")

    def set_display_name(self, display_name):
        """Sets the bot's display name on the server."""
        self.client.api.set_display_name(self.client.user_id, display_name)

    def get_display_name(self):
        """Gets the bot's display name from the server."""
        return self.client.api.get_display_name(self.client.user_id)

    def run(self):
        """Indefinitely listens for messages and handles all that come."""
        current_display_name = self.get_display_name()
        if current_display_name != self.display_name:
            self.set_display_name(self.display_name)

        # listen for invites, including initial sync invites
        self.client.add_invite_listener(
            lambda room_id, state: self.invite_queue.put((room_id, state)))

        # get rid of initial event sync
        logging.info("initial event stream")
        self.client.listen_for_events()

        # listen to events and add them all to the event queue
        # for handling in this thread
        self.client.add_listener(self.event_queue.put)

        def exception_handler(e):
            if isinstance(e, Timeout):
                logging.warning("listener thread timed out.")
            logging.error("exception in listener thread:")
            traceback.print_exc()

        # start listen thread
        logging.info("starting listener thread")
        self.client.start_listener_thread(exception_handler=exception_handler)

        try:
            while True:
                time.sleep(0.25)

                # handle any queued events
                while not self.event_queue.empty():
                    event = self.event_queue.get_nowait()
                    self.handle_event(event)

                while not self.invite_queue.empty():
                    room_id, invite_state = self.invite_queue.get_nowait()
                    self.handle_invite(room_id, invite_state)

        finally:
            logging.info("stopping listener thread")
            self.client.stop_listener_thread()

    def send_read_receipt(self, event):
        """Sends a read receipt for the given event."""
        if "room_id" in event and "event_id" in event:
            room_id = urllib.parse.quote(event['room_id'])
            event_id = urllib.parse.quote(event['event_id'])
            self.client.api._send("POST", "/rooms/" + room_id +
                                  "/receipt/m.read/" + event_id,
                                  api_path="/_matrix/client/r0")


def main():
    argparser = argparse.ArgumentParser(
        description="A chatbot for Matrix (matrix.org)")
    argparser.add_argument("--debug",
                           help="Print out way more things.",
                           action="store_true")
    args = vars(argparser.parse_args())
    debug = args['debug']

    # suppress logs of libraries
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(name)s '
                        '%(levelname)s %(message)s')

    # read bot config
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        print("config.ini does not exist, copy config.ini.example and edit!")
        sys.exit(0)
    config.read('config.ini')
    server = config['bot']['server']
    username = config['bot']['username']
    password = config['bot']['password']
    display_name = config['bot']['display_name']
    mqtt_broker = config['bot']['mqtt_broker']

    for module in config.sections():
        if module == 'bot':
            # ignore general section 
            continue
        try:
            mod = importlib.import_module(module)
        except ImportError:
            logging.error(
                'Module {} not found. Ignoring.'.format(module))
            continue

        logging.info('Loaded extension {}'.format(module))
        if hasattr(mod, 'CMDS'):
            for cmd, func in mod.CMDS.items():
                HELP_CMDS.append((cmd, func.__doc__))
            COMMAND_REGISTRY.update(mod.CMDS)
            ACL_USERS[cmd] = config[module].get('allowed_users')
            ACL_ROOMS[cmd] = config[module].get('allowed_rooms')
        if hasattr(mod, 'MSGS'):
            for msg, func in mod.MSGS.items():
                HELP_MSGS.append((msg, func.__doc__))
            MESSAGES_REGISTRY.update(mod.MSGS)

    COMMANDS.extend(list(COMMAND_REGISTRY.keys()))



    def mqtt_received(client, data, message):
        handler = MESSAGES_REGISTRY.get(message.topic)
        if handler is None:
            return
        handler(message, data, client, bot)

    while True:
        try:
            bot = Bot(server, username, password, display_name)
            bot.login()
            if mqtt_broker:
                mqtt_client = mqtt.Client()
                mqtt_client.connect(mqtt_broker)
                time.sleep(1)
                for topic in MESSAGES_REGISTRY.keys():
                    mqtt_client.subscribe(topic)
                time.sleep(1)
                mqtt_client.on_message = mqtt_received
                mqtt_client.loop_start()
            bot.run()
        except (MatrixRequestError, ConnectionError):
            if mqtt_broker:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            traceback.print_exc()
            logging.warning("disconnected. Waiting a minute to see if"
                            " the problem resolves itself...")
            time.sleep(60)


if __name__ == '__main__':
    main()
