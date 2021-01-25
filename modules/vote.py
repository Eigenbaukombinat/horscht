import datetime
import requests
import logging



class Voting(object):

    def __init__(self, question, *answers, mode='multi'):
        self.question = question
        self.answers = answers
        self.votes = dict()
        self.mode = mode

    def vote(self, uid, choice):
        if self.mode == 'single' and ',' in choice:
            return 'You can only vote for one option here.'
        edit = False
        if choice.endswith('edit'):
            edit = True
            choice = choice[:-4]
        choices = choice.split(',')
        if uid in self.votes and not edit:
            existing_vote = ', '.join(self.votes.get(uid))
            return f'You already voted {existing_vote}. Type "!vote {choice} edit" to change your vote to {choice}.'
        for choice in choices:
            if choice.strip() not in self.answers:
                return f'{choice} is not a valid choice. Type !vote without anything to see the options.'
        self.votes[uid] = [c.strip() for c in choices]

    def total_votes(self):
        return len(self.votes.keys())

    def results_total(self, answer):
        """the number of votes on speficied answer"""
        count = 0
        for uid, votes in self.votes.items():
            for vote in votes:
                if vote == answer:
                    count += 1
        return count


def vote(event, message, bot, args, config):
    """Get infos about running vote, or cast/edit a vote."""
    # First check if there is a voting running:
    if not hasattr(bot, 'VOTING'):
        bot.VOTING = None
    current_voting = bot.VOTING
    if current_voting is None:
        bot.reply(event, 'There is no running voting, use !startvote to create one.')
        return
    sender = event['sender']
    msg = event['content']['body'][5:].strip()
    if msg == '':
        bot.reply(event, f'Question: {current_voting.question}')
        for num, answer in enumerate(current_voting.answers):
            bot.reply(event, f'Answer {num+1}: {answer}')
        if current_voting.mode == 'multi':
            bot.reply(event, f'You can vote for multiple options, by comma separating them like: !vote option1, option2')
        return
    result = current_voting.vote(sender, msg)
    if result is not None:
        bot.reply(event, result)
        return
    bot.reply(event, 'Your vote has been counted.')

def startvote(event, message, bot, args, config):
    """Start a vote. First Parameter is the question, any
    following the choices."""
    if not hasattr(bot, 'VOTING'):
        bot.VOTING = None
    current_voting = bot.VOTING
    if current_voting is not None:
        bot.reply(event, 'There is already a voting in progress, use !endvote to end that first.')
        return
    msg = event['content']['body']
    parts = msg.split()
    if len(parts) < 3:
        bot.reply(event, 'Not enough arguments. We need a question and at least one answer to start things. Please use backslashes to escape whitespace!')
        return
    question = parts[1]
    answers = parts[2:]
    bot.VOTING = Voting(question, *answers)

def endvote(event, message, bot, args, config):
    """Ends a running vote, displaying the results."""
    if not hasattr(bot, 'VOTING'):
        bot.VOTING = None
    current_voting = bot.VOTING
    if current_voting is None:
        bot.reply(event, 'There is no running voting, use !startvote to create one.')
        return
    msg = event['content']['body']
    if 'yes' not in msg:
        bot.reply(event, f'Are you shure you want to end the vote and display results? (!endvote yes to continue)')
        return
    totalvotes = current_voting.total_votes()
    bot.reply(event, f'I hereby present you the results for the vote on "{current_voting.question}:')
    for number, answer in enumerate(current_voting.answers):
        bot.reply(event, f'Answer {number}: {answer} – {current_voting.results_total(answer)}')
    bot.reply(event, 'Thanks for using me, cu next time! :)')
    bot.VOTING = None


CMDS = { '!startvote': startvote,
        '!endvote': endvote,
        '!vote': vote }
