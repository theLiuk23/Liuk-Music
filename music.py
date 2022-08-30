'''
This script is the class containing all the commands and the loops handled by the bot.
To get a list of all the available commands and how they work,
please either open the commands.txt file or visit my GitHub Repository at https://github.com/theLiuk23/Discord-music-bot.
If you have any question, please write me at ldvcoding@gmail.com
'''

'''
This script is structured as follows:
    - imports
    - loops
    - listeners
    - commands
    - functions
    - CustomHelpCommand
'''

'''
These are compulsory libraries that the bot needs in order to work.
To install all the dependencies:
    open a terminal window (ctrl + alt + T)
    change directory to the project folder (e.g.: $ cd Downloads/Discord-music-bot)
    run the following command: $ pip install -r requirements.txt
'''

from discord.ext import commands
from discord.ext import tasks
import datetime, time
import configparser
import youtube_dl
import exceptions
import asyncio
import discord
import os, sys
import inspect



class MusicBot(commands.Cog):
    def __init__(self, bot, prefix, volume, bot_name):
        self.bot = bot # instance of commands.Bot class
        self.bot_name = bot_name
        self.prefix = prefix # bot prefix [default=!]
        self.volume_value = volume # music volume (between 0.0 and 2.0)
        self.check1, self.check2 = 0, 0 # number of times self.check_members() and self.check_music() are triggered
        self.bool_loop = False # bool if bot has to play the same song 
        self.voice = None # instance of the VoiceClient class containing the info about the channel where's the bot has connected
        self.song_info = None # dictionary containing the info of the current playing song
        self.votes = []
        self.played_songs = [] # list containing the titles of already played songs
        self.queue = [] # list containing the titles of the songs which are going to be played
        self.playlists = [] # list of all the saved playlists' names
        self.exceptions = [] # list containing the name of all the classes in "exceptions.py" file
        self.YTDL_OPTIONS = { # options for youtube_dl library
            'format': 'bestaudio',
            'ignoreerrors':'True',
            'noplaylist': 'True',
            'nowarnings': 'True',
            'quiet': 'True',
            'cookiefile': "~/.local/bin/youtube.com_cookies.txt"}
        self.FFMPEG_OPTIONS = { # options for FFMPEG library
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -hide_banner -loglevel error' }
        

    @tasks.loop(seconds=5)
    async def check_members(self):
        '''
        Function called every 5 seconds that checks whether the bot is alone in the voice channel.\n
        If the bot is alone in the voice channel, the variable self.check1 will increase by 1.
        After 3 times in a row, the bot will disconnect from the voice channel.
        '''
        if self.voice is not None:
            if self.check1 >= 3:
                await self.disconnect()
                return
            if len(self.voice.channel.members) <= 1:
                self.check1 += 1
            else:
                self.check1 = 0
                 
        
    @tasks.loop(seconds=5)
    async def check_music(self):
        '''
        Function called every 5 seconds that checks whether the bot is still playing some music.\n
        If the bot is not playing music anymore, the variable self.check2 will increase by 1.
        After 3 times in a row, the bot will disconnect from the voice channel.
        '''
        if self.voice is not None:
            if self.check2 >= 3:
                await self.disconnect()
                return
            if not self.voice.is_playing() and not self.voice.is_paused():
                self.check2 += 1
            else:
                self.check2 = 0




    @commands.Cog.listener()
    async def on_ready(self):
        '''
        Listener triggered when the bot goes online.\n
        It prints in the console the current date and it starts the bot loops:
            - self.check_music()
            - self.check_members()
        '''
        if not self.check_music.is_running():
            self.check_music.start()
        if not self.check_members.is_running():
            self.check_members.start()
        await self.load_playlists()
        print("-"*52)
        print(f'Bot "{self.bot_name}" is now ONLINE -', datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))



    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        '''
        Listener triggered when a discord exception has raised.
        If there is a unhandled exception, it sends an "about me" message and saves the error in the "error_log.txt" file
        Handled exceptions:
            - CommandNotFound
            - CheckFailure
            - CheckAnyFailure
            - CommandOnCooldown
            - NotOwner
            - ChannelNotFound
            - MissingPermissions
        '''
        for _, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj) and isinstance(error, obj):
                await ctx.send(obj().message())
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"This is not an available command.\nType {self.prefix}help to get a list of the available commands.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("Check failure error.")
        elif isinstance(error, commands.CheckAnyFailure):
            await ctx.send("Check any failure error.")
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("The command is currently disabled.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"The command is on cooldown. Wait {error.retry_after:0.2f} seconds.")
        elif isinstance(error, commands.NotOwner):
           await ctx.send("You must be the owner to run this command.")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(f"The channel '{error.argument}' was not found.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have the required permissions to run this command: \n{0}".format('\n'.join(error.missing_perms)))
        else:
            await self.append_error_log(error, ctx.author)
            await ctx.send("An unexpected error occured. If it persists please contact the owner of the bot:\n" +
                            "**Discord:** Liuk Del Valun #3966\n" + 
                            "**Email:** ldvcoding@gmail.com")






    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="play", help="It seaches on YouTube the first result with the given query and plays it in the user's voice channel.",
                    aliases=["p", "song", "music"])
    async def play(self, ctx, *query):
        '''
        It appends the user query to the queue list\n
        If the bot is not already playing in a voice channel, it runs the self.play_music() function.
        '''
        if len(query) <= 0:
            await ctx.send(exceptions.MissingRequiredArgument("query", ctx.author).message())
            return
        if ctx.author.voice is None:
            await ctx.send(exceptions.NotConnected(ctx.author).message())
            return
        if self.voice is None:
            await self.connect(ctx)
        query = " ".join(query)
        self.queue.append(query)
        await ctx.send(f"Song '{query}' added to the queue!")
        if not self.voice.is_playing():
            result = await self.play_music()    
            if result is False:
                await ctx.send("The video is either a playlist or it is too long. (more than 2 hours long)")


    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="pl", help="It plays all the songs in a saved playlist.",
                    aliases=["album", "set", "collection", "col"])
    async def pl(self, ctx, *name:str):
        name = "_".join(name)
        if name is None:
            await ctx.send(exceptions.MissingRequiredArgument("playlist name", ctx.author).message())
            return
        name = name.strip()
        name = name.replace(' ', '_')
        if name.lower() not in self.playlists:
            await ctx.send(exceptions.BadArgument("playlist name", "The playlist does not exist.").message())
            return
        
        with open(f'playlists/{name}.ini', 'r') as file:
            for line in file.readlines():
                self.queue.append(line.strip("\n"))

        await ctx.send(f"Playlist '{name}' added to the queue!")

        await self.connect(ctx)
        result = await self.play_music()
        if result is False:
            await ctx.send("The video is either a playlist or it is too long. (more than 2 hours long)")


    @commands.command(name="stop", help="It disconnects the bot from its voice channel.",
                    aliases=["stfu", "disconnect", "out", "away"])
    async def stop(self, ctx):
        '''
        It disconnects the bot from the voice channel.\n
        Aka it runs the self.disconnect() function.
        '''
        await self.disconnect()


    @commands.command(name="skip", help="It stops the current playing song to play the next song.",
                    aliases=["next", "incoming"])
    async def skip(self, ctx):
        '''
        It stops the current playing song (so the next one in the queue will start).
        '''
        if self.voice is None:
            await ctx.send(exceptions.NotConnected("Bot").message())
            return
        self.voice.stop()


    @commands.cooldown(1, 10, commands.BucketType.user)  # 0 == default = global
    @commands.command(name="nowplaying", help="It shows some information about the current playing song.",
                    aliases=["np", "info"])
    async def nowplaying(self, ctx):
        '''
        It sends an embed containing all the info about the current playing song.
        '''
        if self.voice is None:
            await ctx.send(exceptions.NotConnected("Bot").message())
            return
        if not self.voice.is_playing():
            await ctx.send(exceptions.BotIsNotPlaying(self.voice.channel, ctx.author).message())
            return
        await self.send_np_embed(ctx)


    @commands.command(name="queue", help="It shows a list of songs that are going to be played soon.",
                    aliases=["upcoming", "list"])
    async def next(self, ctx):
        '''
        It shows a list containing all the queries in the 'self.queue' list
        '''
        if len(self.queue) <= 0:
            await ctx.send(exceptions.QueueIsEmpty(self.queue, ctx.author).message())
            return
        await ctx.send(f"**Here's a list of the next songs**: \n[1] {self.played_songs[-1]} (now playing)\n" + "\n".join("[{}] {}".format(str(index + 2), song) for index, song in enumerate(self.queue)))


    @commands.command(name="offline", help="It makes the bot go offline (You must be the owner).")
    @commands.is_owner()
    async def offline(self, ctx):
        '''
        It makes the bot disconnect from the voice channel and go offline.\n
        You must be the owner.
        '''
        await ctx.send("Going offline! See ya later.")
        if self.voice is not None:
            await self.disconnect()
        await self.bot.close()


    @commands.command(name="pause", help="It pauses the music.", aliases=["break"])
    async def pause(self, ctx):
        '''
        It pauses the music in the voice channel.
        '''
        if self.voice is None:
            await ctx.send(exceptions.NotConnected("Bot").message())
            return
        if not self.voice.is_playing():
            await ctx.send(exceptions.BotIsNotPlaying(ctx.author).message())
            return
        self.voice.pause()
        await ctx.send('Music paused.')


    @commands.command(name="resume", help="It resumes the music.", 
                    aliases=["takeback", "playagain"])
    async def resume(self, ctx):
        '''
        It resumes the music in the voice channel.
        '''
        if self.voice is None:
            await ctx.send(exceptions.NotConnected("Bot").message())
            return
        if self.voice.is_playing():
            await ctx.send(exceptions.BotIsAlreadyPlaying(ctx.author).message())
            return
        self.voice.resume()
        await ctx.send('Music resumed.')


    @commands.command(name="volume", help="It sets or gets the music volume.",
                    aliases=["vol", "loudness", "sound"])
    async def volume(self, ctx, volume:int):
        '''
        It sets or gets the music volume.
        '''
        if len(volume) == 0:
            await ctx.send(f"Volume is now set to {int(self.volume_value * 100)}")
        else:
            if not str.isdigit(volume):
                await ctx.send(exceptions.BadArgumentType(volume, type(volume), int, ctx.author).message())
                return
            volume = int(volume)
            if volume < 0 or volume > 200:
                await ctx.send(exceptions.BadArgument(str(volume), "Greater than 200 or lower than 0", ctx.author).message())
                return
            self.volume_value = float(volume / 100)
            await ctx.send(f"Volume is now set to {volume}%")
            if self.voice is not None:
                self.voice.source.volume = float(volume / 100)
            config = configparser.RawConfigParser()
            config.read("settings.ini")
            with open("settings.ini", "w") as file:
                config.set("variables", "volume", str(float(volume / 100)))
                config.write(file)


    @commands.is_owner()
    @commands.command(name="reload", help="It makes the bot go offline and online again (You must be the owner).")
    async def reload(self, ctx):
        '''
        It makes the bot go offline and online again. (see self.reload_bot() function)
        You must be the owner.
        '''
        await self.reload_bot(ctx)


    @commands.command(name="clear", help="It clears out the queue",
                    aliases=["erase", "wipe"])
    async def clear(self, ctx):
        '''
        It clears out the queue
        '''
        self.queue = []
        await ctx.send("Queue erased!")


    @commands.command(name="rm", help="It removes a song from the queue by index.",
                    aliases=["remove", "eliminate", "delete"])
    async def rm(self, ctx, index:int):
        '''
        It removes a query from the self.queue list by index.
        '''
        if len(index) == 0:
            await ctx.send(exceptions.MissingRequiredArgument("song index", ctx.author).message())
            return
        if not str.isdigit(index):
            await ctx.send(exceptions.BadArgumentType(index, type(index), int, ctx.author).message())
            return
        index = int(index) - 1
        if len(self.queue) <= 0:
            await ctx.send(exceptions.QueueIsEmpty(self.queue, ctx.author).message())
            return
        if len(self.queue) < index or index <= 0:
            await ctx.send(exceptions.BadArgument(str(index + 1), f"Greater than {len(self.queue)} or lower than 1", ctx.author).message())
            return
        await ctx.send(f"'{self.queue[index - 1]}' removed from queue.")
        self.queue.pop(index - 1)


    @commands.command(name="playlist", help="It creates a playlist with all the played, playing and on-queue songs.",
                    aliases=["remember", "save"])
    async def playlist(self, ctx, *name:str):
        '''
        It creates a playlist with all the played, playing and on-queue songs.
        '''
        name = "_".join(name)
        if len(name) == 0:
            await ctx.send("Here's a list of the saved playlists:\n" + "\n".join("[{}] {}".format(i, pl) for i, pl in enumerate(self.playlists, start=1)))
            return
        name = name.strip()
        if name in self.playlists:
            await ctx.send(exceptions.BadArgument(name, "The playlist already exists.").message())
            return
        if len(self.played_songs) == 0 or len(self.queue) == 0:
            await ctx.send(exceptions.NoSongsToBeSaved(ctx.author).message())
            return

        with open(f"playlists/{name}.ini", "w") as file:
            for song in (self.played_songs + self.queue):
                file.write(f"{song}\n")

        await self.load_playlists()


    @commands.command(name="loop", help="If set to true, it plays the same song in loop",
                    aliases=["playback", "again"])
    async def loop(self, ctx):
        '''
        It changes a bool if the bot has to
        '''
        self.bool_loop = not self.bool_loop
        if self.bool_loop == True:
            await ctx.send("The song will be played on loop.")
        else:
            await ctx.send("Loop is now disabled.")


    @commands.command(name="vote", help="It counts how many users voted to skip the song (more than 50% votes needed)",
                    aliases=["poll"])
    async def vote(self, ctx):
        '''
        It sums up user votes
        when votes are more than 50% than members it skips song
        '''
        author = ctx.author
        if self.voice is None:
            await ctx.send(exceptions.NotConnected(ctx.author).message())
            return
        members_count = len(self.voice.channel.members) - 1

        if author.id not in self.votes:
            self.votes.append(author.id)
            await ctx.send(f'{author.name}, your vote has been recorded. (current votes: {len(self.votes)}/{members_count})')
        else:
            await ctx.send(f'{author.name}, you have already voted.')
            return

        if len(self.votes) > (members_count / 2):
            if self.voice is None:
                await ctx.send(exceptions.NotConnected("Bot").message())
                return
            await ctx.send(f"Votes are {len(self.votes)}/{members_count}. Skipping to the next song.")
            self.votes = []
            self.voice.stop()





    async def play_music(self):
        if len(self.queue) <= 0:
            await self.disconnect()
        with youtube_dl.YoutubeDL(self.YTDL_OPTIONS) as ytdl:
            video = ytdl.extract_info("ytsearch:%s" % self.queue[0], download=False)['entries'][0]
            if 'audio only' not in video['formats'][0]['format']:
                return False
            self.song_info = {'source': video['formats'][0]['url'],
                            'title': video['title'],
                            'duration': video['duration'],
                            'channel': video['channel'],
                            'thumbnails': video['thumbnails'],
                            'views': video['view_count'],
                            'url': video['webpage_url'] }
        if self.song_info['duration'] > 60 * 60 * 2:
            return False
        if self.bool_loop is False:
            self.played_songs.append(self.queue.pop(0)) # moves current song from queue to old songs
        self.voice.play(discord.FFmpegPCMAudio(self.song_info['source'], **self.FFMPEG_OPTIONS), after = self.after)
        self.voice.source = discord.PCMVolumeTransformer(self.voice.source, volume=self.volume_value)

    
    def after(self, error):
        coro = self.play_music()
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result()
        except:
            fut.cancel()


    async def disconnect(self):
        if self.voice is not None:
            if self.voice.is_connected():
                await self.voice.disconnect()
        self.check_music.stop()
        self.check_members.stop()
        self.voice = None
        self.check1, self.check2 = 0, 0
        self.played_songs = []
        self.queue = []


    async def connect(self, ctx):
        self.voice = await ctx.author.voice.channel.connect()
        await ctx.guild.change_voice_state(channel=self.voice.channel, self_mute=False, self_deaf=True)

    
    async def reload_bot(self, ctx):
        await ctx.send("The bot is now reloading.")
        await self.bot.close()
        os.execv(sys.executable, ['python3'] + ['main.py'])


    async def send_np_embed(self, ctx):
        embed = discord.Embed(title="**__Now playing__**")
        embed.set_image(url=self.song_info['thumbnails'][-1]['url'])
        embed.add_field(name="Title", value=self.song_info['title'], inline = True)
        embed.add_field(name="Channel", value=self.song_info['channel'], inline = False)
        embed.add_field(name="Views", value=f"{self.song_info['views']:,}", inline = True)
        embed.add_field(name="Duration", value=time.strftime('%H:%M:%S', time.gmtime(self.song_info['duration'])), inline = True)
        embed.add_field(name="Link", value=f"[YouTube]({self.song_info['url']})")
        await ctx.send(embed=embed)


    async def append_error_log(self, error, author):
        with open("error_log.txt", "a") as file:
            text = f"{author.name} - {time} | {str(error)}\n"
            time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            file.write(text)
        print(f"EXCEPTION: '{text}'")


    async def load_playlists(self):
        self.playlists = []

        for playlist in os.listdir("playlists"):
            self.playlists.append(playlist.removesuffix(".ini"))



class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()


    # help command
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help command")
        embed.set_footer(text=f"HINT: Type {MusicBot().prefix}help <command name> to get more information about the single command.")
        for cog in mapping:
            names = [command.name for command in mapping[cog]]
            helps = [command.help for command in mapping[cog]]
            dictionary = dict(zip(names, helps))
            for key in sorted(dictionary):
                embed.add_field(name=key, value=dictionary[key])
        await self.get_destination().send(embed=embed)


    # help <command> command
    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Command: '**{str(command).upper()}**'")
        embed.add_field(name="Function", value=command.help)
        if command.aliases:
            embed.add_field(name="Aliases", value=f'**{command}**, ' + ", ".join(command.aliases), inline=False)
        await self.get_destination().send(embed=embed)