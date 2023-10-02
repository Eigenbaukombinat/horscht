

import datetime
import requests
import logging
import os
import json
import hashlib


class Voting(object):

    def __init__(self, room, question, *answers, mode='multi'):
        self.question = question
        self.answers = answers
        self.votes = dict()
        self.mode = mode
        self.room = room

    @classmethod
    def from_file(klass, filehandle):
        """construct instance from saved data."""
        fdata = filehandle.read()
        if not fdata:
            return
        data = json.loads(fdata)
        instance = klass(data['room'], data['question'], *data['answers'])
        instance.votes = data['votes']
        return instance

    def save(self):
        """Save data to file."""
        fn = f'voting_{self.room}.json'
        with open(fn, 'w') as votedata:
            votedata.write(json.dumps({
                'room': self.room,
                'question': self.question,
                'answers': self.answers,
                'votes': self.votes
                }))

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


def get_current_voting(bot, room):
    if not hasattr(bot, 'VOTINGS'):
        bot.VOTINGS = dict()
    voting = bot.VOTINGS.get(room)
    if voting is None:
        fn = f'voting_{room}.json'
        #try to load from file
        if os.path.isfile(fn):
            with open(fn) as voting_data_file:
                bot.VOTINGS[room] = voting_from_file = Voting.from_file(voting_data_file)
            return voting_from_file
    return voting

def start_voting(bot, room, question, answers):
    bot.VOTINGS[room] = voting = Voting(room, question, *answers)
    voting.save()


def reset_voting(bot, room):
    del bot.VOTINGS[room]
    fn = f'voting_{room}.json'
    if os.path.isfile(fn):
        os.unlink(fn)

def get_room_key(event):
    room = event.get('room_id')
    return hashlib.sha224(room.encode('utf8')).hexdigest()

def get_user_key(event):
    user = event['sender']
    return hashlib.sha224(user.encode('utf8')).hexdigest()


def vote(event, message, bot, args, config):
    """Get infos about running vote, or cast/edit a vote."""
    # First check if there is a voting running:
    room = get_room_key(event)
    current_voting = get_current_voting(bot, room)
    if current_voting is None:
        bot.reply(event, 'There is no running voting, use !startvote to create one.')
        return
    sender = get_user_key(event)
    msg = event['content']['body'][5:].strip()
    if msg == '':
        reply = f'Question: {current_voting.question}\nPossible answers:\n'
        for num, answer in enumerate(current_voting.answers):
            reply += f'    {answer}\n'
        if current_voting.mode == 'multi':
            reply += f'You can vote for multiple options, by comma separating them like: !vote option1, option2'
        bot.reply(event, reply)
        return
    result = current_voting.vote(sender, msg)
    current_voting.save()
    if result is not None:
        bot.reply(event, result)
        return
    bot.reply(event, 'Your vote has been counted.')

def startvote(event, message, bot, args, config):
    """Start a vote. First Parameter is the question, any
    following the choices."""
    room = get_room_key(event)
    current_voting = get_current_voting(bot, room)
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
    start_voting(bot, room, question, answers)

def endvote(event, message, bot, args, config):
    """Ends a running vote, displaying the results."""
    room = get_room_key(event)
    current_voting = get_current_voting(bot, room)
    if current_voting is None:
        bot.reply(event, 'There is no running voting, use !startvote to create one.')
        return
    msg = event['content']['body']
    if 'yes' not in msg:
        bot.reply(event, f'Are you sure you want to end the vote and display results? (!endvote yes to continue)')
        return
    totalvotes = current_voting.total_votes()
    reply = f'I hereby present you the results for the vote on "{current_voting.question}":\n'
    for number, answer in enumerate(current_voting.answers):
        reply += f'    {answer}: {current_voting.results_total(answer)} Votes\n'
    reply += 'Thanks for using me, cu next time! :)'
    bot.reply(event, reply)
    reset_voting(bot, room)


CMDS = { '!startvote': startvote,
        '!endvote': endvote,
        '!vote': vote }
