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
        # await self.load_playlists()
        if not self.check_music.is_running():
            self.check_music.start()
        if not self.check_members.is_running():
            self.check_members.start()
        print("Bot is now ONLINE", datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))           


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f'{ctx.message.content.split(" ")[0]} is not an available command. Type {self.prefix}help to get more information.')
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f'The command is on cooldown. Wait {error.retry_after:.2f} seconds.')
        elif isinstance(error, youtube_dl.DownloadError):
            await ctx.send(f'There is a unexpected error during the download of the song.')
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'A required argument is missing. ' + error.param.name)
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(f"The {error.argument} is not connected to a voice channel.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f'The provided arguments are not correct.')
        elif isinstance(error, exceptions.TooLongVideo):
            await ctx.send(f'{error.title} is more than an hour long. ' + error.duration)
        elif isinstance(error, discord.errors.Forbidden):
            await ctx.send("Error 403. The song could not be downloaded. Try again.")
        elif isinstance(error, exceptions.BotIsAlreadyPlaying):
            await ctx.send("Bot is already playing some music.")
        elif isinstance(error, exceptions.BotIsNotPlaying):
            await ctx.send("Bot is not playing some music at the moment.")
        elif isinstance(error, exceptions.QueueIsEmpty):
            await ctx.send(f'There are no songs in the music queue.')
        # elif isinstance(error, exceptions.PlaylistNotFound):
        #     await ctx.send(f'There is no playlist named: {error.pl_name}')
        elif isinstance(error, TimeoutError):
            await ctx.send("Expired [default = No]")
        # elif isinstance(error, exceptions.FileAlreadyExists):
        #     await ctx.send(f'A file named {error.file} already exists.')
        else:
            await self.append_error_log(error)
            await ctx.send('Unexpected error.')
            await self.reload_bot(ctx)










    @commands.command(name="p")
    async def p(self, ctx, *args):
        if len(args) <= 0:
            raise commands.MissingRequiredArgument("song name")
        if ctx.author.voice is None:
            raise exceptions.NotConnected("Bot")
        if self.voice is None:
            await self.connect(ctx)
        
        query = " ".join(args)
        self.queue.append(query)
        await ctx.send("Song added to the queue!")
        if not self.voice.is_playing():
            await self.play_music()


    @commands.command(name="stop")
    async def stop(self, ctx):
        await self.disconnect()


    @commands.command(name="skip")
    async def skip(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected(ctx.author)
        self.voice.stop()


    @commands.command(name="np")
    async def np(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected(ctx.author)
        if not self.voice.is_playing():
            raise exceptions.BotIsNotPlaying(self.voice.channel)
        await self.send_np_embed(ctx)


    @commands.command(name="queue")
    async def next(self, ctx):
        if len(self.queue) <= 0:
            raise exceptions.QueueIsEmpty(self.queue)
        await ctx.send(f"**Here's a list of the next songs**: \n[1] {self.played_songs[-1]} (now playing)\n" + "\n".join("[{}] {}".format(str(index + 2), song) for index, song in enumerate(self.queue)))


    @commands.command(name="offline")
    @commands.is_owner()
    async def offline(self, ctx):
        await ctx.send("Going offline! See ya later.")
        if self.voice is not None:
            await self.disconnect()
        await self.bot.close()


    @commands.command(name="pause")
    async def pause(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if not self.voice.is_playing():
            raise exceptions.BotIsNotPlaying()
        self.voice.pause()
        await ctx.send('Music paused.')


    @commands.command(name="resume")
    async def resume(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if self.voice.is_playing():
            raise exceptions.BotIsAlreadyPlaying()
        self.voice.resume()
        await ctx.send('Music resumed.')


    @commands.command(name="help")
    async def help(self, ctx, *args):
        embed = discord.Embed(color= discord.Colour.dark_teal())
        embed.add_field(name='Here\'s a github page containing all the "Music From YT!" bot info:', value='[Music From YT! - github.com](https://github.com/theLiuk23/Discord-bot-NEW)', inline=False)
        await ctx.send(embed=embed)


    @commands.command(name="vol")
    async def vol(self, ctx, *args):
        if len(args) == 0:
            await ctx.send(f"Volume is now set to {int(self.volume * 100)}")
        else:
            if not str.isdigit(args[0]):
                raise commands.BadArgument()
            volume = int(args[0])
            if volume < 0 or volume > 200:
                raise commands.BadArgument()
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
    @commands.command(name="reload")
    async def reload(self, ctx):
        await self.reload_bot()


    @commands.command(name="rm")
    async def rm(self, ctx, *args):
        if len(args) <= 0:
            raise commands.MissingRequiredArgument("song index")
        if not str.isdigit(args[0]):
            raise commands.BadArgument("The argument must be an integer rappresenting the index of the song you want to remove.")
        index = int(args[0]) - 1
        if len(self.queue) < index or index <= 0:
            raise commands.BadArgument(f"The queue does not contain a song at index {index}")
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


    async def append_error_log(self, error):
        with open("error_log.txt", "a") as file:
            time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            file.write(f"{time} - {str(error)}\n")