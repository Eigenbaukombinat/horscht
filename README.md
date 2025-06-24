# horscht

A simple and extensible Matrix chatbot that can respond to commands, MQTT messages, and run scheduled tasks. Perfect for automating tasks in your Matrix rooms!

## Features

- 🤖 **Command responses**: React to specific commands typed in Matrix rooms
- 📡 **MQTT integration**: Respond to IoT device messages and sensor data
- ⏰ **Scheduled tasks**: Run periodic tasks like reminders or status updates
- 🔒 **Access control**: Restrict commands to specific users or rooms
- 🔌 **Easy to extend**: Write custom modules without deep Python knowledge

## Installation

```bash
git clone https://github.com/Eigenbaukombinat/horscht.git
cd horscht
python3 -m venv .
bin/pip install -r requirements.txt
cp config.ini.example config.ini
```

## Configuration and starting

Edit `config.ini` to match your Matrix server settings. You can leave the `mqtt_broker` setting empty to disable MQTT support if you don't need it.

```bash
bin/python main.py
```

The bot will automatically connect to your Matrix server and start responding to configured commands.

## Understanding the Configuration File

The `config.ini` file controls how your bot behaves. Here's what each section does:

### Bot Settings (`[bot]` section)
```ini
[bot]
server = https://matrix.example.com     # Your Matrix server URL
username = mybot                        # Bot's Matrix username (without @)
display_name = My Bot                   # Name shown in Matrix rooms
password = your_secure_password         # Bot's Matrix password
mqtt_broker = localhost                 # MQTT server (optional, leave empty to disable)
```

### Module Configuration
Each module (extension) you want to use gets its own section. The section name tells the bot which module to load:

```ini
[modules.helloworld]        # Loads the helloworld module from the modules/ folder
[modules.quote]             # Loads the quote module from the modules/ folder
[my.custom.extension]       # Loads a module from a Python package you installed
```

## Access Control: Who Can Use What

You can control which users and rooms can use specific commands from each module.

### Restricting Commands to Specific Rooms

Use `allowed_rooms` to limit where commands work. Users can only use these commands in the specified rooms:

```ini
[modules.helloworld]
allowed_rooms = #general:matrix.example.com
    #announcements:matrix.example.com
```

### Giving Special Access to Specific Users

Use `allowed_users` to give certain users permission to use commands anywhere, even in rooms where the command is normally restricted:

```ini
[modules.quote]
allowed_users = @admin:matrix.example.com
    @moderator:matrix.example.com
```

### Example: Public vs Private Commands

```ini
# Anyone can use this in the specified rooms
[modules.helloworld]
allowed_rooms = #general:matrix.example.com

# Only specific users can use this, but they can use it anywhere
[modules.quote]
allowed_users = @admin:matrix.example.com
allowed_rooms =    # Empty = not allowed in any room for regular users
```


## Writing Your Own Modules (Extensions)

Creating custom functionality for your bot is easy! You can write modules that respond to commands, MQTT messages, or run on a schedule.

### Getting Started

1. **Create a new file**: Save it as `modules/mymodule.py` in your bot directory
2. **Add configuration**: Add a `[modules.mymodule]` section to your `config.ini`
3. **Restart the bot**: Your new module will be loaded automatically

### Module Structure

Every module is just a Python file with special variables that tell the bot what to do:

- `CMDS` - Dictionary of commands the module responds to
- `MSGS` - Dictionary of MQTT topics the module responds to  
- `CRON` - Function to run on a schedule

You only need to include the variables for the features you want to use.

## Creating Command Responses

Commands let users interact with your bot by typing specific messages in Matrix rooms.

### Basic Command Example

Create `modules/mygreetings.py`:

```python
def say_hello(event, message, bot, args, config):
    """Greets the user who typed the command."""
    # Get the user who sent the command
    sender = event['sender']
    
    # Send a reply back to the same room
    bot.reply(event, f"Hello {sender}! Nice to meet you!")

def say_goodbye(event, message, bot, args, config):
    """Says goodbye to the user."""
    bot.reply(event, "Goodbye! Have a great day!")

# Register your commands - the key is what users type, the value is your function
CMDS = {
    '!hello': say_hello,
    '!goodbye': say_goodbye
}
```

Add to your `config.ini`:
```ini
[modules.mygreetings]
# Anyone can use these commands in any room the bot is in
```

Now users can type `!hello` or `!goodbye` in Matrix rooms where your bot is present!

### Understanding Command Functions

Every command function receives exactly these 5 parameters:

