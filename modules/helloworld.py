def hello_world(event, message, bot, args):
    """Says hello to the world."""
    bot.reply(event, "Hello world.")


CMDS = {'!hello': hello_world}
