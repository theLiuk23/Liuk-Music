import discord
import youtube_dl
import exceptions
import asyncio
import configparser
import datetime, time
import lyricsgenius
import sys, os
import math


class Commands:
    def __init__(self, bot, prefix, volume, lyrics, bot_name):
        self.bot = bot # instance of commands.Bot class
        self.prefix = prefix # bot prefix [default=!]
        self.lyrics_token = lyrics # token to get lyrics from genius.com
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


    async def play_music(self):
        if len(self.queue) <= 0:
            await self.disconnect()
        with youtube_dl.YoutubeDL(self.YTDL_OPTIONS) as ytdl:
            video = ytdl.extract_info("ytsearch:%s" % self.queue[0], download=False)['entries'][0]
            if 'audio only' not in video['formats'][0]['format']:
                raise exceptions.BadArgument(video['formats'][0]['format'], "The video does not have an audio file or is a playlist", None)
            self.song_info = {'source': video['formats'][0]['url'],
                            'title': video['title'],
                            'duration': video['duration'],
                            'channel': video['channel'],
                            'thumbnails': video['thumbnails'],
                            'views': video['view_count'],
                            'url': video['webpage_url'] }
        if self.song_info['duration'] > 60 * 60 * 2:
            raise exceptions.BadArgument(self.song_info['duration'], "The video is longer than 2 hours", None)
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
            time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            if author is None:
                text = f"Unknown - {time} | {str(error)}\n"
            text = f"{author.name} - {time} | {str(error)}\n"
            file.write(text)
        print(f"EXCEPTION: '{text}'")


    async def load_playlists(self):
        self.playlists = []

        for playlist in os.listdir("playlists"):
            self.playlists.append(playlist.removesuffix(".ini"))


    async def vote_skip(self, ctx):
        author = ctx.author
        if self.voice is None:
            raise exceptions.NotConnected(ctx.author)
        members_count = len(self.voice.channel.members) - 1

        if author.id not in self.votes:
            self.votes.append(author.id)
            await ctx.send(f'{author.name}, your vote has been recorded. (current votes: {len(self.votes)}/{members_count})')
        else:
            await ctx.send(f'{author.name}, you have already voted.')
            return

        if len(self.votes) > (members_count / 2):
            if self.voice is None:
                raise exceptions.NotConnected("Bot")
            await ctx.send(f"Votes are {len(self.votes)}/{members_count}. Skipping to the next song.")
            self.votes = []
            self.voice.stop()


    async def search_lyrics(self, ctx, message, song):
        for emoji in ('👍', '👎'):
            await message.add_reaction(emoji)

        def check(reaction, user):
            return str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'
        try:
            reaction = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            result = False
        
        if reaction[0].emoji == '👍': result = True
        else: result = False

        if result:
            if len(song.lyrics) > 6000:
                await ctx.send(f"Lyrics exceeds maximum size of 6000.\nHere's a link to open up a site with the entire lyrics: {song.url}")
                return
            embed = discord.Embed(title=f"Lyrics for: '{song.full_title}'")
            for page in range(math.ceil(len(song.lyrics) / 1024)):
                embed.add_field(name=f"Page{page+1}", value=song.lyrics[1023*page:page*1023 + 1023:])
            await ctx.send(embed=embed)


    async def play(self, ctx, *query):
        if len(query) <= 0:
            raise exceptions.MissingRequiredArgument("query", ctx.author)
        if ctx.author.voice is None:
            raise exceptions.NotConnected(ctx.author)
        if self.voice is None:
            await self.connect(ctx)
        query = " ".join(query)
        self.queue.append(query)
        if query.startswith("http"):
            await ctx.send("Link added to the queue!")
        else:
            await ctx.send(f"Song '{query}' added to the queue!")
        if not self.voice.is_playing():
            result = await self.play_music()    
            if result is False:
                await ctx.send("The video is either a playlist or it is too long. (more than 2 hours long)")


    async def album(self, ctx, *name):
        if len(name) == 0:
            raise exceptions.MissingRequiredArgument("playlist name", ctx.author)
        if ctx.author.voice is None:
            raise exceptions.NotConnected(ctx.author)
        name = "_".join(name)
        name = name.strip()
        name = name.replace(' ', '_')
        if name.lower() not in self.playlists:
            raise exceptions.BadArgument("playlist name", "The playlist does not exist.")
        
        with open(f'playlists/{name}.ini', 'r') as file:
            for line in file.readlines():
                self.queue.append(line.strip("\n"))

        await ctx.send(f"Playlist '{name}' added to the queue!")

        await self.connect(ctx)
        result = await self.play_music()
        if result is False:
            await ctx.send("The video is either a playlist or it is too long. (more than 2 hours long)")
    

    async def stop(self, ctx):
        if self.voice is None:
            return
        await ctx.send(f"Disconnecting from '{self.voice.channel.name}'")
        await self.disconnect()


    async def skip(self, ctx):
        if ctx.author == ctx.guild.owner:
            if self.voice is None:
                raise exceptions.NotConnected("Bot")
            self.voice.stop()
        else:
            await self.vote_skip(ctx)


    async def nowplaying(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if not self.voice.is_playing():
            raise exceptions.BotIsNotPlaying(self.voice, ctx.author)
        await self.send_np_embed(ctx)


    async def next(self, ctx):
        if len(self.queue) <= 0:
            raise exceptions.QueueIsEmpty(self.queue, ctx.author)
        await ctx.send(f"**Here's a list of the next songs**: \n[1] {self.played_songs[-1]} (now playing)\n" + "\n".join("[{}] {}".format(str(index + 2), song) for index, song in enumerate(self.queue)))


    async def offline(self, ctx):
        await ctx.send("Going offline! See ya later.")
        if self.voice is not None:
            await self.disconnect()
        await self.bot.close()


    async def pause(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if not self.voice.is_playing():
            raise exceptions.BotIsNotPlaying(ctx.voice, ctx.author)
        self.voice.pause()
        await ctx.send('Music paused.')


    async def resume(self, ctx):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if self.voice.is_playing():
            raise exceptions.BotIsAlreadyPlaying(ctx.author)
        self.voice.resume()
        await ctx.send('Music resumed.')


    async def volume(self, ctx):
        if len(volume) == 0:
            await ctx.send(f"Volume is now set to {int(self.volume_value * 100)}")
        else:
            volume = str(volume[0])
            if not str.isdigit(volume):
                raise exceptions.BadArgumentType(volume, type(volume), int, ctx.author)
            volume = int(volume)
            if volume < 0 or volume > 200:
                raise exceptions.BadArgument(str(volume), "Greater than 200 or lower than 0", ctx.author)
            self.volume_value = float(volume / 100)
            await ctx.send(f"Volume is now set to {volume}%")
            if self.voice is not None:
                self.voice.source.volume = float(volume / 100)
            config = configparser.RawConfigParser()
            config.read("settings.ini")
            with open("settings.ini", "w") as file:
                config.set("variables", "volume", str(float(volume / 100)))
                config.write(file)


    async def clear(self, ctx):
        self.queue = []
        await ctx.send("Queue erased!")


    async def remove(self, ctx, index):
        if len(index) == 0:
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


    async def playlist(self, ctx, *name):
        name = "_".join(name)
        if len(name) == 0:
            await ctx.send("Here's a list of the saved playlists:\n" + "\n".join("[{}] {}".format(i, pl) for i, pl in enumerate(self.playlists, start=1)))
            return
        name = name.strip()
        if name in self.playlists:
            raise exceptions.BadArgument(name, "The playlist already exists.")
        if len(self.played_songs) == 0 or len(self.queue) == 0:
            raise exceptions.NoSongsToBeSaved(ctx.author)

        with open(f"playlists/{name}.ini", "w") as file:
            for song in (self.played_songs + self.queue):
                file.write(f"{song}\n")

        await self.load_playlists()


    async def loop(self, ctx):
        self.bool_loop = not self.bool_loop
        if self.bool_loop == True:
            await ctx.send("The song will be played on loop.")
        else:
            await ctx.send("Loop is now disabled.")


    async def lyrics(self, ctx, *title):
        if self.voice is None:
            raise exceptions.NotConnected("Bot")
        if self.voice.is_playing() is False:
            raise exceptions.BotIsNotPlaying(ctx.voice, ctx.author)

        if len(title) == 0:
            title = self.song_info['title']
            title = title.split("ft")[0]
            title = title.split("official")[0]
            title = title.split("explicit")[0]
            title = title.strip("[]().,;:-_")
        else:
            title = " ".join(title)

        genius = lyricsgenius.Genius(access_token=self.lyrics_token, verbose=False)
        song = genius.search_song(title)

        if song is None:
            await ctx.send(f"I searched for '{title}', but I couldn't find any lyrics.\n" +
                            f"Try to write {self.prefix}lyrics <custom title> to look for lyrics manually.")
            return
        
        embed = discord.Embed(title="I found this song's lyrics. Is it correct?")
        embed.add_field(name="Title", value=song.full_title)
        embed.add_field(name="Author", value=song.artist)
        embed.set_image(url=song.song_art_image_thumbnail_url)

        message = await ctx.send(embed=embed)
        await self.search_lyrics(ctx, message, song)