- **event**: Information about the Matrix message (who sent it, which room, etc.)
- **message**: The full command message that was typed
- **bot**: The bot object - use `bot.reply()` to respond
- **args**: List of words typed after the command (e.g., `!hello world` → `args = ['world']`)
- **config**: Settings from your module's config.ini section

### Advanced Command Example

```python
def weather_command(event, message, bot, args, config):
    """Shows weather for a city. Usage: !weather <city_name>"""
    
    # Check if user provided a city name
    if not args:
        bot.reply(event, "Please specify a city: !weather London")
        return
    
    # Join all arguments to handle cities with spaces
    city = ' '.join(args)
    
    # You could call a weather API here
    # For this example, we'll just echo back
    response = f"The weather in {city} is sunny! 🌞"
    bot.reply(event, response)

def fortune_command(event, message, bot, args, config):
    """Tells your fortune."""
    import random
    
    fortunes = [
        "Today will be a great day!",
        "You will find something you lost.",
        "A pleasant surprise awaits you.",
        "Good news is coming your way."
    ]
    
    fortune = random.choice(fortunes)
    bot.reply(event, f"🔮 Your fortune: {fortune}")

CMDS = {
    '!weather': weather_command,
    '!fortune': fortune_command
}
```

## Responding to MQTT Messages (IoT Integration)

MQTT lets your bot react to messages from IoT devices, sensors, or other systems. This is perfect for home automation or monitoring setups!

### Setting Up MQTT

1. **Configure MQTT broker**: Set `mqtt_broker = your.mqtt.server.com` in your `config.ini`
2. **Leave empty to disable**: Set `mqtt_broker =` (empty) if you don't need MQTT

### Basic MQTT Example

Create `modules/myiotbot.py`:

```python
def handle_temperature(message, data, client, bot, config):
    """Announces temperature readings to Matrix rooms."""
    
    # Get the temperature value from the MQTT message
    temperature = message.payload.decode('utf8')
    
    # Create a friendly announcement
    announcement = f"🌡️ Living room temperature: {temperature}°C"
    
    # Send to all rooms the bot is in
    for room_id in bot.client.rooms:
        bot.client.rooms[room_id].send_notice(announcement)

def handle_doorbell(message, data, client, bot, config):
    """Alerts when someone rings the doorbell."""
    
    # The doorbell just sends "ring" when pressed
    if message.payload.decode('utf8') == 'ring':
        alert = "🔔 Someone is at the door!"
        
        # Only send to rooms specified in config (see below)
        alert_rooms = config.get('alert_rooms', '').split('\n')
        for room_address in alert_rooms:
            if room_address.strip():  # Skip empty lines
                # Find the room by its address
                for room_id, room in bot.client.rooms.items():
                    if room.canonical_alias == room_address.strip():
                        room.send_notice(alert)
                        break

# Register your MQTT topic handlers
MSGS = {
    'home/sensors/temperature': handle_temperature,
    'home/doorbell/status': handle_doorbell
}
```

Add to your `config.ini`:
```ini
[modules.myiotbot]
# Specify which rooms should get doorbell alerts
alert_rooms = #alerts:matrix.example.com
    #family:matrix.example.com
```

### Understanding MQTT Functions

Every MQTT handler function receives exactly these 5 parameters:

- **message**: The MQTT message object
  - `message.payload.decode('utf8')` - The actual message content as text
  - `message.topic` - Which MQTT topic this came from
- **data**: MQTT user data (usually not needed)
- **client**: The MQTT client object (use this to publish MQTT messages back)
- **bot**: The bot object - use this to send messages to Matrix rooms
- **config**: Settings from your module's config.ini section

### Advanced MQTT Example with Response

```python
def smart_switch_control(message, data, client, bot, config):
    """Controls smart switches via MQTT and reports status."""
    
    command = message.payload.decode('utf8')
    
    if command == 'status':
        # Publish a request for switch status
        client.publish('home/switches/living_room/get', 'state')
        
    elif command in ['on', 'off']:
        # Control the switch
        client.publish('home/switches/living_room/set', command)
        
        # Announce the action in Matrix
        action_msg = f"💡 Living room lights turned {command}"
        for room_id in bot.client.rooms:
            bot.client.rooms[room_id].send_notice(action_msg)

def switch_status_response(message, data, client, bot, config):
    """Reports switch status back to Matrix."""
    
    status = message.payload.decode('utf8')
    status_emoji = "💡" if status == "on" else "🌑"
    
    report = f"{status_emoji} Living room lights are {status}"
    
    # Send to specific rooms only
    report_rooms = config.get('status_rooms', '').split('\n')
    for room_address in report_rooms:
        if room_address.strip():
            for room_id, room in bot.client.rooms.items():
                if room.canonical_alias == room_address.strip():
                    room.send_notice(report)
                    break

MSGS = {
    'home/switches/living_room/command': smart_switch_control,
    'home/switches/living_room/status': switch_status_response
}
```

