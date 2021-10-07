import discord
import functools
from discord.ext import commands

import asyncio
import youtube_dl

from apiclient.discovery import build

import config

youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'proxy': f'{config.PROXY_URL}:{config.PROXY_PORT}',
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': 'musics/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'geo-bypass': True,
    'verbose': False
}

ffmpeg_options = {
    'before_options': '-loglevel fatal -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

class mido_music(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
        self.youtube = build("youtube", "v3", developerKey=config.YOUTUBE_KEY)

    #get_data
    async def get_data(self, ctx, key, download=False):
        loop = self.bot.loop or asyncio.get_event_loop()

        try:
            data = await loop.run_in_executor(None, functools.partial(self.ytdl.extract_info, key, download=download))
        except Exception as exc:
            raise exc

        return data

    #get_info
    async def get_info(self, ctx, url, download=True):
        data = await self.get_data(ctx, url, download)

        result = {
            "type": "Download" if download else "Stream",
            "url": data["url"],
            "id": data["id"],
            "webpage_url": data["webpage_url"],
            "title": data["title"],
            "thumbnail": data["thumbnail"],
            "uploader": data["uploader"],
            "uploader_url": data["uploader_url"],
            "payload": data,
            "request": ctx.author.id
        }

        return result

    #stop
    @commands.command(name="stop", description="音楽の再生を停止し、キューを削除してからボイスチャンネルから退出します。", usage="rsp!stop", aliases=["leave"])
    async def stop(self, ctx):
        msg = await ctx.send("> 処理中...")

        if not ctx.author.voice:
            return await msg.edit(content=f"> ボイスチャンネルに接続してね！")
        if not ctx.guild.voice_client:
            return await msg.edit(content=f"> ボイスチャンネルに接続していないため、使えないよ！")
        if not ctx.author.voice.channel == ctx.guild.voice_client.channel:
            return await msg.edit(content=f"> このコマンドを使用するには、Botと同じチャンネルに接続する必要があるよ！")

        try:
            await ctx.guild.voice_client.disconnect()

            try:
                del self.bot.queue[ctx.guild.id]
                del self.bot.loop_queue[ctx.guild.id]
            except:
                pass
        except Exception as exc:
            return await msg.edit(content=f"> エラー \n```\n{exc}\n```")
        else:
            await msg.edit(content=f"> 再生を停止し、ボイスチャンネルから退出しました！")

    #play
    @commands.command(name="play", aliases=["p"], description="音楽を再生します。", usage="rsp!play <query>")
    async def play(self, ctx, query:str=None):
        msg = await ctx.send("> 処理中...")

        if not ctx.author.voice:
            return await msg.edit(content=f"> ボイスチャンネルに接続してね！")

        if not ctx.guild.voice_client:
            try:
                vc = await ctx.author.voice.channel.connect()
            except Exception as exc:
                return await msg.edit(content=f"> エラー \n```\n{exc}\n```")
            else:
                await msg.edit(content=f"> {vc.channel.name}に接続したよ！再生処理を行っています...")
        else:
            await msg.edit(content="> 再生処理を行っています...")

        if ctx.guild.voice_client.is_paused():
            ctx.guild.voice_client.resume()
            return await msg.edit(content="> 再生を再開したよ！")

        if not query:
            await msg.edit(content="> 検索ワード/URLを送信してください。")

            try:
                message = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=30.0)
            except asyncio.TimeoutError:
                return await msg.edit(content="> 30秒が経過したため、キャンセルされたよ！")
            else:
                query = message.content

        response = self.youtube.search().list(part="snippet", q=query, type="video").execute()
        id = response["items"][0]["id"]["videoId"]

        if not id:
            return await msg.edit(content="> 動画が見つからなかったよ！")

        try:
            data = await self.get_data(ctx, id, True)
        except Exception as exc:
            return await msg.edit(content=f"> エラー \n```\n{exc}\n```")

        if not data.get("extractor", "").startswith("youtube"):
            return await msg.edit(content="> YouTubeの動画のみ対応しているよ！")

        lists = []

        #from sina ()
        if data.get("_type", None) == "playlist":
            for i in data["entries"]:
                lists.append(self.get_info(ctx, f"https://www.youtube.com/watch?v={i['id']}", True))

                try:
                    ret = [r for r in await asyncio.gather(*lists) if r]
                except Exception as exc:
                    return await msg.edit(content=f"> エラー \n```\n{exc}\n```")

            if self.bot.queue.get(ctx.guild.id, None):
                self.bot.queue[ctx.guild.id] = self.bot.queue[ctx.guild.id] + ret
                return await msg.edit(content=f"> キューに{len(ret)}本の動画を追加しました！")
            else:
                self.bot.queue[ctx.guild.id] = ret
                await msg.edit(content=f"> プレイリストからの{len(ret)}本の動画を再生するよ！")
                self.bot.loop.create_task(self._play(ctx))
        else:
            ret = await self.get_info(ctx, f"https://www.youtube.com/watch?v={data['id']}")

            if self.bot.queue.get(ctx.guild.id, None):
                self.bot.queue[ctx.guild.id] = self.bot.queue[ctx.guild.id] + [ret]
                return await msg.edit(content=f"> キューに{ret['title']}を追加しました！")
            else:
                self.bot.queue[ctx.guild.id] = [ret]
                await msg.edit(content=f"> {ret['title']}を再生するよ！")
                self.bot.loop.create_task(self._play(ctx))

    #skip
    @commands.command(name="skip", description="曲をスキップします。", usage="rsp!skip")
    async def skip(self, ctx):
        msg = await ctx.send("> 処理中...")

        if not ctx.author.voice:
            return await msg.edit(content=f"> ボイスチャンネルに接続してね！")
        if not ctx.guild.voice_client:
            return await msg.edit(content="> このサーバーでは何も再生していないよ！")
        if not ctx.guild.voice_client.channel == ctx.author.voice.channel:
            return await msg.edit(content="> このコマンドを実行するには、Botと同じチャンネルに接続している必要があるよ！")
        if not ctx.guild.voice_client.is_playing():
            return await msg.edit(content=f"> 再生中のみスキップできるよ！")

        loop = self.bot.loop_queue[ctx.guild.id]
        self.bot.loop_queue[ctx.guild.id] = False
        ctx.guild.voice_client.stop()
        self.bot.loop_queue[ctx.guild.id] = loop
        return await msg.edit(content="> 曲をスキップしたよ！")

    #pause
    @commands.command(name="pause", description="曲の再生を一時停止します。", usage="rsp!pause")
    async def pause(self, ctx):
        msg = await ctx.send("> 処理中...")

        if not ctx.author.voice:
            return await msg.edit(content=f"> ボイスチャンネルに接続してね！")
        if not ctx.guild.voice_client:
            return await msg.edit(content="> このサーバーでは何も再生していないよ！")
        if not ctx.guild.voice_client.channel == ctx.author.voice.channel:
            return await msg.edit(content="> このコマンドを実行するには、Botと同じチャンネルに接続している必要があるよ！")
        if not ctx.guild.voice_client.is_playing():
            return await msg.edit(content=f"> 再生中のみ一時停止できるよ！")
        ctx.guild.voice_client.pause()
        return await msg.edit(content="> 曲を一時停止したよ！")

    #volume
    @commands.command(name="volume", aliases=["vol"], description="音量を変更します。", usage="rsp!volume <volume>")
    async def volume(self, ctx, vol: float=None):
        msg = await ctx.send("> 処理中...")

        if not ctx.author.voice:
            return await msg.edit(content=f"> ボイスチャンネルに接続してね！")
        if not ctx.guild.voice_client:
            return await msg.edit(content="> このサーバーでは何も再生していないよ！")
        if not ctx.guild.voice_client.channel == ctx.author.voice.channel:
            return await msg.edit(content="> このコマンドを実行するには、Botと同じチャンネルに接続している必要があるよ！")
        if not ctx.guild.voice_client.is_playing():
            return await msg.edit(content="> 再生中のみ変更できるよ！")
        if not vol:
            return await msg.edit(content="> 音量を指定してね！")

        ctx.guild.voice_client.source.volume = vol/100.0
        return await msg.edit(content=f"> 音量を{vol}にしたよ！！")

    #nowplaying
    @commands.command(name="nowplaying", aliases=["np"], description="現在再生中の音楽を表示します。", usage="rsp!nowplaying")
    async def nowplaying(self, ctx):
        msg = await ctx.send("> 処理中...")

        if not ctx.guild.voice_client:
            return await msg.edit(content="> このサーバーでは何も再生していないよ！")
        if not ctx.guild.voice_client.is_playing():
            return await msg.edit(content="> 現在再生中の曲はないよ！")

        queue = self.bot.queue[ctx.guild.id][0]

        e = discord.Embed(title="🎶Now Playing", color=self.bot.color, timestamp=ctx.message.created_at)
        e.set_thumbnail(url=queue["thumbnail"])
        e.set_footer(text=f"Requested by {self.bot.get_user(queue['request'])}", icon_url=self.bot.get_user(queue["request"]).avatar_url_as(static_format="png"))
        e.add_field(name="再生中の曲", value=f"[{queue['title']}]({queue['webpage_url']})")
        e.add_field(name="アップロードチャンネル", value=f"[{queue['uploader']}]({queue['uploader_url']})")
        return await msg.edit(content=None, embed=e)

    #queue
    @commands.command(name="queue", aliases=["q"], description="キューを表示します。", usage="rsp!queue")
    async def queue(self, ctx):
        msg = await ctx.send("> 処理中...")

        if not ctx.guild.voice_client:
            return await msg.edit(content="> このサーバーでは何も再生していないよ！")

        if self.bot.queue.get(ctx.guild.id, None) == None:
            return await msg.edit(content="> キューに何も追加されてないよ！")

        e = discord.Embed(title="🎶Music Queues", description="", color=self.bot.color, timestamp=ctx.message.created_at)

        for count, i in enumerate(self.bot.queue[ctx.guild.id], 1):
            e.description += f"{count}. [{i['title']}]({i['webpage_url']})\n"

        return await msg.edit(content=None, embed=e)

    #loop
    @commands.command(name="loop", aliases=["repeat"], description="曲のループを切り替えます。", usage="rsp!loop <on/off>")
    async def loop(self, ctx, loop: bool=None):
        msg = await ctx.send("> 処理中...")

        if not loop:
            return await msg.edit(content="> onかoffか指定してね！")
        if not ctx.author.voice:
            return await msg.edit(content=f"> ボイスチャンネルに接続してね！")
        if not ctx.guild.voice_client:
            return await msg.edit(content="> このサーバーでは何も再生していないよ！")
        if not ctx.guild.voice_client.channel == ctx.author.voice.channel:
            return await msg.edit(content="> このコマンドを実行するには、Botと同じチャンネルに接続している必要があるよ！")
        if not ctx.guild.voice_client.is_playing():
            return await msg.edit(content="> 再生中のみ変更できるよ！")

        self.bot.loop_queue[ctx.guild.id] = loop
        return await msg.edit(content=f"> ループを{loop}にしたよ！")

    #_play
    async def _play(self, ctx, vol=0.5):
        if not self.bot.loop_queue.get(ctx.guild.id, None):
            self.bot.loop_queue[ctx.guild.id] = False

        while self.bot.queue[ctx.guild.id]:
            ctx.guild.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.bot.queue[ctx.guild.id][0]["url"], **ffmpeg_options), volume=vol))

            try:
                while ctx.guild.voice_client.is_playing() or ctx.guild.voice_client.is_paused():
                    await asyncio.sleep(1)
                    v = ctx.voice_client.source.volume
            except AttributeError:
                pass

            if self.bot.loop_queue[ctx.guild.id]:
                self.bot.queue[ctx.guild.id].append(self.bot.queue[ctx.guild.id][0])
            self.bot.queue[ctx.guild.id].pop(0)

def setup(bot):
    bot.add_cog(mido_music(bot))

    if not hasattr(bot, "queue"):
        bot.queue = dict()
    if not hasattr(bot, "loop_queue"):
        bot.loop_queue = dict()
