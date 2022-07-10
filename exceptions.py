import datetime


class OptionNotFound(BaseException):
    def __init__(self, *options):
        self.options = ' '.join(options)
    def message(self):
        return f"Option {self.option} was not found."


class NotConnected(BaseException):
    def __init__(self, author):
        self.author = author
    def message(self):
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