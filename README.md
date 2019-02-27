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

Then, edit config.ini to your needs and start the bot.

```bash
bin/python main.py
```

## Development mode

If you work on a specific extension module (see below), you can restrict to bot to only react on the commands specified in that module. (This prevents the bot from answering multiple times if its running elsewhere.)

```bash
bin/python main.py --dev mymodule
```

## Extension

To extend a bot, simply drop a .py-File into the modules folder, which must contain the following:

**The function which is called when your command is spelled in a room the bot is in.**

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

After the definition of the function, you have to register it together with the command.

```python
CMDS = { '!hello', my_function }
```