## Creating Scheduled Tasks (Automation)

Scheduled tasks let your bot perform actions automatically at regular intervals, like sending reminders, checking system status, or posting daily updates.

### Basic Scheduled Task Example

Create `modules/myreminders.py`:

```python
import datetime

def daily_reminder(bot, config):
    """Sends a daily reminder at 9 AM."""
    
    # Check if it's 9 AM (only run the reminder at this hour)
    current_hour = datetime.datetime.now().hour
    if current_hour != 9:
        return  # Not time yet, do nothing
    
    # Get the reminder message from config
    reminder_text = config.get('reminder_message', 'Don\'t forget to check your tasks!')
    
    # Get which rooms should receive reminders
    reminder_rooms = config.get('reminder_rooms', '').split('\n')
    
    # Send the reminder
    for room_address in reminder_rooms:
        if room_address.strip():  # Skip empty lines
            for room_id, room in bot.client.rooms.items():
                if room.canonical_alias == room_address.strip():
                    room.send_notice(f"⏰ Daily Reminder: {reminder_text}")
                    break

# Register your scheduled function
CRON = daily_reminder
```

Add to your `config.ini`:
```ini
[modules.myreminders]
# Run every hour to check if it's time for the daily reminder
secs = 3600
reminder_message = Time for your daily standup meeting!
reminder_rooms = #general:matrix.example.com
    #team:matrix.example.com
```

### Understanding Scheduled Functions

Every scheduled function receives exactly these 2 parameters:

- **bot**: The bot object - use this to send messages to Matrix rooms
- **config**: Settings from your module's config.ini section (including the `secs` timing)

### Common Timing Examples

```ini
secs = 60        # Every minute
secs = 300       # Every 5 minutes  
secs = 1800      # Every 30 minutes
secs = 3600      # Every hour
secs = 21600     # Every 6 hours
secs = 65000     # Maximum value (about 18 hours)
```

**Important Note**: The maximum value for `secs` is 65001. For longer intervals like daily or weekly tasks, your function should run frequently (e.g., every hour) but check the current time internally to decide when to actually perform the action.

### Advanced Scheduled Task Example

```python
import datetime
import requests

def system_status_check(bot, config):
    """Checks system status and reports issues."""
    
    try:
        # Check if a website is responding
        website = config.get('website_to_check', 'https://example.com')
        response = requests.get(website, timeout=10)
        
        if response.status_code == 200:
            status_msg = f"✅ {website} is responding normally"
        else:
            status_msg = f"⚠️ {website} returned status code {response.status_code}"
            
    except requests.exceptions.RequestException as e:
        status_msg = f"❌ {website} is not responding: {str(e)}"
    
    # Add timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {status_msg}"
    
    # Send to monitoring rooms only
    monitor_rooms = config.get('monitor_rooms', '').split('\n')
    for room_address in monitor_rooms:
        if room_address.strip():
            for room_id, room in bot.client.rooms.items():
                if room.canonical_alias == room_address.strip():
                    room.send_notice(full_message)
                    break

def weekly_summary(bot, config):
    """Sends a weekly summary every Sunday at 8 PM."""
    
    now = datetime.datetime.now()
    
    # Check if today is Sunday (weekday 6) and it's 8 PM
    if now.weekday() == 6 and now.hour == 20:
        summary = """
📊 Weekly Summary:
• Bot has been running smoothly
• All scheduled tasks completed
• Ready for the new week!
"""
        
        # Send to all rooms
        for room_id in bot.client.rooms:
            bot.client.rooms[room_id].send_notice(summary)

# You can only have ONE CRON function per module
# If you need multiple schedules, create separate modules
CRON = system_status_check
```

## Recurring Reminders Module

The bot includes a built-in recurring reminders module that allows room members to create weekly reminders that are automatically sent at specified days and times.

### Features

- **Create reminders**: Any room member can create reminders with custom text, weekday, and time
- **Automatic delivery**: Reminders are sent automatically every week at the specified time
- **Room-specific**: Reminders are tied to the room where they were created
- **User management**: Users can list and delete their own reminders
- **German language support**: Supports German weekday names

### Usage

