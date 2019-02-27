#!/usr/bin/env python3
from matrix_client.api import MatrixRequestError
from matrix_client.client import MatrixClient
from requests.exceptions import ConnectionError, Timeout
import argparse
import logging
import queue
import re
import os
import sys
import importlib
import time
import traceback
import urllib.parse


COMMAND_REGISTRY = {}
HELP = []


for fn in os.listdir('modules'):
    if not fn.startswith('_') and fn.endswith('.py'):
        mod = importlib.import_module('modules.{}'.format(fn[:-3]))
        for cmd, func in mod.CMDS.items():
            HELP.append('{}: {}'.format(cmd, func.__doc__))
        COMMAND_REGISTRY.update(mod.CMDS)

COMMANDS = COMMAND_REGISTRY.keys()


def sigterm_handler(_signo, _stack_frame):
    """Raises SystemExit(0), causing everything to cleanly shut down."""
    sys.exit(0)


class Bot(object):
    """Handles everything that the bot does."""
    def __init__(self):
        self.client = None
        self.server = 'https://matrix.eigenbaukombinat.de'
        self.username = 'horscht'
        self.password = 'xxx'
        self.display_name = 'horscht'
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

    def handle_command(self, event, command, args):
        """Handles the given command, possibly sending a reply to it."""
        command = COMMAND_REGISTRY.get(command.lower())
        if command is not None:
            command(event, command, self, args)

    def reply(self, event, message):
        """Replies to the given event with the provided message."""
        room = self.get_room(event)
        logging.info("Reply: %s" % message)
        import pdb; pdb.set_trace()
        room.send_notice(message)

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
            self.reply(event, '\n'.join(HELP))
        
        return command_found


    def handle_event(self, event):
        """Handles the given event.

        Joins a room if invited, learns from messages, and possibly responds to
        messages.
        """
        self.send_read_receipt(event)
        
        # only care about text messages
        if event['type'] != 'm.room.message' or event['content']['msgtype'] != 'm.text':
            return

         # dont care about messages by myself
        if event['sender'] == self.client.user_id:
            return

        message = str(event['content']['body'])
        command_found = self.handle_message(event, message)
        if not command_found and self.display_name in message:
            room = self.get_room(event)
            if self.is_name_in_message(message):
                self.reply(event, "Don't mess with me, buddy. Try !help instead.")

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

    while True:
        try:
            bot = Bot()
            bot.login()
            bot.run()
        except (MatrixRequestError, ConnectionError):
            traceback.print_exc()
            logging.warning("disconnected. Waiting a minute to see if"
                            " the problem resolves itself...")
            time.sleep(60)


if __name__ == '__main__':
    main()
