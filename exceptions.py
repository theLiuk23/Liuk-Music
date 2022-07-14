from discord.ext import commands
import discord
import datetime



class OptionNotFound(commands.CommandError):
    def __init__(self, option:str):
        self.options = option
        self.message = f"Option {self.option} was not found."


class NotConnected(commands.CommandError):
    def __init__(self, author:discord.Member=None):
        self.author = author
        if self.author == "Bot":
            self.message = f"The bot is not connected to a voice channel."
        else:
            self.message = f"{self.author.name}, you are not connected to a voice channel."


class TooLongVideo(commands.CommandError):
    def __init__(self, title:str, duration:int, author:discord.Member=None):
        self.title = title
        self.duration = duration
        self.author = author
        self.message = f"The video titled '{self.title}' is too long: {datetime.datetime.fromtimestamp(self.duration).strftime('%H hours %M minutes and %S seconds.')}"


class BotIsNotPlaying(commands.CommandError):
    def __init__(self, channel:discord.VoiceChannel, author:discord.Member=None):
        self.channel = channel
        self.author = author
        self.message = f"The bot is connected to {self.channel.name} but is playing no music."


class BotIsAlreadyPlaying(commands.CommandError):
    def __init__(self, channel:discord.VoiceChannel, author:discord.Member=None):
        self.channel = channel
        self.author = author
        self.message = f"The bot is already playing some music in '{self.channel.name}' channel."


class QueueIsEmpty(commands.CommandError):
    def __init__(self, queue:list, author:discord.Member=None):
        self.queue = queue
        self.author = author
        self.message = f"There are no songs in the music queue."

    
class MissingRequiredArgument(commands.CommandError):
    def __init__(self, parameter:str, author:discord.Member=None):
        self.parameter = parameter
        self.author = author
        self.message = f"A required argument is missing: '{self.parameter}'"


class BadArgumentType(commands.CommandError):
    def __init__(self, parameter:str, wrong_type: type, correct_type: type, author:discord.Member=None):
        self.parameter = parameter
        self.wrong_type = wrong_type
        self.correct_type = correct_type
        self.author = author
        self.message = f"The provided argument '{self.parameter}' is type '{self.wrong_type.__name__}' but it need to be type '{self.correct_type.__name__}'"


class BadArgument(commands.CommandError):
    def __init__(self, parameter:str, reason:str, author:discord.Member=None):
        self.parameter = parameter
        self.reason = reason
        self.author = author
        self.message = f"The parameter {self.parameter} is a bad argument: {self.reason}"


class CommandNotFound(commands.CommandError):
    def __init__(self):
        self.message = f"The command was not found! LOL"