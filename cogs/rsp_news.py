from discord.ext import commands
import discord

import datetime
import aiohttp
import feedparser

def clean_content(text):
    return discord.utils.escape_mentions(discord.utils.escape_markdown(text))

class rsp_news(commands.Cog):
    class NewsData:
        last_update = None
        rss = None
        site = None
        rss_url = None

        def __init__(self, get_time: datetime.datetime, rss: feedparser.util.FeedParserDict, rss_url: str, site: str):
            self.last_update = get_time
            self.rss = rss
            self.site = site
            self.rss_url = rss_url

    def __init__(self, bot):
        self.bot = bot
        if hasattr(bot, "session") and isinstance(bot.session, aiohttp.client.ClientSession):
            self.session = bot.session
        else:
            self.session = aiohttp.ClientSession()

        self.embed_color = 0x36b8fa
        self.rss_page = {"old": "https://www.risupunet.jp/?feed=rss2", "new": "https://www.risupunet.jp/feed/", "beta": "https://www.risupunet.jp/feed/", "rifupu": "https://rifupu.xyz/?feed=rss2"}
        self.site_url = {"old": "https://www.risupunet.jp/", "new": "https://www.risupunet.jp/", "beta": "https://www.risupunet.jp/", "rifupu": "https://rifupu.xyz/"}
        self.icon_url = {"default": "https://www.risupunet.jp/favicon.ico", "rifupu": discord.Embed.Empty}
        self.author_text = {"default": "RisuPu News", "rifupu": "RifuPu"}
        self.caches = []
        self.cache_expires = 60*60
        self.cache_ignores = [415526420115095554]

    #get_data
    async def get_data(self, site):
        async with self.bot.session.get(site, proxy=f"{self.bot.config.PROXY_URL}:{self.bot.config.PROXY_PORT}") as request:
            return await request.text()

    @commands.command(name="risupunews", aliases=["rspnews"], description="RisuPuのお知らせ一覧を表示します。", usage="rsp!risupunews <old/new/beta/rifupu> | rsp!rspnews <old/new/beta/rifupu>")
    async def risupunews(self, ctx, site: str="new"):
        if site in self.rss_page:
            feeds = [c for c in self.caches if c.site == site]
            if feeds:
                if (feeds[0].last_update+datetime.timedelta(seconds=self.cache_expires) < datetime.datetime.utcnow()) or ctx.author.id in self.cache_ignores:
                    async with ctx.channel.typing():
                        ret = await self.get_data(self.rss_page[site])
                        data = self.NewsData(datetime.datetime.utcnow(), feedparser.parse(ret), self.rss_page[site], site)
                    self.caches.remove(feeds[0])
                    self.caches.append(data)
                else:
                    data = feeds[0]
            else:
                async with ctx.channel.typing():
                    ret = await self.get_data(self.rss_page[site])
                    data = self.NewsData(datetime.datetime.utcnow(), feedparser.parse(ret), self.rss_page[site], site)
                self.caches.append(data)

            feed = data.rss

            embed = discord.Embed(description="", color=self.embed_color)

            icon_url = self.icon_url.get(site, self.icon_url["default"])

            if site in self.site_url:
                embed.set_author(name=self.author_text.get(site, self.author_text.get("default")), icon_url=icon_url, url=self.site_url[site])
            else:
                embed.set_author(name=self.author_text.get(site, self.author_text.get("default")), icon_url=icon_url)

            for entry in feed.entries:
                embed.description += f"[`{clean_content(entry.title)}`]({clean_content(entry.link)})\n - {(datetime.datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')+datetime.timedelta(hours=9)).strftime('%Y %m/%d %H:%M')}\n"

            embed.set_footer(text="最終取得時刻")
            embed.timestamp = data.last_update

            try:
                await ctx.reply(embed=embed)
            except AttributeError:
                await ctx.send(content=f"{ctx.author.mention} ->", embed=embed)

        else:
            embed = discord.Embed(title="エラー", description="**指定されたキーが存在しません。**", color=0xFF0000)
            try:
                await ctx.reply(embed=embed)
            except AttributeError:
                await ctx.send(content=f"{ctx.author.mention} ->", embed=embed)

def setup(bot):
    bot.add_cog(rsp_news(bot))

if __name__ == "__main__":
    print("りくりくりーくねっ！")
    print("bot.load_extensionしてね！")
