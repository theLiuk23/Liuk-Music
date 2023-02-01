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
import my_commands
import datetime
import discord




class MusicBot(commands.Cog):
    def __init__(self, bot, bot_prefix, volume, lyrics, bot_name):
        self.bot = bot # instance of commands.Bot class
        self.bot_name = bot_name
        self.bot_prefix = bot_prefix # bot bot_prefix [default=!]
        self.lyrics_token = lyrics # token to get lyrics from genius.com
        self.volume_value = volume # music volume (between 0.0 and 2.0)
        self.functions = my_commands.MyCommands(bot, bot_prefix, volume, lyrics, bot_name)
        self.check1, self.check2 = 0, 0 # number of times self.check_members() and self.check_music() are triggered
        self.voice = None # instance of the VoiceClient class containing the info about the channel where's the bot has connected


    def cog_unload(self):
        self.check_members.cancel()
        self.check_music.cancel()
        

    @tasks.loop(seconds=5)
    async def check_members(self):
        '''
        Function called every 5 seconds that checks whether the bot is alone in the voice channel.\n
        If the bot is alone in the voice channel, the variable self.check1 will increase by 1.
        After 3 times in a row, the bot will disconnect from the voice channel.
        '''
        if self.voice is None:
            return
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
        if self.voice is None:
            return
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
        await self.functions.load_playlists()
        print("-"*52)
        print(f'Bot "{self.bot_name}" is now ONLINE -', datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))



    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        '''
        Listener triggered when a discord exception has raised.
        If there is a unhandled exception, it sends an "about me" message and saves the error in the "error_log.txt" file
        Handled exceptions:
            - Custom Exceptions (see exceptions.py script)
            - CommandNotFound
            - CheckFailure
            - CheckAnyFailure
            - CommandOnCooldown
            - NotOwner
            - ChannelNotFound
            - MissingPermissions
        '''
        if isinstance(error, commands.CommandError):
            # if hasattr, it's a custom exception
            if hasattr(error, "message"):
                await ctx.send(error.message())
                return
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"This is not an available command.\nType {self.bot_prefix}help to get a list of the available commands.")
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
            await self.functions.append_error_log(error, ctx.author)
            await ctx.send("An unexpected error occured. If it persists please contact the owner of the bot:\n" +
                            "**Discord:** Liuk Del Valun #3966\n" + 
                            "**Email:** ldvcoding@gmail.com\n"+
                            "If you do so, you'll help the owner to fix the bugs. Thank you.")






    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="play", help="It seaches on YouTube the first result with the given query and plays it in the user's voice channel.",
                    aliases=["p", "song", "music"])
    async def play(self, ctx, *query):
        '''
        It appends the user query to the queue list\n
        If the bot is not already playing in a voice channel, it runs the self.play_music() function.
        '''
        await self.functions.play(ctx, *query)


    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(name="album", help="It plays all the songs in a saved playlist.",
                    aliases=["pl", "set", "collection", "col"])
    async def album(self, ctx, *name:str):
        await self.functions.album(ctx, *name)


    @commands.command(name="stop", help="It disconnects the bot from its voice channel.",
                    aliases=["stfu", "disconnect", "out", "away"])
    async def stop(self, ctx):
        '''
        It disconnects the bot from the voice channel.\n
        Aka it runs the self.disconnect() function.
        '''
        await self.functions.stop(ctx)
        


    @commands.command(name="skip", help="It stops the current playing song to play the next song.",
                    aliases=["next", "incoming"])
    async def skip(self, ctx):
        '''
        It stops the current playing song (so the next one in the queue will start).
        only the owner can directly skip the song. Other users will simply add a vote.
        '''
        await self.functions.skip(ctx)


    @commands.cooldown(1, 10, commands.BucketType.user)  # 0 == default = global
    @commands.command(name="nowplaying", help="It shows some information about the current playing song.",
                    aliases=["np", "info"])
    async def nowplaying(self, ctx):
        '''
        It sends an embed containing all the info about the current playing song.
        '''
        await self.functions.nowplaying(ctx)


    @commands.command(name="queue", help="It shows a list of songs that are going to be played soon.",
                    aliases=["upcoming", "list"])
    async def next(self, ctx):
        '''
        It shows a list containing all the queries in the 'self.queue' list
        '''
        await self.functions.next(ctx)


    @commands.command(name="offline", help="It makes the bot go offline (You must be the owner).")
    @commands.is_owner()
    async def offline(self, ctx):
        '''
        It makes the bot disconnect from the voice channel and go offline.\n
        You must be the owner.
        '''
        await self.functions.offline(ctx)


    @commands.command(name="pause", help="It pauses the music.", aliases=["break"])
    async def pause(self, ctx):
        '''
        It pauses the music in the voice channel.
        '''
        await self.functions.pause(ctx)


    @commands.command(name="resume", help="It resumes the music.", 
                    aliases=["takeback", "playagain"])
    async def resume(self, ctx):
        '''
        It resumes the music in the voice channel.
        '''
        await self.functions.resume(ctx)


    @commands.command(name="volume", help="It sets or gets the music volume.",
                    aliases=["vol", "loudness", "sound"])
    async def volume(self, ctx, *volume:int):
        '''
        It sets or gets the music volume.
        '''
        await self.functions.volume(ctx, *volume)


    @commands.command(name="clear", help="It clears out the queue",
                    aliases=["erase", "wipe"])
    async def clear(self, ctx):
        '''
        It clears out the queue
        '''
        await self.functions.clear(ctx)


    @commands.command(name="remove", help="It removes a song from the queue by index.",
                    aliases=["rm", "eliminate", "delete"])
    async def remove(self, ctx, index = None):
        '''
        It removes a query from the self.queue list by index.
        '''
        await self.functions.remove(ctx, index)


    @commands.command(name="playlist", help="It creates a playlist with all the played, playing and on-queue songs.",
                    aliases=["remember", "save"])
    async def playlist(self, ctx, *name:str):
        '''
        It creates a playlist with all the played, playing and on-queue songs.
        '''
        await self.functions.playlist(ctx, *name)


    @commands.command(name="loop", help="If set to true, it plays the same song in loop",
                    aliases=["playback", "again"])
    async def loop(self, ctx):
        '''
        It changes a bool if the bot has to
        '''
        await self.functions.loop(ctx)


    @commands.command(name="vote", help="It adds up a vote to skip the song (more than 50% votes needed)",
                    aliases=["poll"])
    async def vote(self, ctx):
        '''
        It sums up user votes
        when votes are more than 50% than members it skips song
        '''
        await self.functions.vote_skip(ctx)


    @commands.command(name="lyrics", help="It searches for the lyrics of the currently playing song",
                    aliases=["text", "speech", "karaoke"])
    async def lyrics(self, ctx, *title):
        '''
        It searches for the lyrics of the currently playing song
        '''
        await self.functions.lyrics(ctx, *title)


    @commands.command(name="prefix", help="It changes the bot bot_prefix",
                    aliases=["pref", "char"])
    async def prefix(self, ctx, new = None):
        '''
        It changes the bot bot_prefix
        '''
        await self.functions.change_prefix(ctx, new)






class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()
        
        
    # help command
    async def send_bot_help(self, mapping):
        import main
        bot_prefix = main.read_setting("prefix")
        embed = discord.Embed(title="Help command")
        embed.set_footer(text=f"HINT: Type '{bot_prefix}help <command name>' to get more information about the single command.")
        for cog in mapping:
            ''' creating dict containing:
                    keys = commands' names
                    values = commands' help '''
            dictionary = dict(zip([command.name.capitalize() for command in mapping[cog]], [command.help for command in mapping[cog]]))
            for key in sorted(dictionary):
                embed.add_field(name=f"__{key}__", value=dictionary[key])
        await self.get_destination().send(embed=embed)


    # help <command> command
    async def send_command_help(self, command):
        embed = discord.Embed(title=f"Command: '**{str(command).upper()}**'")
        embed.add_field(name="Function", value=command.help)
        if command.aliases:
            embed.add_field(name="Aliases", value=f'**{command}**, ' + ", ".join(command.aliases), inline=False)
        await self.get_destination().send(embed=embed)