'''
This is the main python script that will be launched to make the bot online.
Here's a list of the functions it will do:
    - check if ffmpeg is already installed in the machine
    - read some useful varibles in the settings.ini file (hidden from the GitHub repository) like the bot token and the prefix
    - launch the bot instance with all the available commands.
Some functions like the one to install ffmpeg are made specifically for Linux; if you're using another OS please be aware of some possible problems.
If you want to get more information, please visit my GitHub Repository at https://github.com/theLiuk23/Discord-music-bot.
If you have any question, please write me at ldvcoding@gmail.com
'''


from discord.ext import commands
import pip
import configparser
import exceptions
import subprocess
import asyncio
import discord
import my_commands
import sys, os


config = configparser.RawConfigParser()
token = None
prefix = None
volume = None
lyrics = None
bot_name = None


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


async def initiate_bot():
    await bot.add_cog(my_commands.MusicBot(bot, prefix, float(volume), lyrics, bot_name))
    await bot.start(token)


if __name__ == "__main__":
    install_ffmpeg()
    token = read_setting("token")
    prefix = read_setting("prefix")
    volume = read_setting("volume")
    lyrics = read_setting("lyrics")
    bot_name = read_setting("name")
    activity = discord.Activity(type=discord.ActivityType.listening, name=f'music. {prefix}help')
    bot = commands.Bot(command_prefix=prefix, intents=discord.Intents.all(), activity=activity, help_command=my_commands.CustomHelpCommand())
    
    # create loop
    loop = asyncio.new_event_loop()
    # create a future
    asyncio.ensure_future(initiate_bot(), loop=loop)
    try:
        # loop runs until stop is called
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # stop and close loop
        loop.stop()
        sys.exit(0)