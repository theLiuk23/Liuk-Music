'''
This script is the class containing all the commands and the loops handled by the bot.
To get a list of all the available commands and how they work,
please either open the commands.txt file or visit my GitHub Repository at https://github.com/theLiuk23/Discord-music-bot.
If you have any question, please write me at ldvcoding@gmail.com
'''


from discord.ext import commands
from discord.ext import tasks
import asyncio
import datetime
import discord
import youtube_dl
import exceptions
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
                self.disconnect()
                return
            if len(self.voice.members) <= 1:
                self.check1 += 1
                 
        
    @tasks.loop(seconds=5)
    async def check_music(self):
        if self.voice is not None:
            if self.check2 >= 3:
                self.disconnect()
                return
            if not self.voice.is_playing():
                self.check2 += 1


    @commands.command(name="p")
    async def p(self, ctx, *args):
        if len(args) <= 0:
            raise commands.MissingRequiredArgument("song name")
        if ctx.author.voice is None:
            raise exceptions.NotConnected()
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
        # embed TODO


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
        self.voice = None
        self.check1, self.check2 = 0, 0
        self.played_songs = []
        self.queue = []


    async def connect(self, ctx):
        self.voice = await ctx.author.voice.channel.connect()
        await ctx.guild.change_voice_state(channel=self.voice.channel, self_mute=False, self_deaf=True)