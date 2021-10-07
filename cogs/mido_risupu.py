import discord
from discord.ext import commands

import asyncio
import traceback

import util

class mido_risupu(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.main_server_console = bot.get_channel(706054362186645554)
        self.life_server_console = bot.get_channel(706054643347882056)
        self.main_bot = bot.get_guild(703920815652995072).get_member(561327285718745109)
        self.life_bot = bot.get_guild(703920815652995072).get_member(596070378892296195)

        self.o = self.bot.get_emoji(734033926892290130)
        self.x = self.bot.get_emoji(734033946639204362)

    #async send
    async def globalsend(self, msg, webhook):
        try:
            hook = discord.Webhook.from_url(webhook, adapter=discord.AsyncWebhookAdapter(self.bot.session))
        except discord.InvalidArgument as exc:
            raise exc
        else:
            attachments = []
            embeds = []

            try:
                if msg.attachments:
                    attachments = [await attachment.to_file() for attachment in msg.attachments]
                if msg.embeds:
                    embeds = msg.embeds

                await hook.send(msg.clean_content, username=str(msg.author), avatar_url=msg.author.avatar_url_as(static_format="png"), files=attachments, embeds=embeds)
            except Exception as exc:
                raise exc

    #sync risupu chat
    @commands.Cog.listener()
    async def on_message(self, msg):
        if isinstance(msg.channel, discord.DMChannel):
            return
        if msg.webhook_id:
            return
        if msg.is_system():
            return

        log = self.bot.get_channel(self.bot.config.LOG_CHANNEL)

        if msg.channel.id == 724236446763843654:
            webhook = self.bot.config.WEBHOOK_URL_SUPPORT
        elif msg.channel.id == 705715113893560331:
            webhook = self.bot.config.WEBHOOK_URL_ADMIN
        else:
            return

        try:
            return await asyncio.gather(asyncio.ensure_future(self.globalsend(msg, webhook)))
        except Exception as exc:
            e = discord.Embed(title="GlobalChat Exception", description=f"```py\n{exc}\n```", color=self.bot.color, timestamp=msg.created_at)
            return await log.send(embed=e)

    #confirm
    async def confirm(self, ctx, msg):
        await msg.add_reaction("❌")
        await msg.add_reaction("✅")

        try:
            r, u = await self.bot.wait_for("reaction_add", check=lambda r,u: r.message.id == msg.id and u.id == ctx.author.id and r.emoji in ["❌", "✅"], timeout=30.0)
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            return False
        else:
            if r.emoji == "❌":
                await msg.clear_reactions()
                return True
            elif r.emoji == "✅":
                await msg.clear_reactions()
                return True

    #risupuword
    @commands.group(name="risupuword", aliases=["risupuwords", "rw"], description="RisuPu用語を追加/削除/修正します。", invoke_without_command=True, usage="rsp!risupuword <args>")
    async def risupuword(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            return await ctx.send("> DMでは使えません。")

        pass

    #risupuword add
    @risupuword.command(name="add", description="RisuPu用語を追加します。", usage="rsp!risupuword add <text>")
    async def add(self, ctx, *, word: str=None):
        m = await ctx.send("> 処理中...")

        if not word:
            return await m.edit(content="> 追加する内容を指定してください。")

        d = await self.bot.db(db="risupu_bot").fetchall("SELECT * FROM risupuwords")
        texts = [r["word"] for r in d]

        if word in texts:
            return await m.edit(content="> すでに追加されています。")

        await m.edit(content="> 追加しますか？")
        r = await self.confirm(ctx, m)

        if r is False:
            return await m.edit(content="> キャンセルしました。")

        try:
            await self.bot.db(db="risupu_bot").execute("INSERT INTO risupuwords VALUES(%s, %s, %s)", (len(d) + 1, word, ctx.author.id))
        except Exception as exc:
            return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
        else:
            return await m.edit(content="> 追加しました！")

    """#risupuword del
    @risupuword.command(name="del", description="RisuPu用語を削除します。", usage="rsp!risupuword del <id>")
    async def rm(self, ctx, id: int=None):
        m = await ctx.send("> 処理中...")

        if not id:
            return await m.edit(content="> 削除する用語のIDを指定してください。")

        d = await self.bot.db(db="risupu_bot").fetchall("SELECT * FROM risupuwords WHERE id=%s", (id, ))

        if not d:
            return await m.edit(content="> そのIDの用語は追加されていません。")

        await m.edit(content="> 削除しますか？")
        r = await self.confirm(ctx, m)

        if not r == True:
            return await msg.edit("> キャンセルしました。")

        try:
            await self.bot.db(db="risupu_bot").execute("DELETE FROM risupuwords WHERE id=%s", (id, ))
        except Exception as exc:
            return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
        else:
            return await m.edit(content="> 削除しました！")"""

    #risupuword info
    @risupuword.command(name="info", description="RisuPu用語の情報を表示します。", usage="rsp!risupuword info <id>")
    async def info(self, ctx, id: int=None):
        e = discord.Embed(title="RisuPuWord - info", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if not id:
            e.description = None
            e.add_field(name="エラー", value="用語のIDを指定してください。")
            return await msg.edit(embed=e)

        db = await self.bot.db(db="risupu_bot").fetchone("SELECT * FROM risupuwords WHERE id=%s", (id, ))

        if not db:
            e.description = None
            e.add_field(name="エラー", value="そのIDの用語は存在しません。")
            return await msg.edit(embed=e)

        e.description = None
        e.add_field(name="ID", value=db["id"])
        e.add_field(name="作成者", value=f"{self.bot.get_user(db['author_id'])} \nID: {db['id']}")
        e.add_field(name="内容", value=db["word"])
        return await msg.edit(embed=e)

    #risupuword list
    @risupuword.command(name="list", description="RisuPu用語の情報を表示します。", usage="rsp!risupuword list")
    async def list_(self, ctx):
        e = discord.Embed(title="RisuPuWord - list", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        data = await self.bot.db(db="risupu_bot").fetchall("SELECT * FROM risupuwords")

        for db in data:
            e.add_field(name=f"ID {db['id']}", value=db["word"])

        e.description = None
        return await msg.edit(embed=e)

    #risupuword fix
    @risupuword.command(name="fix", description="RisuPu用語を修正します。", usage="rsp!risupuword fix <id> <text>")
    async def fix(self, ctx, id: int=None, *, text: str=None):
        m = await ctx.send("> 処理中...")

        if not id:
            return await m.edit(content="> 修正する用語のIDを指定してください。")

        if not text:
            return await m.edit(content="> 修正する用語を入力してください。")

        db = await self.bot.db(db="risupu_bot").fetchall("SELECT * FROM risupuwords WHERE id=%s", (id, ))

        if not db:
            return await m.edit(content="> そのIDの用語は追加されていません。")

        await m.edit(content="> 修正しますか？")
        r = await self.confirm(ctx, m)

        if r is False:
            return await m.edit("> キャンセルしました。")

        try:
            await self.bot.db(db="risupu_bot").execute("UPDATE risupuwords SET word=%s WHERE id=%s", (text, id))
        except Exception as exc:
            return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
        else:
            return await m.edit(content="> 修正しました！")

    #risupuword help
    @risupuword.command(name="help", description="ヘルプを表示します。", usage="rsp!risupuword help")
    async def help(self, ctx):
        e = discord.Embed(title="risupuword - help", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        for c in self.bot.get_command("risupuword").commands:
            e.add_field(name=c.name, value=c.description)

        e.description = None
        await msg.edit(embed=e)

    #togglepin
    @commands.command(name="togglepin", description="メッセージをピン止め/解除します。", usage="rsp!togglepin <message>", brief="メッセージの管理権限所持者のみ")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def togglepin(self, ctx, m:commands.MessageConverter=None):
        if not m:
            if ctx.message.reference:
                if isinstance(ctx.message.reference.resolved, discord.Message):
                    m = ctx.message.reference.resolved
                else:
                    return await ctx.send("> 削除されたメッセージは指定できません。")
            else:
                return await ctx.send("> メッセージを指定してください。")

        if m.pinned:
            try:
                await m.unpin()
            except Exception as exc:
                return await ctx.send(f"> エラーが発生しました。\n```py\n{exc}\n```")
            else:
                return await ctx.send(ctx.bot.get_emoji(734033926892290130))
        else:
            try:
                await m.pin()
            except Exception as exc:
                return await ctx.send(f"> エラーが発生しました。\n```py\n{exc}\n```")
            else:
                return await ctx.send(ctx.bot.get_emoji(734033926892290130))

    #console
    @commands.command(name="console", description="MCSのコンソールからコマンドを実行します。", usage="rsp!console <main/life> <command>", brief="MCS担当課のみ")
    @commands.check(util.is_mcs)
    async def console(self, ctx, server=None, *, command=None):
        e = discord.Embed(title="MCS - console", description="コマンド実行中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if server is None:
            e.description = None
            e.add_field(name="エラー", value="main / life からサーバーを選択してください。")
            return await msg.edit(embed=e)

        if command is None:
            e.description = None
            e.add_field(name="エラー", value="実行するコマンドを入力してください。")
            return await msg.edit(embed=e)

        if str(server) == "main":
            ch = self.main_server_console
            b = self.main_bot
        elif str(server) == "life":
            ch = self.life_server_console
            b = self.main_bot
        else:
            e.description = None
            e.add_field(name="エラー", value="main / life からサーバーを選択してください。")
            return await msg.edit(embed=e)

        try:
            await ch.send(command)
            ret = await self.bot.wait_for("message", check=lambda m: m.channel.id == ch.id and m.author.id == b.id, timeout=30.0)
        except asyncio.TimeoutError:
            e.description = f"```\n***タイムアウトしました。***\n```"
            return await msg.edit(embed=e)
        except Exception as er:
            e.description = None
            e.add_field(name="エラー", value=f"```py\n{er}\n```")
            return await msg.edit(embed=e)
        else:
            e.description = f"```\n{ret.content}\n```"
            return await msg.edit(embed=e)

    #sql
    @commands.command(name="sql", description="指定データベースからSQLコマンドを実行します。", usage="rsp!sql <db> <sql>", brief="インフラ担当課のみ")
    @commands.check(util.is_infra)
    async def sql(self, ctx, db:str, *, code=None):
        if not code:
            return await ctx.reply("> SQL文を入力してね！")

        try:
            ret = await self.bot.db(db=db).fetchall(code)
        except Exception as exc:
            await ctx.message.add_reaction("❌")
            return await ctx.author.send(f"```py\n{exc}\n```")
        else:
            await ctx.message.add_reaction("✅")

            if ret:
                try:
                    await ctx.send(f"```\n{ret}\n```")
                except discord.HTTPException:
                    await ctx.send("> 出力が長すぎます。")
            else:
                await ctx.send(f"```\nnone\n```")

    #roles
    @commands.command(name="roles", description="指定ユーザーからロールを剥奪・付与します。", usage="rsp!roles <add/remove> <member> <roles>", brief="運営審査担当課のみ")
    @commands.check(util.is_risupu_manager)
    @commands.bot_has_permissions(manage_roles=True)
    async def roles(self, ctx, mode:str=None, member:commands.MemberConverter=None, roles:commands.Greedy[discord.Role]=None):
        e = discord.Embed(title="Manage - roles", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if mode is None or not str(mode) in ["add", "remove"]:
            e.description = None
            e.add_field(name="エラー", value="addかremoveを指定してね！")
            return await msg.edit(embed=e)

        if member is None:
            e.description = None
            e.add_field(name="エラー", value="メンバーを入力してね！")
            return await msg.edit(embed=e)

        if roles is None:
            e.description = None
            e.add_field(name="エラー", value="ロールを入力してね！")
            return await msg.edit(embed=e)

        if str(mode) == "add":
            task = []

            count = [len(roles), 0]

            for role in roles:
                task.append(member.add_roles(role))

            try:
                await asyncio.gather(*task)
            except:
                count[1] += 1

            e.description = None
            e.add_field(name="成功", value=f"{member}に{count[0]}のロールを付与したよ！\n成功: {count[0] - count[1]}, 失敗: {count[1]}")
            return await msg.edit(embed=e)
        elif str(mode) == "remove":
            task = []

            count = [len(roles), 0]

            for role in roles:
                task.append(member.remove_roles(role))

            try:
                await asyncio.gather(*task)
            except:
                count[1] += 1

            e.description = None
            e.add_field(name="成功", value=f"{member}から{count[0]}のロールを剥奪したよ！\n成功: {count[0] - count[1]}, 失敗: {count[1]}")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="addかremoveを指定してね！")
            return await msg.edit(embed=e)

def setup(bot):
    bot.add_cog(mido_risupu(bot))
