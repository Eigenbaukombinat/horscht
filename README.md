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

## Configure extensions

You can configure the extensions your bot should load
be defining sections in your config file with an importable module as section name. To use the shipped extension `spacebot` specify like `[modules.spacebot]`.
You can also load extensions from other python packages like `[my.fancy.exension]`.

In those sections there are 2 possible configuration options which lets to define which users
and which rooms the commands from the module are allowed.

### allowed_rooms

Specify the rooms (by their canonical room address) the command is allowed in.

```cfg
[my.fancy.extension]
allowed_rooms = #room1:fancyserver.com
	#room2:fancyserver.com
```

### allowed_users

To let specific users use a command (even in rooms the command is not allowed), set
them like this.

```cfg
[my.fancy.extension]
allowed_users = @user1:fancyserver.com
	@user2:otherserver.com
```


## Writing extensions

To extend a bot, either simply drop a .py-File into the modules folder, which contains
the code of your extension, and add its name to config like `[modules.myextension]`. Or if you want to develop your exension into a separate python package, give its full module path.

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