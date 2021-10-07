import discord
from discord.ext import commands, tasks

import aiohttp
import logging
import datetime
import ntplib
import gc
import json
import traceback

import config
import util
from database import Database

bot = commands.AutoShardedBot(shard_count=config.SHARD_COUNT, intents=discord.Intents.all(), command_prefix=config.PREFIX)
bot._close = bot.close

#configs
bot.session = aiohttp.ClientSession(loop=bot.loop)
bot.uptime = datetime.datetime.now()
bot.ntpclient = ntplib.NTPClient()
bot.log_command = True
bot.config = config
bot.color = 0x36b8fa
#Owners (Midorichan, rikusutep, T-taku)
bot.owner_ids = {546682137240403984, 415526420115095554, 462765491325501445}
bot.db = Database
bot.ALLOWED_GUILDS = config.ALLOWED_GUILDS
bot.json_config = None
bot.notice = config.NOTICE

#logging configs
bot.logger = logging.getLogger("discord")
logging.basicConfig(level=logging.WARNING, format="[DebugLog] %(levelname)-8s: %(message)s")

#init remove default help
bot.remove_command("help")

#status
@tasks.loop(minutes=30.0)
async def st_change():
    try:
        await bot.change_presence(status=discord.Status.online, activity=discord.Game(name=f"{config.PREFIX} | りくりくりーくねっ！"))
        print("[System] Auto Status Changed Successfully")
    except:
        print(f"[Error] Auto Status Changed failed")

#gc
@tasks.loop(minutes=30.0)
async def gc_auto():
    try:
        print("[System] Auto GC Start")
        first = gc.collect()
        second = gc.collect()
        print(f"[System] Auto GC End {first} -> {second}")
    except:
        print(f"[Error] Auto GC Failed")

#close
async def shutdown():
    print("[System] Disabling RisuPuBot")

    try:
        await bot.session.close()
    except Exception as e:
        print(f"[Error] {e}")

    try:
        await bot._close()
    except Exception as e:
        print(f"[Error] {e}")

    print("[System] Disabled RisuPuBot")

bot.close = shutdown

#help
@bot.command(name="help", description="ヘルプを表示します。", usage="rsp!help [command]")
async def help(ctx, *, cmd=None):
    e = discord.Embed(title="Help Menu", description="読み込み中...", color=bot.color, timestamp=ctx.message.created_at)
    msg = await ctx.send(embed=e)

    if cmd:
        c = bot.get_command(cmd)

        if c:
            e.title = f"Help - {c.name}"
            e.description = None

            if c.name == "jishaku":
                e.add_field(name="説明", value="jishakuを実行します。")
                e.add_field(name="使用法", value="rsp!jishaku [arg1] [arg2] [arg3] | rsp!jsk [arg1] [arg2] [arg3]")
                e.add_field(name="エイリアス", value=", ".join([f"`{row}`" for row in c.aliases]))
                e.add_field(name="権限", value="オーナーのみ")
                return await msg.edit(embed=e)

            e.add_field(name="説明", value=c.description or "なし")
            e.add_field(name="使用法", value=c.usage or "なし")
            e.add_field(name="エイリアス", value=", ".join([f"`{row}`" for row in c.aliases]) or "なし")
            e.add_field(name="権限", value=c.brief or "メンバー以上")

            return await msg.edit(embed=e)

        else:
            e.description = None
            e.add_field(name="エラー", value="そのコマンドは存在しません。")
            return await msg.edit(embed=e)
    else:
        e.description = None

        for c in bot.commands:
            if c.name == "jishaku":
                e.add_field(name=c.name, value="jishakuを実行します。")
            else:
                e.add_field(name=c.name, value=c.description or "説明なし")

        return await msg.edit(embed=e)

#on_ready
@bot.event
async def on_ready():
    bot._ext = ["cogs.mido_admins", "cogs.mido_info", "cogs.mido_risupu", "cogs.mido_ticket", "cogs.rsp_news", "cogs.rsp_obstacle", "cogs.mido_thread", "jishaku"]
    e = discord.Embed(title="Startup Exceptions", description="", color=bot.color, timestamp=datetime.datetime.now())

    for cog in bot._ext:
        try:
            bot.load_extension(cog)
        except Exception as er:
            print(f"[Error] {cog} load failed → {er}")
            e.description += f"{cog} → {er} \n"
        else:
            print(f"[System] {cog} load")

    try:
        st_change.start()
        print("[System] Status changer start")
    except Exception as exc:
        print("[Error] Status changer start failed")
        e.description += f"Status Changer → {exc} \n"

    try:
        gc_auto.start()
        print("[System] Auto gc start")
    except Exception as exc:
        print("[Error] Auto gc start failed")
        e.description += f"Auto GC → {exc} \n"

    try:
        with open("config.json", "r", encoding="utf-8") as conf:
            bot.json_config = json.load(conf)
        print("[System] Json Config load")
    except Exception as exc:
        print("[Error] Json Config load failed")
        e.description += f"Json Config → {exc} \n"

    if e.description:
        await bot.get_channel(config.LOG_CHANNEL).send(embed=e)

    await bot.change_presence(activity=discord.Activity(name=f"{bot.command_prefix} | りくりくりーくねっ！", type=discord.ActivityType.playing))

    print("[System] on_ready!")

