import datetime
from lib2to3.pytree import Base


class OptionNotFound(BaseException):
    def __init__(self, *options):
        self.options = ' '.join(options)
    def message(self):
        return f"Option {self.option} was not found."


class NotConnected(BaseException):
    def __init__(self, author):
        self.author = author
    def message(self):
        if self.author == "Bot":
            return f"The bot is not connected to a voice channel."
        return f"{self.author.name} is not connected to a voice channel."


class TooLongVideo(BaseException):
    def __init__(self, title, duration):
        self.title = title
        self.duration = duration
    def message(self):
        return f"The video titled '{self.title}' is too long: {datetime.datetime.fromtimestamp(self.duration).strftime('%H hours %M minutes and %S seconds.')}"


class BotIsNotPlaying(BaseException):
    def __init__(self, channel):
        self.channel = channel
    def message(self):
        return f"The bot is connected to {self.channel.name} but is playing no music."


class BotIsAlreadyPlaying(BaseException):
    def __init__(self, channel):
        self.channel = channel
    def message(self):
        return f"The bot is already playing some music in '{self.channel.name}' channel."


class QueueIsEmpty(BaseException):
    def __init__(self, queue):
        self.queue = queue
    def message(self):
        return f"There are no songs in the music queue."