'''
This is the main python script that will be launched to make the bot online.
Here's a list of the functions it will do:
    - check if ffmpeg is already installed in the machine
    - read some useful varibles in the settings.ini file (hidden from the GitHub repository) like the bot token and the prefix
    - launch the client instance with all the available commands.
Some functions like the one to install ffmpeg are made specifically for Linux; if you're using another OS please be aware of some possible problems.
If you want to get more information, please visit my GitHub Repository at https://github.com/theLiuk23/Discord-music-bot.
If you have any question, please write me at ldvcoding@gmail.com
'''


from discord.ext import commands
import configparser
import exceptions
import subprocess
import discord
import music
import os


config = configparser.RawConfigParser()
intents = discord.Intents.default()
intents.members = True
intents.guilds = True


def read_setting(setting:str) -> str:
    config.read("settings.ini")
    if not setting in config.options("variables"):
        raise exceptions.OptionNotFound(setting)
    return config.get("variables", setting)


def install_ffmpeg():
    try:
      subprocess.check_output(['which', 'ffmpeg'])
    except subprocess.CalledProcessError:
        return os.system("sudo apt-get install ffmpeg -y")


if __name__ == "__main__":
    install_ffmpeg()
    token = read_setting("token")
    prefix = read_setting("prefix")
    volume = read_setting("volume")
    if token is None or prefix is None or volume is None:
        raise exceptions.OptionNotFound(token, prefix, volume)
    activity = discord.Activity(type=discord.ActivityType.listening, name=f'music. {prefix}help')
    client = commands.Bot(command_prefix=prefix, intents=intents, activity=activity, help_command=None)
    client.add_cog(music.MusicCog(client, prefix, float(volume)))
    client.run(token, bot=True)