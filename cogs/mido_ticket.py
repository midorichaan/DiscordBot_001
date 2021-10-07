import discord
from discord.ext import commands

import asyncio
import os
import json
import datetime

from database import Database
import util

class ticket_log():

    def __init__(self, msg):
        self.author_id = msg.author.id
        self.message_id = msg.id
        self.channel_id = msg.channel.id
        self.message_content = msg.content
        self.created_at = msg.created_at
        self.embeds = [e.to_dict() for e in msg.embeds if msg.embeds]
        self.attachments = [a.proxy_url for a in msg.attachments if msg.attachments]

class mido_ticket(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database(db="risupu_bot")

        if hasattr(bot, "ticket_log") and isinstance(bot.ticket_log, dict):
            self.ticket_log = bot.ticket_log
        else:
            bot.ticket_log = dict()
            self.ticket_log = bot.ticket_log

        asyncio.gather(self.db.execute("CREATE TABLE IF NOT EXISTS ticket_config(guild BIGINT PRIMARY KEY NOT NULL, category BIGINT, mention INTEGER, role BIGINT, deleteafter INTEGER, moveclosed INTEGER, movecat BIGINT, log BIGINT)"),
                       self.db.execute("CREATE TABLE IF NOT EXISTS tickets(id BIGINT PRIMARY KEY NOT NULL, panel BIGINT, author BIGINT, category BIGINT, status INTEGER)"),
                       self.db.execute("CREATE TABLE IF NOT EXISTS ticket_panel(id BIGINT PRIMARY KEY NOT NULL, channel BIGINT, guild BIGINT)"),
                       self.db.execute("CREATE TABLE IF NOT EXISTS ticket_log(id BIGINT PRIMARY KEY NOT NULL, channel BIGINT, author BIGINT, content TEXT)"))

    #create_ticket
    async def create_ticket(self, guild, member, reason, *, config=None):
        if config is None:
            config = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (guild.id,))

        chs = [c for c in guild.channels if str(member.id) in str(c.name)]

        ch = await guild.get_channel(config["category"]).create_text_channel(name=f"ticket-{member.id}-{len(chs)+1}")

        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = True
        overwrite.read_messages = True
        overwrite.add_reactions = True
        overwrite.embed_links = True
        overwrite.read_message_history = True
        overwrite.external_emojis = True
        overwrite.attach_files = True

        await ch.set_permissions(member, overwrite=overwrite)
        panel = await self.create_panel(guild, member, ch, db=config, reason=reason)
        await ch.send(f"> お問い合わせ内容を送信してください。")

        return ch, panel

    #create panel
    async def create_panel(self, guild, author, channel, *, db=None, reason=None):
        if db is None:
            db = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (guild.id,))

        e = discord.Embed(title=f"Support Ticket - {author}", color=0x36b8fa)
        time = await self.check_time(guild.id)

        if not reason:
            e.add_field(name="チケット作成理由 / Reason", value=f"```\nunknown\n```", inline=False)
            e.add_field(name="ステータス / Ticket Status", value="```\nwait for reason\n```", inline=False)
        else:
            e.add_field(name="チケット作成理由 / Reason", value=f"```\n{reason}\n```", inline=False)
            e.add_field(name="ステータス / Ticket Status", value="```\nOpen\n```", inline=False)

        if time:
            e.set_footer(text="お問い合わせ対応時間外のため、緊急時のみ運営チームにメンションしてください。", icon_url=guild.icon_url_as(static_format="png"))

        if db and db["mention"] == 1 and not time:
            msg = await channel.send(content=f"{guild.get_role(db['role']).mention} {author.mention} →", embed=e)
        else:
            msg = await channel.send(content=f"{author.mention} →", embed=e)

        await msg.pin()
        if not reason:
            await self.db.execute(f"INSERT INTO tickets VALUES(%s, %s, %s, %s, %s)", (channel.id, msg.id, author.id, channel.category.id, 2))
        else:
            await self.db.execute(f"INSERT INTO tickets VALUES(%s, %s, %s, %s, %s)", (channel.id, msg.id, author.id, channel.category.id, 1))
        await msg.add_reaction("🔐")

        return msg

    #log_ticket
    async def log_ticket(self, msg):
        if not os.path.exists(f"./logs/ticket-{msg.channel.id}.json"):
            with open(f"./logs/ticket-{msg.channel.id}.json", "x", encoding="utf-8") as f:
                json.dump({}, f)

        with open(f"./logs/ticket-{msg.channel.id}.json", "r", encoding="utf-8") as f:
            file = json.load(f)

        if msg.content:
            await self.db.execute(f"INSERT INTO ticket_log VALUES(%s, %s, %s, %s)", (int(msg.id), int(msg.channel.id), int(msg.author.id), str(msg.content)))
        else:
            await self.db.execute(f"INSERT INTO ticket_log VALUES(%s, %s, %s, %s)", (int(msg.id), int(msg.channel.id), int(msg.author.id), None))

        self.ticket_log[msg.id] = ticket_log(msg)

        file[msg.id] = {
            "message_id":msg.id,
            "channel_id":msg.channel.id,
            "author_id":msg.author.id,
            "embeds":[e.to_dict() for e in msg.embeds if msg.embeds],
            "attachments":[a.proxy_url for a in msg.attachments if msg.attachments],
            "content":msg.content,
            "created_at":str(msg.created_at)
        }

        with open(f"./logs/ticket-{msg.channel.id}.json", "w", encoding="utf-8") as f:
            json.dump(file, f, indent=4)

    #time_check
    async def check_time(self, guild_id: int):
        db = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (guild_id,))
        if not db:
            return False

        date = datetime.datetime.now().strftime("%H")

        if db["time_start"] <= db["time_end"]:
            if db["time_start"] <= int(date) and int(date) <= db["time_end"]:
                return True
        else:
            if db["time_start"] <= int(date) and int(date) >= db["time_end"]:
                return True

        return False

    #on_msg log
    @commands.Cog.listener()
    async def on_message(self, msg):
        if isinstance(msg.channel, discord.DMChannel):
            return

        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (msg.channel.id,))

        if not db:
            return

        if db["status"] == 1:
            try:
                await self.log_ticket(msg)
            except Exception as exc:
                await self.bot.get_user(546682137240403984).send(f"> Ticket Log Exc \n```py\n{exc}\n```")

        if db["status"] == 2:
            if not msg.author.id == db["author"]:
                return

            panel = await msg.channel.fetch_message(db["panel"])
            embed = panel.embeds[0]
            embed.set_field_at(0, name="チケット作成理由 / Reason", value=f"```\n{msg.content}\n```", inline=False)
            embed.set_field_at(1, name="ステータス / Ticket Status", value="```\nOpen\n```", inline=False)
            await panel.edit(embed=embed)
            await self.db.execute("UPDATE tickets SET status=1 WHERE id=%s", (msg.channel.id,))

    #detect reaction
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        db = await self.db.fetchone("SELECT * FROM tickets WHERE panel=%s", (payload.message_id,))
        panel = await self.db.fetchone("SELECT * FROM ticket_panel WHERE id=%s", (payload.message_id,))
        config = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (payload.guild_id,))

        if db and str(payload.event_type) == "REACTION_ADD" and payload.user_id != self.bot.user.id and str(payload.emoji) == "🔐":
            try:
                msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                await msg.remove_reaction("🔐", payload.member)
            except:
                pass

            if db["status"] == 0:
                return

            if not (db["author"] == payload.member.id or payload.member.id in [m.id for m in self.bot.get_guild(payload.guild_id).get_role(config["role"]).members]):
                return

            ch = self.bot.get_channel(payload.channel_id)

            check = await ch.send("> Closeしますか？ (open/close)")

            wait = await self.bot.wait_for("message", check=lambda m: m.author.id == payload.user_id and m.channel.id == payload.channel_id)

            if str(wait.content) != "close":
                await check.edit(content=f"> キャンセルしました！")
                return
            else:
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = False
                overwrite.add_reactions = False
                overwrite.external_emojis = False

                await self.db.execute("UPDATE tickets SET status=%s WHERE panel=%s", (0, payload.message_id))
                await ch.edit(name=ch.name.replace("ticket", "close"))
                await ch.set_permissions(self.bot.get_guild(payload.guild_id).get_member(db["author"]), overwrite=overwrite)
                await ch.send("> サポートチケットをcloseしました！")
                await ch.send(content="> Support Ticket Logs (json)", file=discord.File(f"./logs/ticket-{ch.id}.json"))

                if config["log"]:
                    embed = discord.Embed(title=f"Ticket Logs {self.bot.get_user(db['author'])} ({db['author']})", color=0x36b8fa)

                    await self.bot.get_channel(config["log"]).send(embed=embed, file=discord.File(f"./logs/ticket-{ch.id}.json"))

                if config["deleteafter"] == 1:
                    await asyncio.sleep(10)
                    await ch.delete()

                if config["moveclosed"] == 1:
                    await ch.edit(category=self.bot.get_channel(int(config["movecat"])))

        if panel and str(payload.event_type) == "REACTION_ADD" and payload.user_id != self.bot.user.id and payload.message_id == panel["id"] and str(payload.emoji) == "📩":
            msg = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            await msg.remove_reaction("📩", payload.member)
            await self.create_ticket(self.bot.get_guild(payload.guild_id), payload.member, None)

    #ticket
    @commands.group(invoke_without_command=True, name="ticket", description="チケット関連のコマンドです。", usage="rsp!ticket <arg1> [arg2]")
    async def ticket(self, ctx):
        pass

    #ticket help
    @ticket.command(name="help", description="チケットのヘルプを表示します。", usage="rsp!ticket help [command]")
    async def help(self, ctx, command=None):
        e = discord.Embed(title="Support - ticket", color=0x36b8fa, timestamp=ctx.message.created_at)

        if command and (c := self.bot.get_command("ticket").get_command(command)):
            e.title = f"Support - {c.name}"
            e.add_field(name="説明", value=c.description)
            e.add_field(name="使用法", value=c.usage)

            if c.brief:
                e.add_field(name="権限", value=c.brief)

            e.add_field(name="エイリアス", value=", ".join([f"`{row}`" for row in c.aliases]))
            return await ctx.reply(embed=e)
        else:
            for i in self.bot.get_command("ticket").commands:
                e.add_field(name=i.name, value=i.description)

            return await ctx.reply(embed=e)

    #ticket adduser
    @ticket.command(name="adduser", description="チケットにユーザーを追加します。", usage="rsp!ticket adduser <member> [channel]", brief="サポート係以上")
    @commands.check(util.is_support)
    async def adduser(self, ctx, member:commands.MemberConverter=None, channel:commands.TextChannelConverter=None):
        e = discord.Embed(title="Ticket - adduser", description="処理中....", color=0x36b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if member is None:
            e.description = None
            e.add_field(name="エラー", value="メンバーを指定してね！")
            return await msg.edit(embed=e)

        if channel is None:
            ch = ctx.channel
        else:
            ch = channel

        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (ch.id,))

        if db:
            overwrite = discord.PermissionOverwrite()
            overwrite.send_messages = True
            overwrite.read_messages = True
            overwrite.add_reactions = True
            overwrite.embed_links = True
            overwrite.read_message_history = True
            overwrite.external_emojis = True
            overwrite.attach_files = True

            await ch.set_permissions(member, overwrite=overwrite)

            e.description = None
            e.add_field(name="成功", value=f"{member} ({member.id}) さんを{ch}に追加したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="そのチャンネルはチケットチャンネルじゃないよ！")
            return await msg.edit(embed=e)

    #ticket removeuser
    @ticket.command(name="removeuser", aliases=["deluser"], description="チケットからユーザーを削除します。", usage="rsp!ticket removeuser <member> [channel] | rsp!ticket deluser <member> [channel]", brief="サポート係以上")
    @commands.check(util.is_support)
    async def removeuser(self, ctx, member:commands.MemberConverter=None, channel:commands.TextChannelConverter=None):
        e = discord.Embed(title="Ticket - removeuser", description="処理中....", color=0x36b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if member is None:
            e.description = None
            e.add_field(name="エラー", value="メンバーを指定してね！")
            return await msg.edit(embed=e)

        if channel is None:
            ch = ctx.channel
        else:
            ch = channel

        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (ch.id,))

        if db:
            await ch.set_permissions(member, overwrite=None)

            e.description = None
            e.add_field(name="成功", value=f"{member} ({member.id}) さんを{ch}から削除したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="そのチャンネルはチケットチャンネルじゃないよ！")
            return await msg.edit(embed=e)

    #ticket deletepanel
    @ticket.command(name="deletepanel", aliases=["delpanel"], description="チケットパネルを削除します。", usage="rsp!ticket deletepanel <panel_id> | rsp!ticket delpanel <panel_id>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def deletepanel(self, ctx, panel_id:int=None):
        e = discord.Embed(title="Ticket - deletepanel", description="処理中...", color=0x36b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if panel_id is None:
            e.description = None
            e.add_field(name="エラー", value="パネルIDを入力してね！")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_panel WHERE id=%s", (panel_id,))

        if check:
            ch = self.bot.get_channel(check["channel"])
            panel = await ch.fetch_message(panel_id)

            await self.db.execute("DELETE FROM ticket_panel WHERE id=%s", (panel_id,))
            await panel.delete()

            e.description = None
            e.add_field(name="成功", value="パネルを削除しました！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value=f"そのIDのパネルは存在しません。")
            return await msg.edit(embed=e)

    #ticket panel
    @ticket.command(name="panel", aliases=["addpanel"], description="チケットパネルを作成します。", usage="rsp!ticket panel [channel] | rsp!ticket addpanel [channel]", brief="サポート係以上")
    @commands.check(util.is_support)
    async def panel(self, ctx, channel:commands.TextChannelConverter=None):
        e = discord.Embed(title="Ticket - panel", description="処理中...", color=0x36b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if channel is None:
            channel = ctx.channel
        else:
            channel = channel

        db = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))
        if not db:
            e.description = None
            e.add_field(name="エラー", value="Configがないのでパネルを作成できません。")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_panel WHERE channel=%s", (channel.id,))

        if check:
            e.description = None
            e.add_field(name="エラー", value="すでにパネルが存在するよ！")
            return await msg.edit(embed=e)
        else:
            panel = discord.Embed(title="Support Ticket Panel", description="📩 をクリックすることでサポートチケットを発行します。", color=0x36b8fa)
            m = await channel.send(embed=panel)
            await m.add_reaction("📩")

            await self.db.execute(f"INSERT INTO ticket_panel VALUES({m.id}, {channel.id}, {ctx.guild.id})")

            e.description = None
            e.add_field(name="成功", value=f"{channel} ({channel.id})にサポートパネルを作成しました！")
            return await msg.edit(embed=e)

    #ticket config
    @ticket.group(name="config", description="チケットの設定を変更します。", usage="rsp!ticket config <arg1> [arg2]", brief="サポート係以上", invoke_without_command=False)
    @commands.check(util.is_support)
    async def config(self, ctx):
        pass

    #ticket config help
    @commands.check(util.is_support)
    @config.command(name="help", description="チケットの設定のヘルプを表示します。",usage="rsp!ticket config help [command]", brief="サポート係以上")
    async def ticket_help(self, ctx, command=None):
        e = discord.Embed(title="Support - ticket", color=0x36b8fa, timestamp=ctx.message.created_at)

        if command and (c := self.bot.get_command("ticket").get_command("config").get_command(command)):
            e.title = f"Support - {c.name}"
            e.add_field(name="説明", value=c.description)
            e.add_field(name="使用法", value=c.usage)

            if c.brief:
                e.add_field(name="権限", value=c.brief)

            e.add_field(name="エイリアス", value=", ".join([f"`{row}`" for row in c.aliases]))
            return await ctx.reply(embed=e)
        else:
            for i in self.bot.get_command("ticket").get_command("config").commands:
                e.add_field(name=i.name, value=i.description)

            return await ctx.reply(embed=e)

    #ticket config  settime
    @config.command(name="settime", description="営業時間外を設定します。", usage="rsp!ticket config settime <start> <end>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def settime(self, ctx, start:int=None, end:int=None):
        e = discord.Embed(title="Config - settime", description="処理中...", color=0x26b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if not start or not end:
            e.description = None
            e.add_field(name="エラー", value="時間を指定してください。")
            return await msg.edit(embed=e)

        db = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if not db:
            e.description = None
            e.add_field(name="エラー", value="データベースにデータが存在しないよ！")
            return await msg.edit(embed=e)

        try:
            await self.db.execute("UPDATE ticket_config SET time_start=%s WHERE guild=%s", (start, ctx.guild.id))
            await self.db.execute("UPDATE ticket_config SET time_end=%s WHERE guild=%s", (end, ctx.guild.id))

            e.description = None
            e.add_field(name="成功", value=f"{start}-{end}を営業時間外として設定したよ！") #誰か日本語教えてくれ
            return await msg.edit(embed=e)
        except Exception as exc:
            e.description = None
            e.add_field(name="エラー", value=f"```py\n{exc}\n```")
            return await msg.edit(embed=e)

    #ticket config moveto
    @config.command(name="moveto", description="チケットをクローズ後に移動するカテゴリを設定します。", usage="rsp!ticket config moveto <category>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def moveto(self, ctx, category:commands.CategoryChannelConverter=None):
        e = discord.Embed(title="Config - moveto", description="処理中...", color=0x26b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if category is None:
            e.description = None
            e.add_field(name="エラー", value="カテゴリを入力してね！")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if check:
            await self.db.execute(f"UPDATE ticket_config SET movecat={category.id} WHERE guild={ctx.guild.id}")
            e.description = None
            e.add_field(name="成功", value=f"アーカイブ先のカテゴリを{category} ({category.id})に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。インフラ担当課DB係に連絡してください。")
            return await msg.edit(embed=e)

    #ticket config moveclosed
    @config.command(name="moveclosed", description="チケットをクローズ後にカテゴリを移動するか設定します。", usage="rsp!ticket config moveclosed <True/False>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def moveclosed(self, ctx, value:bool=None):
        e = discord.Embed(title="Config - moveclosed", description="処理中...", color=0x26b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if value is None:
            e.description = None
            e.add_field(name="エラー", value="TrueかFalseを入力してね！")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if check:
            await self.db.execute("UPDATE ticket_config SET moveclosed=%s WHERE guild=%s", (int(value), ctx.guild.id))
            e.description = None
            e.add_field(name="成功", value=f"チケットの移動を{value}に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。インフラ担当課DB係に連絡してください。")
            return await msg.edit(embed=e)

    #ticket config mention
    @config.command(name="mention", description="チケット作成時に指定ロールにメンションするかを設定します。", usage="rsp!ticket config mention <on/off>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def mention(self, ctx, mention:bool=None):
        e = discord.Embed(title="Config - mention", description="処理中...", color=0x26b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if mention is None:
            e.description = None
            e.add_field(name="エラー", value="onかoffを入力してね！")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if check:
            await self.db.execute("UPDATE ticket_config SET mention=%s WHERE guild=%s", (int(mention), ctx.guild.id))
            e.description = None
            e.add_field(name="成功", value=f"メンションを{mention}に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。インフラ担当課DB係に連絡してください。")
            return await msg.edit(embed=e)

    #ticket config role
    @config.command(name="role", description="チケット発行時にメンションする役職を設定します。", usage="rsp!ticket config role <role>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def role(self, ctx, role:commands.RoleConverter=None):
        e = discord.Embed(title="Config - role", description="処理中...", color=0x26b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if role is None:
            e.description = None
            e.add_field(name="エラー", value="ロールを入力してね！")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if check:
            await self.db.execute("UPDATE ticket_config SET role=%s WHERE guild=%s", (role.id, ctx.guild.id))
            e.description = None
            e.add_field(name="成功", value=f"メンションする役職を{role} ({role.id})に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。インフラ担当課DB係に連絡してください。")
            return await msg.edit(embed=e)

    #ticket config category
    @config.command(name="category", description="チケット発行時にどのカテゴリにチャンネルを作成するかを設定します。", usage="rsp!ticket config category <category>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def category(self, ctx, category:commands.CategoryChannelConverter=None):
        e = discord.Embed(title="Config - category", description="処理中...", color=0x26b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if category is None:
            e.description = None
            e.add_field(name="エラー", value="カテゴリを入力してね！")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if check:
            await self.db.execute("UPDATE ticket_config SET category=%s WHERE guild=%s", (category.id, ctx.guild.id))
            e.description = None
            e.add_field(name="成功", value=f"チケットのカテゴリを{category} ({category.id})に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。インフラ担当課DB係に連絡してください。")
            return await msg.edit(embed=e)

    #ticket config channel
    @config.command(name="log", description="チケットクローズ後にjsonのログを送信するチャンネルを設定します。", usage="rsp!ticket config log <channel>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def log(self, ctx, channel:commands.TextChannelConverter=None):
        e = discord.Embed(title="Config - log", description="処理中...", color=0x26b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if channel is None:
            e.description = None
            e.add_field(name="エラー", value="チャンネルを入力してね！")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if check:
            await self.db.execute("UPDATE ticket_config SET log=%s WHERE guild=%s", (channel.id, ctx.guild.id))
            e.description = None
            e.add_field(name="成功", value=f"ログチャンネルを{channel} ({channel.id})に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。インフラ担当課DB係に連絡してください。")
            return await msg.edit(embed=e)

    #ticket config delafter
    @config.command(name="delafter", description="チケットクローズ後にチケットを削除するかを設定します。", usage="rsp!ticket config delafter <True/False>", brief="サポート係以上")
    @commands.check(util.is_support)
    async def delafter(self, ctx, close_bool:bool=None):
        e = discord.Embed(title="Config - delafter", description="処理中...", color=0x26b8fa, timestamp=ctx.message.created_at)
        msg = await ctx.send(embed=e)

        if isinstance(ctx.channel, discord.DMChannel):
            e.description = None
            e.add_field(name="エラー", value="DMでは使えないよ！")
            return await msg.edit(embed=e)

        if close_bool is None:
            e.description = None
            e.add_field(name="エラー", value="TrueかFalseを入力してね！")
            return await msg.edit(embed=e)

        check = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if check:
            await self.db.execute("UPDATE ticket_config SET deleteafter=%s WHERE guild=%s", (int(close_bool), ctx.guild.id))
            e.description = None
            e.add_field(name="成功", value=f"{close_bool}に設定したよ！")
            return await msg.edit(embed=e)
        else:
            e.description = None
            e.add_field(name="エラー", value="データが存在しません。インフラ担当課DB係に連絡してください。")
            return await msg.edit(embed=e)

    #ticket close
    @ticket.command(name="close", description="チケットをクローズします。", usage="rsp!ticket close")
    async def _close(self, ctx):
        msg = await ctx.send("> 処理中...")

        if isinstance(ctx.channel, discord.DMChannel):
            return await msg.edit(content="> エラー\nDMでは使えないよ！")

        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (ctx.channel.id,))
        config = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if db and not (db["author"] == ctx.author.id or ctx.author.id in [m.id for m in ctx.guild.get_role(config["role"]).members]):
            return await msg.edit(content=f"> エラー\nチケットの作成者または運営のみがcloseできます。")

        if not db:
            return await msg.edit(content=f"> エラー\nこのチャンネルはサポートチケットじゃないよ！")

        if db["status"] != 1:
            return await msg.edit(content=f"> エラー\nこのチャンネルはすでにcloseされてるよ！")

        await msg.edit(content=f"> Closeしますか？ (close/open)")
        wait = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id)

        if str(wait.content) != "close":
            return await msg.edit(content=f"> キャンセルしました！")

        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = False
        overwrite.add_reactions = False
        overwrite.external_emojis = False

        await ctx.channel.edit(name=ctx.channel.name.replace("ticket", "close"))
        await ctx.channel.set_permissions(self.bot.get_user(db["author"]), overwrite=overwrite)
        await self.db.execute("UPDATE tickets SET status=%s WHERE id=%s", (1, ctx.channel.id))
        await msg.edit(content="> サポートチケットをcloseしました！")
        await ctx.send(content="> Support Ticket Logs (json)", file=discord.File(f"/home/midorichan/RisuPu-Bot/logs/ticket-{ctx.channel.id}.json"))

        if config["log"]:
            embed = discord.Embed(title=f"Ticket Logs {self.bot.get_user(db['author'])} ({db['author']})", color=0x36b8fa)

            await self.bot.get_channel(config["log"]).send(embed=embed, file=discord.File(f"/home/midorichan/RisuPu-Bot/logs/ticket-{ctx.channel.id}.json"))

        if config["deleteafter"] == 1:
            await asyncio.sleep(10)
            await ctx.channel.delete()

        if config["moveclosed"] == 1:
            await ctx.channel.edit(category=ctx.guild.get_channel(config["movecat"]))

    #ticket reopen
    @ticket.command(name="reopen", description="クローズ済みのチケットを再度オープンします。", usage="rsp!ticket reopen <channel>")
    async def reopen(self, ctx, channel:commands.TextChannelConverter=None):
        msg = await ctx.send("> 処理中...")

        if isinstance(ctx.channel, discord.DMChannel):
            return await msg.edit(content="> エラー \nDMでは使えないよ！")

        if channel is None:
            return await msg.edit(content="> エラー \n再オープンするチケットチャンネルを入力してね！")

        db = await self.db.fetchone("SELECT * FROM tickets WHERE id=%s", (channel.id,))
        config = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if not db:
            return await msg.edit(content="> エラー \nそのチャンネルはチケットチャンネルではありません。")

        if db["status"] != 0:
            return await msg.edit(content="> エラー \nそのチケットチャンネルはcloseされていません。")

        if db["author"] == ctx.author.id or ctx.author.id in [m.id for m in ctx.guild.get_role(config["role"]).members]:
            await self.db.execute("UPDATE tickets SET status=1 WHERE id=%s", (channel.id,))

            overwrite = discord.PermissionOverwrite()
            overwrite.send_messages = True
            overwrite.read_messages = True
            overwrite.add_reactions = True
            overwrite.embed_links = True
            overwrite.read_message_history = True
            overwrite.external_emojis = True
            overwrite.attach_files = True

            if channel.category_id == int(config["movecat"]):
                await channel.edit(name=channel.name.replace("close", "ticket"), category=ctx.guild.get_channel(int(config["category"])))
            elif channel.category_id != int(config["category"]):
                await channel.edit(name=channel.name.replace("close", "ticket"), category=ctx.guild.get_channel(int(config["category"])))
            else:
                await channel.edit(name=channel.name.replace("close", "ticket"))

            await channel.set_permissions(ctx.guild.get_member(db["author"]), overwrite=overwrite)

            return await msg.edit(content="> チケットを再オープンしました！")
        else:
            return await msg.edit(content="> エラー \nそのチケットチャンネルは作成者または、運営のみが再オープンできます。")

    #ticket create
    @ticket.command(name="create", description="チケットを発行します。", usage="rsp!ticket create [reason]")
    async def create(self, ctx, *, reason:str=None):
        msg = await ctx.send("> 処理中...")

        if isinstance(ctx.channel, discord.DMChannel):
            return await msg.edit(content="> エラー\nDMでは使えないよ！")

        if reason:
            if len(reason) >= 1024:
                return await msg.edit(content="> エラー\n理由は1024文字以下にしてね！")

        db = await self.db.fetchone("SELECT * FROM ticket_config WHERE guild=%s", (ctx.guild.id,))

        if not db:
            return await msg.edit(content=f"> エラー \nデータが存在しません。インフラ担当課DB係に連絡してください。")

        channel, message = await self.create_ticket(ctx.guild, ctx.author, None)

        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = True
        overwrite.read_messages = True
        overwrite.add_reactions = True
        overwrite.embed_links = True
        overwrite.read_message_history = True
        overwrite.external_emojis = True
        overwrite.attach_files = True
        await message.channel.set_permissions(ctx.author, overwrite=overwrite)

        await msg.edit(content=f"> チケットを作成しました！ \n→ {message.channel.mention}")

    #ticket create
    @ticket.command(name="register", description="チャンネルをチケット扱いにします。", usage="rsp!ticket register [channel]")
    async def register(self, ctx, *, channel:commands.TextChannelConverter=None):
        msg = await ctx.send("> 処理中...")

        if isinstance(ctx.channel, discord.DMChannel):
            return await msg.edit(content="> エラー\nDMでは使えないよ！")

        if channel is None:
            channel = ctx.channel

        await self.create_panel(ctx.guild, ctx.author, channel, reason=None)

        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = True
        overwrite.read_messages = True
        overwrite.add_reactions = True
        overwrite.embed_links = True
        overwrite.read_message_history = True
        overwrite.external_emojis = True
        overwrite.attach_files = True
        await channel.set_permissions(ctx.author, overwrite=overwrite)

        await msg.edit(content=f"> チケット登録しました！")

def setup(bot):
    bot.add_cog(mido_ticket(bot))
