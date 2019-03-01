# horscht

A simple to extend matrix chatbot. 


## Installation

```bash
git clone git@github.com:Eigenbaukombinat/horscht.git
cd horscht
python3 -m venv .
bin/pip install -r requirements.txt
cp config.ini.example config.ini
```

## Configuration and starting

Then, edit config.ini to your needs and start the bot. Please note that you can leave the mqtt_broker setting empty, to disable MQTT support.

```bash
bin/python main.py
```

## Development mode

If you work on a specific extension module (see below), you can restrict to bot to only react on the commands specified in that module. (This prevents the bot from answering multiple times if its running elsewhere.)

```bash
bin/python main.py --dev mymodule
```

## Writing extensions

To extend a bot, simply drop a .py-File into the modules folder, which contains
the code of your extension.

### React to commands

If you want to react to spelled commands, you have to write a single function for every command. The docstring of the function will be displayed in the bots help text.

It must accept exactly 4 arguments:

* **event** The event object, containing all information you might need.
* **message** The message which was spelled.
* **bot** The bot instance, providing the reply method and many more.
* **args** Arguments which where given to the command (List).

```python
def my_function(event, message, bot, args):
	"""Help text for your command."""
	bot.reply(event, "Heyja!")
```

After the definition of the function, you have to register it in the CMDS dict  with the command as the key.

```python
CMDS = { '!hello': my_function }
```

### React to MQTT messages

Your bot can also react to MQTT messages. Make sure to set the address of the MQTT broker in your config.ini.

For each topic you want to subscribe to, you have to define a function, which must
accept these 4 arguments:

* **message** The MQTT message. Among others, it has the "payload" and "topic" attributes.
* **data** MQTT Userdata. Whatever.
* **client** The MQTT Client object. You might want to publish some messages in your handler.
* **bot** The Bot instance. In the example below it is used to send the received text into every room the bot is in.

```python
def announce_status(message, data, client, bot):
	"""Help text."""
	text = message.payload.decode('utf8')
    for room_id in bot.client.rooms:
        bot.client.rooms[room_id].send_notice(text)
```

You have to register your function, by mapping the topic in the MSGS dict to your function.

```python
MSGS = { 'example/topic': announce_status }
```