import discord
from discord.ext import commands

import re
import time
import datetime
import psutil
import platform

import util

class mido_info(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.notify_channels = {464964949823848449: "RisuPu", 670557793010319362: "MCS", 695026857438871592: "VPN", 703556849710006353: "NTP",
                                718592791223074846: "RisuPu-rsvr", 789495012831920128: "MDBS", 718592871749517353: "Other", 698514180214489128: "RisuPu MusicBot"}

    #resolve_url
    def resolve_url(self, url):
        HTTP_URL_REGEX = "https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"
        URL_REGEX = "[\w/:%#\$&\?\(\)~\.=\+\-]+"

        if re.match(HTTP_URL_REGEX, str(url)):
            return str(url)
        elif re.match(URL_REGEX, str(url)):
            return f"http://" + str(url)
        else:
            return False

    #resolve_status
    def resolve_status(self, status):
        if str(status) == "online":
            return "💚オンライン"
        elif str(status) == "dnd":
            return "❤取り込み中"
        elif str(status) == "idle":
            return "🧡退席中"
        elif str(status) == "offline":
            return "🖤オフライン"

    #debug
    @commands.command(name="debug", aliases=["dbg"], description="Botのデバッグ情報を表示します。", usage="rsp!debug | rsp!dbg")
    async def debug(self, ctx):
        e = discord.Embed(title="Debug Information", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        mem = psutil.virtual_memory()
        allmem = str(mem.total/1000000000)[0:3]
        used = str(mem.used/1000000000)[0:3]
        ava = str(mem.available/1000000000)[0:3]
        memparcent = mem.percent
        cpu = psutil.cpu_percent(interval=1)
        core_a = psutil.cpu_count()
        core_b = psutil.cpu_count(logical=False)
        f = 100-memparcent

        dsk = psutil.disk_usage("/")
        d_used = str(dsk.used/100000000)[0:3]
        d_free = str(dsk.free/1000000000)[0:3]

        e.description = None
        e.add_field(name="OS", value=f"{platform.platform(aliased=True)} ({platform.machine()})")
        e.add_field(name="OS Version", value=platform.release())
        e.add_field(name="CPU Information", value=f"Usage: {cpu}% \nCore: {core_a}/{core_b}")
        e.add_field(name="Memory Information", value=f"Total: {allmem}GB \nUsed: {used}GB ({memparcent}%) \nFree: {ava}GB ({f}%)")
        e.add_field(name="Disk Information", value=f"Total: {d_used}GB \nFree: {d_free}GB \nUsage: {dsk.percent}%")
        e.add_field(name="Shard Information", value=f"Total: {self.bot.shard_count}")
        e.add_field(name="Last Started Date", value=self.bot.uptime.strftime('%Y/%m/%d %H:%M:%S'))
        e.add_field(name="Bot Information", value=f"discord.py v{discord.__version__} \nPython v{platform.python_version()}")

        await msg.edit(embed=e)

    #about
    @commands.group(name="about", description="Botについての情報を表示します。", usage="rsp!about [args]", invoke_without_command=True)
    async def about(self, ctx):
        e = discord.Embed(title="Info - about", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        e.description = """
        > 1. このBotについて
         このBotはRisuPu (https://risupunet.jp/) Discordサーバー用に作られた専属Botです。
         Botの導入等はできませんのでご注意ください。

        > 2. RisuPu Discordサーバー
         本サーバー: https://discord.gg/2JkvG2JwuC
         サポートサーバー: https://discord.gg/zaQnvmrp76

        > 3. Botの不具合等について
         ・Midorichan#3451 (ID: 546682137240403984)にDM
         ・サポートサーバーにてチケットを発行
         ・Twitter: https://twitter.com/Midorichaan2525
         ・Mail: midorichan@adm.rspnet.jp

        > 4. その他
         開発者は Midorichan#3451 (ID: 546682137240403984) ですが、所有権はRisuPuにあるものとします。
        """

        await msg.edit(embed=e)

    #about notice
    @about.command(name="notice", description="Botのお知らせを表示します。", usage="rsp!about notice")
    async def notice(self, ctx):
        e = discord.Embed(title="About - notice", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)
        e.description = self.bot.notice or "なし"

        return await msg.edit(embed=e)

    #about support
    @about.command(name="support", description="サポートサーバーのURL等を表示します。", usage="rsp!about support")
    async def support(self, ctx):
        e = discord.Embed(title="About - support", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        e.description = "> RisuPuお問い合わせ・サポート \nDiscordサーバー: https://discord.gg/zaQnvmrp76 \nWeb: https://www.risupunet.jp/contact \nサポート(メール): support@rspeml.jp \nAbuse: abuse@rspeml.jp \n個人情報担当窓口: プライバシーポリシーに明記している担当部署"

        await msg.edit(embed=e)

    #ping
    @commands.command(name="ping", description="Pingを表示します。URLを指定するとそのサイトのステータスコードを取得します。", usage="rsp!ping [url] [noproxy]")
    async def ping(self, ctx, link=None, option:str=None):
        st = time.time()
        e = discord.Embed(title="Ping pong!!", description="Pinging...Please Wait....", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if link == None:
            e.description = "ぽんぐっ！🏓"
            e.add_field(name="Ping", value=str(round(time.time()-st, 3) * 1000)+"ms")
            e.add_field(name="WebSocket", value=f"{round(self.bot.latency * 1000, 2)}ms")
            [e.add_field(name=f"Shard{s}", value=f"{round(self.bot.get_shard(s).latency * 1000, 2)}ms") for s in self.bot.shards]
            return await msg.edit(embed=e)
        else:
            url = self.resolve_url(link)

            if url is False:
                e.description = None
                e.add_field(name="エラー", value="URLが不正です。")
                return await msg.edit(embed=e)

            latency = time.time()

            if option == "noproxy" and ctx.author.id in self.bot.owner_ids:
                async with ctx.bot.session.get(url) as ret:
                    e.description = f"Latency: {round(time.time() - latency, 3) * 1000}ms"
                    e.add_field(name="Result", value=f"ステータスコード: {ret.status}")
                    return await msg.edit(embed=e)
            else:
                async with ctx.bot.session.get(url, proxy=f"{ctx.bot.config.PROXY_URL}:{ctx.bot.config.PROXY_PORT}") as ret:
                    e.description = f"Latency: {round(time.time() - latency, 3) * 1000}ms"
                    e.add_field(name="Result", value=f"ステータスコード: {ret.status}")
                    return await msg.edit(embed=e)

    #on_member_join
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 461153681971216384:
            e = discord.Embed(color=0x36b8fa, timestamp=datetime.datetime.now())
            e.set_author(name=f"{member} さんが参加しました！！", icon_url=member.avatar_url_as(static_format="png"))
            e.add_field(name="ID", value=str(member.id))
            e.add_field(name="Botか", value="はい" if member.bot else "いいえ")
            e.add_field(name="ステータス", value=self.resolve_status(member.status))
            e.add_field(name="アカウント作成日", value=str(member.created_at.strftime('%Y/%m/%d %H:%M:%S')))

            dm = discord.Embed(title=f"{member.guild} へようこそ！", description="", color=0x36b8fa, timestamp=member.joined_at)
            dm.description = f"""
            {member.guild}公式Discordサーバーへご参加いただき、まことにありがとうございます。
            当サーバーではBotを介した認証を行わないとチャットに参加できない仕組みとなっております。

            まず初めにこの以下当組織グループ会員規約・コミュニティサーバ利用規約をお読みください。
            > **https://www.risupunet.jp/agreement/dcd-srvtos/**
            上記規約に同意いただける場合は、認証についての条約に記載されている方法で認証して下さい。
            ※認証は <#621387537608605716> で行ってください。

            > **------------------------------------------------------------------------------------------**
            rspnet.jpグループ
            RisuPu by RSPnet.jp

            ホームページ　　**https://suoc.me/rspnet**
　　　　　　　　            **https://www.risupunet.jp/**

            お問い合わせ　　サポートデスク等
　　　　　　　　            **https://www.risupunet.jp/contact/**

　　　　　　　　            サポートサーバー
　　　　　　　　            **https://discord.gg/phvBHXh5DT**
            > **------------------------------------------------------------------------------------------**
            """

            try:
                await member.send(embed=dm)
                await member.guild.get_channel(621387537608605716).send(embed=dm)
            except:
                await member.guild.get_channel(621387537608605716).send(embed=dm)

            await member.guild.get_channel(685034563747184650).send(content="> メンバーの情報", embed=e)
            await member.guild.get_channel(461153681971216388).send(content="> メンバーの情報", embed=e)

    #on_member_left
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id == 461153681971216384:
            e = discord.Embed(color=0x36b8fa, timestamp=datetime.datetime.now())
            e.set_author(name=f"{member} さんが退出しました...", icon_url=member.avatar_url_as(static_format="png"))
            e.add_field(name="ID", value=str(member.id))
            e.add_field(name="Botか", value="はい" if member.bot else "いいえ")
            e.add_field(name="ステータス", value=self.resolve_status(member.status))
            e.add_field(name="サーバー参加日", value=str(member.joined_at.strftime('%Y/%m/%d %H:%M:%S')))
            e.add_field(name="アカウント作成日", value=str(member.created_at.strftime('%Y/%m/%d %H:%M:%S')))

            await member.guild.get_channel(685034563747184650).send(embed=e)
            await member.guild.get_channel(461153681971216388).send(embed=e)

    #on_message
    @commands.Cog.listener()
    async def on_message(self, msg):
        if isinstance(msg.channel, discord.DMChannel):
            return

        if msg.guild.id == 461153681971216384 and msg.channel.id in self.notify_channels:
            e = discord.Embed(title=f"📢 {self.notify_channels[msg.channel.id]} Notification", description=f"{msg.channel.mention}で新しいお知らせがあります！！ \n[ここをクリック]({msg.jump_url})", color=0x36b8fa, timestamp=msg.created_at)
            await msg.guild.get_channel(685034563747184650).send(embed=e)

    #userinfo
    @commands.command(name="userinfo", aliases=["ui", "user"], description="ユーザーの情報を表示します。", usage="rsp!userinfo [user/member]")
    async def userinfo(self, ctx, user:util.FetchUserConverter=None):
        e = discord.Embed(title="User Information", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if not user:
            user = ctx.author

        e.set_thumbnail(url=user.avatar_url_as(static_format="png"))
        e.description = None
        e.add_field(name="ユーザー名", value=f"{user} \n({user.id})")

        if ctx.guild and isinstance(user, discord.Member):
            e.add_field(name="ニックネーム", value=user.display_name)

        e.add_field(name="Botか", value="はい" if user.bot else "いいえ")

        if isinstance(user, discord.Member):
            e.add_field(name="Nitroブースター", value=f"{user.premium_since.strftime('%Y/%m/%d %H:%M:%S')}から" if user.premium_since is not None else "なし")

        e.add_field(name="アカウント作成日時", value=user.created_at.strftime('%Y/%m/%d %H:%M:%S'))

        if isinstance(user, discord.Member):
            e.add_field(name="サーバー参加日時", value=user.joined_at.strftime('%Y/%m/%d %H:%M:%S'))
            e.add_field(name="ステータス", value=self.resolve_status(user.status))
            if not user.activity:
                try:
                    if user.activity.type == discord.ActivityType.custom:
                        e.add_field(name="カスタムステータス", value=user.activity)
                    else:
                        e.add_field(name="カスタムステータス", value=f"{user.activity.name}")
                except:
                    e.add_field(name="カスタムステータス", value=user.activity)

            roles = ", ".join(c.mention for c in list(reversed(user.roles)))
            if len(user.roles) <= 1000:
                e.add_field(name="役職", value=roles, inline=False)
            else:
                e.add_field(name="役職", value="多すぎて表示できないよ！", inline=False)
            e.add_field(name=f"権限 ({user.guild_permissions.value})", value=", ".join("`{}`".format(self.bot.json_config["roles"].get(c, str(c))) for c,b in dict(user.guild_permissions).items() if b is True), inline=False)

        await msg.edit(embed=e)

def setup(bot):
    bot.add_cog(mido_info(bot))