#on_command_error
@bot.event
async def on_command_error(ctx, error):
    if isinstance(ctx.channel, discord.DMChannel):
        print(f"[Error] @{ctx.author} ({ctx.author.id}) → {error}")
    else:
        print(f"[Error] {ctx.guild} ({ctx.guild.id}) - {ctx.author} ({ctx.author.id}) → {error}")

    traceback_error = f"```py\n{''.join(traceback.TracebackException.from_exception(error).format())}\n```"
    if len(str(traceback_error)) >= 1024:
        exc = f"```py\n{error}\n```"
    else:
        exc = traceback_error

    e = discord.Embed(title="Command Exceptions", description=exc, color=bot.color, timestamp=ctx.message.created_at)
    if ctx.guild:
        e.add_field(name="サーバー", value=f"{ctx.guild} (ID: {ctx.guild.id})")
    else:
        e.add_field(name="場所", value=f"DM")
    e.add_field(name="チャンネル", value=f"{ctx.channel} (ID: {ctx.channel.id})")
    e.add_field(name="コマンド", value=f"```\n{ctx.message.content}\n```", inline=False)
    await bot.get_channel(bot.config.LOG_CHANNEL).send(embed=e)

    if isinstance(error, commands.NotOwner):
        e = discord.Embed(title="Error - NotOwner", description="このコマンドは管理者のみが使えるよ！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.CommandNotFound):
        e = discord.Embed(title="Error - CommandNotFound", description="そのコマンドは存在しません。 `rsp!help` と入力して、ヘルプを確認してね！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.DisabledCommand):
        e = discord.Embed(title="Error - DisabledCommand", description="このコマンドは無効化されているよ！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.CommandOnCooldown):
        e = discord.Embed(title="Error - CommandOnCooldown", description=f"クールダウン中です。 {str(error.retry_after)[0:4]}秒後に実行してね！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.MessageNotFound):
        e = discord.Embed(title="Error - MessageNotFound", description=f"メッセージ {error.argument} は見つからなかったよ！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.MemberNotFound):
        e = discord.Embed(title="Error - MessageNotFound", description=f"メンバー {error.argument} は見つからなかったよ！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.UserNotFound):
        e = discord.Embed(title="Error - UserNotFound", description=f"ユーザー {error.argument} は見つからなかったよ！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.ChannelNotFound):
        e = discord.Embed(title="Error - ChannelNotFound", description=f"チャンネル {error.argument} は見つからなかったよ！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.RoleNotFound):
        e = discord.Embed(title="Error - RoleNotFound", description=f"ロール {error.argument} は見つからなかったよ！", color=0xff3d3d, timestamp=ctx.message.created_at)

    elif isinstance(error, commands.MissingPermissions):
        e = discord.Embed(title="Error - MissingPermissions", description=f"権限が不足しているよ！", color=0xff3d3d, timestamp=ctx.message.created_at)
        p = [bot.json_config["roles"].get(i) for i in error.missing_perms]
        e.add_field(name="不足している権限", value=', '.join(p))

    elif isinstance(error, commands.BotMissingPermissions):
        e = discord.Embed(title="Error - BotMissingPermissions", description=f"Botの権限が不足しているよ！", color=0xff3d3d, timestamp=ctx.message.created_at)
        p = [bot.json_config["roles"].get(i) for i in error.missing_perms]
        e.add_field(name="不足している権限", value=', '.join(p))

    elif isinstance(error, commands.CheckFailure):
        e = discord.Embed(title="Error - CheckFailure", description="このコマンドは使えないよ！", color=0xff3d3d, timestamp=ctx.message.created_at)

    else:
        e = discord.Embed(title="Error - unknown", description=f"```py\n{error}\n```", color=0xff3d3d, timestamp=ctx.message.created_at)

    if e.title.startswith("Error"):
        try:
            return await ctx.send(embed=e)
        except:
            try:
                return await ctx.author.send(embed=e)
            except:
                return


#on_command
@bot.event
async def on_command(ctx):
    e = discord.Embed(title="Command Logs", color=bot.color, timestamp=ctx.message.created_at)
    if isinstance(ctx.message.channel, discord.DMChannel):
        e.set_thumbnail(url=ctx.author.avatar_url_as(static_format=("png")))
        e.add_field(name="実行場所", value=f"DM")
        e.add_field(name="実行ユーザー名", value=f"{ctx.author} \n(ID: {ctx.author.id})")
        e.add_field(name="実行日時", value=ctx.message.created_at.strftime('%Y/%m/%d %H:%M:%S'))
        e.add_field(name="実行コマンド", value=f"```{ctx.message.content}```", inline=False)
    else:
        e.set_thumbnail(url=ctx.author.avatar_url_as(static_format=("png")))
        e.add_field(name="実行サーバー", value=f"{ctx.guild.name} \n(ID: {ctx.guild.id})")
        e.add_field(name="実行ユーザー名", value=f"{ctx.author} \n(ID: {ctx.author.id})")
        e.add_field(name="実行日時", value=ctx.message.created_at.strftime('%Y/%m/%d %H:%M:%S'))
        e.add_field(name="チャンネル", value=f"{ctx.channel} \n(ID: {ctx.channel.id})")
        e.add_field(name="実行コマンド", value=f"```{ctx.message.content}```", inline=False)

    await bot.get_channel(bot.config.LOG_CHANNEL).send(embed=e)

    if bot.log_command:
        if isinstance(ctx.message.channel, discord.DMChannel):
            print(f"[Log] {ctx.author} ({ctx.author.id}) → {ctx.message.content} @DM")
        else:
            print(f"[Log] {ctx.author} ({ctx.author.id}) → {ctx.message.content} @{ctx.guild} ({ctx.guild.id}) - {ctx.channel} ({ctx.channel.id})")

#guild join
@bot.event
async def on_guild_join(guild):
    print(f"[System] {guild} join.")

    if not guild.id in bot.ALLOWED_GUILDS:
        await guild.leave()
        print(f"[System] {guild} left (Not Allowed)")

print("[System] Enabling RisuPu Bot...")
bot.run(config.BOT_TOKEN)
