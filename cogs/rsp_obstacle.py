import discord
from discord.ext import commands, tasks

import datetime
import aiohttp

import paginator as p

class rsp_obstacle(commands.Cog):

    class ObstacleData:

        def __init__(self, time:datetime.datetime, data:dict):
            self.last_update = time
            self.data = data

    def __init__(self, bot):
        self.bot = bot

        if hasattr(bot, "session") and isinstance(bot.session, aiohttp.client.ClientSession):
            self.session = bot.session
        else:
            self.session = aiohttp.ClientSession()

        self.caches = bot.caches
        self.cache_expires = 60*60

        self.create_cache.start()

    #create_cache
    @tasks.loop(hours=1)
    async def create_cache(self):
        try:
            await self.update_cache()
            print("[System] RisuPu Obstacle Cache created")
        except Exception as exc:
            print(f"[Error] {exc}")

    #update_cache
    async def update_cache(self):
        if self.caches == []:
            async with self.session.get("https://api2.maikuradentetu.jp/rsp_obstacle.json") as ret:
                try:
                    data = await ret.json()
                except:
                    return None

                for d in data["Obstacles"]:
                    self.caches.append(self.ObstacleData(datetime.datetime.utcnow(), d))
        elif (self.caches[0].last_update + datetime.timedelta(seconds=self.cache_expires) < datetime.datetime.utcnow()):
            self.caches = []

            async with self.session.get("https://api2.maikuradentetu.jp/rsp_obstacle.json") as ret:
                try:
                    data = await ret.json()
                except:
                    return None

                for d in data["Obstacles"]:
                    self.caches.append(self.ObstacleData(datetime.datetime.utcnow(), d))
        return True

    #obstacle
    @commands.command(name="obstacle", aliases=["ob"], description="RisuPuの障害情報を表示します。\n(API提供: mRiku#2987)", usage="rsp!obstacle | rsp!ob")
    async def obstacle(self, ctx):
        ret = await self.update_cache()

        if ret is None:
            return await ctx.send("> データを取得できませんでした")

        embeds = []

        for i in self.caches:
            e = discord.Embed(title="RisuPu Obstacles", description="", color=0x36b8fa, timestamp=ctx.message.created_at)

            data = i.data

            e.description = f"{data['Title']}"
            e.add_field(name="ステータス", value=data["Status"])
            e.add_field(name="発生日時", value=f"{data['OccurrenceTime']}", inline=False)
            e.add_field(name="復旧日時", value=f"{data['RecoveryTime']}", inline=False)
            e.add_field(name="対象", value=f"{data['Target']}", inline=False)
            e.add_field(name="原因", value=f"{data['Cause']}")
            e.add_field(name="事象", value=f"{data['Case']}")
            e.add_field(name="対応", value=f"{data['Corresponding']}", inline=False)
            e.add_field(name="詳細", value=data["Link"], inline=False)

            embeds.append(e)

        page = p.EmbedPaginator(ctx, entries=embeds, timeout=30.0)

        await page.paginate()

def setup(bot):
    if not hasattr(bot, "caches"):
        bot.caches = []

    bot.add_cog(rsp_obstacle(bot))
