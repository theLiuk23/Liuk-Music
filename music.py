'''
This script is the class containing all the commands and the loops handled by the bot.
To get a list of all the available commands and how they work,
please either open the commands.txt file or visit my GitHub Repository at https://github.com/theLiuk23/Discord-music-bot.
If you have any question, please write me at ldvcoding@gmail.com
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


class MusicCog(commands.Cog):
    def __init__(self, bot, prefix, volume):
        self.bot = bot
        self.prefix = prefix
        self.volume = volume
        self.check1, self.check2 = 0, 0
        self.voice = None
        self.song_info = None
        self.played_songs = []
        self.queue = []
        self.YTDL_OPTIONS = {
            'format': 'bestaudio',
            'ignoreerrors':'True',
            'noplaylist': 'True',
            'nowarnings': 'True',
            'quiet': 'True' }
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -hide_banner -loglevel error' }
        

    @tasks.loop(seconds=5)
    async def check_members(self):
        if self.voice is not None:
            if self.check1 >= 3:
                await self.disconnect()
                return
            if len(self.voice.channel.members) <= 1:
                self.check1 += 1
                 
        
    @tasks.loop(seconds=5)
    async def check_music(self):
        if self.voice is not None:
            if self.check2 >= 3:
                await self.disconnect()
                return
            if not self.voice.is_playing():
                self.check2 += 1






    @commands.Cog.listener()
    async def on_ready(self):
        if not self.check_music.is_running():
            self.check_music.start()
        if not self.check_members.is_running():
            self.check_members.start()
        print("Bot is now ONLINE", datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))           


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(error.args[0])
        else:
            await self.append_error_log(error, ctx.author, handled=False)
            await ctx.send("An unexpected error occured. If it persists please contact the owner of the bot:\n" +
                            "**Discord:** Liuk Del Valun #3966\n" + 
                            "**Email:** ldvcoding@gmail.com")


    async def cog_command_error(self, ctx, error):
        await self.append_error_log(error.message(), error.author, handled=True)
        await ctx.send(error.message())









    @commands.command(help="It seach on YouTube the first result with the query input by the user and plays that video's audio in the user's voice channel.",
                    aliases=["play", "reproduce", "rec", "suona", "riproduci", "musica"])
    async def p(self, ctx, *query):
        if len(query) <= 0:
            raise exceptions.MissingRequiredArgument("query", ctx.author)
        if ctx.author.voice is None:
            raise exceptions.NotConnected("Bot")
        if self.voice is None:
            await self.connect(ctx)
        query = " ".join(query)
        self.queue.append(query)
        await ctx.send("Song added to the queue!")
        if not self.voice.is_playing():
            await self.play_music()    


    @commands.command(help="It disconnects the bot from its voice channel.",
                    aliases=["disconnect", "shut up", "basta", "zitto", "citu", "disconnetti", "disconnettiti"])
    async def stop(self, ctx):
        await self.disconnect()


    @commands.command(help="It stops the current playing song to play the next song.",
                    aliases=["next", "pass", "prossima", "salta"])
    async def skip(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        self.voice.stop()


    @commands.command(name="np", help="It shows some information about the current playing song.",
                    aliases=["now playing", "info", "song info", "informazioni", "informazione"])
    async def np(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if not self.voice.is_playing():
            raise exceptions.BotIsNotPlaying(self.voice.channel, ctx.author)
        await self.send_np_embed(ctx)


    @commands.command(name="queue", help="It shows a list of songs that are going to be played soon.",
                    aliases=["next songs", "upcoming", "future", "coda", "scaletta"])
    async def next(self, ctx):
        if len(self.queue) <= 0:
            raise exceptions.QueueIsEmpty(self.queue, ctx.author)
        await ctx.send(f"**Here's a list of the next songs**: \n[1] {self.played_songs[-1]} (now playing)\n" + "\n".join("[{}] {}".format(str(index + 2), song) for index, song in enumerate(self.queue)))


    @commands.command(name="offline", help="It makes the bot go offline (You must be the owner).",
                    aliases=["shutdown", "away", "spegni"])
    @commands.is_owner()
    async def offline(self, ctx):
        await ctx.send("Going offline! See ya later.")
        if self.voice is not None:
            await self.disconnect()
        await self.bot.close()


    @commands.command(name="pause", help="It pauses the music.", aliases=["pausa"])
    async def pause(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if not self.voice.is_playing():
            raise exceptions.BotIsNotPlaying(ctx.author)
        self.voice.pause()
        await ctx.send('Music paused.')


    @commands.command(name="resume", help="It resumes the music.", aliases=["riprendi", "ricomincia"])
    async def resume(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if self.voice.is_playing():
            raise exceptions.BotIsAlreadyPlaying(ctx.author)
        self.voice.resume()
        await ctx.send('Music resumed.')


    @commands.command(name="vol", help="It sets or gets the music volume.",
                    aliases=["v", "volume"])
    async def vol(self, ctx, volume):
        if volume is None:
            await ctx.send(f"Volume is now set to {int(self.volume * 100)}")
        else:
            if not str.isdigit(volume):
                raise exceptions.BadArgumentType(volume, type(volume), int, ctx.author)
            volume = int(volume)
            if volume < 0 or volume > 200:
                raise exceptions.BadArgument(str(volume), "Greater than 200 or lower than 0", ctx.author)
            self.volume = float(volume / 100)
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
        await self.reload_bot()


    @commands.command(name="rm", help="It removes a song from the queue.")
    async def rm(self, ctx, index):
        if index is None:
            raise exceptions.MissingRequiredArgument("song index", ctx.author)
        if not str.isdigit(index):
            raise exceptions.BadArgumentType(index, type(index), int, ctx.author)
        index = int(index) - 1
        if len(self.queue) <= 0:
            raise exceptions.QueueIsEmpty(self.queue, ctx.author)
        if len(self.queue) < index or index <= 0:
            raise exceptions.BadArgument(str(index + 1), f"Greater than {len(self.queue)} or lower than 1", ctx.author)
        await ctx.send(f"'{self.queue[index - 1]}' removed from queue.")
        self.queue.pop(index - 1)











    async def play_music(self):
        if len(self.queue) <= 0:
            await self.disconnect()
        with youtube_dl.YoutubeDL(self.YTDL_OPTIONS) as ytdl:
            video = ytdl.extract_info("ytsearch:%s" % self.queue[0], download=False)['entries'][0]
            self.song_info = {'source': video['formats'][0]['url'],
                            'title': video['title'],
                            'duration': video['duration'],
                            'channel': video['channel'],
                            'thumbnails': video['thumbnails'],
                            'views': video['view_count'],
                            'url': video['webpage_url'] }
        if self.song_info['duration'] > 60 * 60 * 2:
            raise exceptions.TooLongVideo()
        self.played_songs.append(self.queue.pop(0)) # moves current song from queue to old songs
        self.voice.play(discord.FFmpegPCMAudio(self.song_info['source'], **self.FFMPEG_OPTIONS), after = self.after)
        self.voice.source = discord.PCMVolumeTransformer(self.voice.source, volume=self.volume)

    
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
        await ctx.send("The bot is now relaoding.")
        await self.bot.close()
        os.execv(sys.executable, ['python3'] + ['main.py'])


    async def send_np_embed(self, ctx):
        embed = discord.Embed(title="**__Now playing__**")
        embed.set_image(url=self.song_info['thumbnails'][-1]['url'])
        embed.add_field(name="Title", value=self.song_info['title'], inline = True)
        embed.add_field(name="Channel", value=self.song_info['channel'], inline = True)
        embed.add_field(name="Views", value=f"{self.song_info['views']:,}", inline = True)
        # embed.add_field(name="Time Stamp", value=f'{time_stamp} ({percentage}%)', inline = True)
        embed.add_field(name="Duration", value=time.strftime('%H:%M:%S', time.gmtime(self.song_info['duration'])), inline = True)
        embed.add_field(name="Link", value=f"[YouTube]({self.song_info['url']})")
        await ctx.send(embed=embed)


    async def append_error_log(self, error, author, handled=False):
        with open("error_log.txt", "a") as file:
            time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            file.write(f"{author.name} - {time} | {str(error)}\n")




class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()


    # help command
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help command")
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_signature(c) for c in filtered]
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        await self.get_destination().send(embed=embed)


    # help <command> command
    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Command: '**{self.get_command_signature(command)}**'")
        embed.add_field(name="Function", value=command.help)
        alias = command.aliases
        if alias:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)