**Create a reminder:**
```
!reminder <weekday> <time> <message>
```

**Examples:**
```
!reminder montag 09:00 Team-Meeting im Konferenzraum
!reminder freitag 17:30 Arbeitszeit-Ende!
!reminder sonntag 20:00 Tatort schauen 📺
```

**List reminders:**
```
!reminder list
```

**Delete a reminder:**
```
!reminder delete <number>
```

### Supported Weekdays

German: `montag`, `dienstag`, `mittwoch`, `donnerstag`, `freitag`, `samstag`, `sonntag`
English: `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`

### Time Format

Use 24-hour format: `HH:MM` (e.g., `14:30` for 2:30 PM)

### Configuration

Add to your `config.ini`:
```ini
[modules.recurring_reminders]
# Check every minute for reminders to send
secs = 60
```

### Data Storage

Reminders are stored in a `reminders.json` file in the bot's directory and persist across bot restarts.

## Learning from Existing Modules

Your bot installation comes with several example modules you can study and modify:

### Simple Examples
- **`modules/helloworld.py`** - Basic command that replies with "Hello world"
- **`modules/quote.py`** - Sends messages to specific rooms (demonstrates room finding)

### Advanced Examples  
- **`modules/reminder.py`** - MQTT integration for calendar reminders
- **`modules/zammad.py`** - Scheduled task that checks a ticket system
- **`modules/vote.py`** - Complex voting system with multiple commands

### Quick Start: Modify an Existing Module

1. **Copy a simple module**:
   ```bash
   cp modules/helloworld.py modules/mybot.py
   ```

2. **Edit your copy**:
   ```python
   def my_command(event, message, bot, args, config):
       """My custom command that does something cool."""
       bot.reply(event, "This is my custom response!")

   CMDS = {'!mycmd': my_command}
   ```

3. **Add to config.ini**:
   ```ini
   [modules.mybot]
   # Any custom settings for your module
   ```

4. **Restart the bot** - Your command `!mycmd` is now available!

### Understanding Python Basics (For Non-Programmers)

Don't worry if you're not a Python expert! Here are the key concepts you need:

#### Variables and Text
```python
# Store text in variables
my_message = "Hello there!"
user_name = "Alice"

# Combine text with f-strings (put f before the quotes)
greeting = f"Welcome {user_name}!"  # Results in: "Welcome Alice!"
```

#### Lists and Loops
```python
# A list of items
room_list = ["#general:matrix.com", "#alerts:matrix.com"]

# Do something for each item in the list
for room_name in room_list:
    print(f"Processing room: {room_name}")
```

#### If Statements (Making Decisions)
```python
# Check conditions and do different things
if len(args) == 0:
    bot.reply(event, "Please provide some arguments!")
elif args[0] == "help":
    bot.reply(event, "Here's how to use this command...")
else:
    bot.reply(event, f"You said: {args[0]}")
```

#### Functions (Your Commands)
```python
def my_function_name(parameters):
    """This text explains what the function does."""
    # Your code goes here
    return something  # Optional

# For bot commands, always use exactly these parameters:
def my_command(event, message, bot, args, config):
    # Your command logic here
    pass
```

## Getting Help and Support

### Debugging Your Modules

1. **Check the logs**: Run your bot with `--debug` to see detailed information:
   ```bash
   bin/python main.py --debug
   ```

2. **Common error messages**:
   - `Module not found` - Check your filename and config.ini section name
   - `IndentationError` - Python is picky about spaces; use consistent indentation
   - `KeyError` - You're trying to access a config value that doesn't exist

3. **Test your module step by step**:
   - Start with a simple command that just replies with text
   - Add complexity gradually
   - Use `print()` statements to debug (they'll show in the bot logs)

### Python Resources for Beginners

- **Python Tutorial**: https://docs.python.org/3/tutorial/
- **Learn Python Basics**: https://www.codecademy.com/learn/learn-python-3
- **Python for Beginners**: https://www.python.org/about/gettingstarted/

### Community and Contributions

- Report bugs or request features on the project's issue tracker
- Share your cool modules with the community
- Ask questions in Matrix rooms where the bot is being used

## Next Steps

1. **Start simple**: Copy `helloworld.py` and make small changes
2. **Read existing modules**: See how they solve problems you want to solve
3. **Experiment**: Try adding new commands to existing modules
4. **Build gradually**: Start with basic text responses, then add complexity
5. **Share your work**: Help others by sharing useful modules you create

Remember: every expert was once a beginner. Don't be afraid to experiment and learn by doing!
