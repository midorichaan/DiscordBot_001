import discord
from discord.ext import commands

import asyncio
import traceback
import io
import textwrap
import inspect
import subprocess
from contextlib import redirect_stdout

import util

class mido_admins(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    #create shell process
    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    #strip code
    def strip_code(self, content):
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        return content.strip('` \n')

    #restart
    @commands.command(name="restart", description="Botを再起動します。", usage="rsp!restart", brief="オーナーのみ")
    @commands.check(util.is_owner)
    async def restart(self, ctx):
        msg = await ctx.reply("> 処理中...")

        task = [msg.edit(content=f"> Botを再起動します...しばらくお待ちください..."),
                self.bot.close()
               ]

        asyncio.gather(*task)

    #shell
    @commands.command(pass_context=True, name="shell", aliases=["sh"], description="shellコマンドを実行します。", usage="rsp!shell <command> | rsp!sh <command>", brief="担当者のみ")
    @commands.check(util.is_admin)
    async def shell(self, ctx, *, command=None):
        if not command:
            return await ctx.reply("> 実行するコマンドを入力してね！")

        stdout, stderr = await self.run_process(command)

        if stderr:
            text = f"```\nstdout: \n{stdout} \nstderr: \n{stderr}\n```"
        else:
            text = f"```\nstdout: \n{stdout} \nstderr: \nnone\n```"

        try:
            return await ctx.reply(text)
        except Exception as exc:
            return await ctx.reply(f"```py\n{exc}\n```")

    #addguild
    @commands.command(name="addguild", description="Botが参加できるサーバーを追加します。", usage="rsp!addguild <guild_id>", brief="担当者のみ")
    @commands.check(util.is_admin)
    async def addguild(self, ctx, guild_id:int=None):
        if guild_id is None:
            await ctx.message.add_reaction("❌")
            return await ctx.reply("> サーバーIDを入力してください。")

        try:
            if guild_id in self.bot.ALLOWED_GUILDS:
                await ctx.message.add_reaction("❌")
                return await ctx.reply("> すでに追加されています。")

            self.bot.ALLOWED_GUILDS.append(guild_id)
            await ctx.message.add_reaction("✅")
        except Exception as exc:
            await ctx.message.add_reaction("❌")
            return await ctx.reply(f"```py\n{exc}\n```")

    #delguild
    @commands.command(name="delguild", description="Botが参加できるサーバー 一覧から削除します。", usage="rsp!delguild <guild_id>", brief="担当者のみ")
    @commands.check(util.is_admin)
    async def delguild(self, ctx, guild_id:int=None):
        if guild_id is None:
            await ctx.message.add_reaction("❌")
            return await ctx.reply("> サーバーIDを入力してください。")

        try:
            if not guild_id in self.bot.ALLOWED_GUILDS:
                await ctx.message.add_reaction("❌")
                return await ctx.reply("> そのIDのデータが存在しません。")

            self.bot.ALLOWED_GUILDS.remove(guild_id)
            await ctx.message.add_reaction("✅")

            try:
                await self.bot.on_guild_join(self.bot.get_guild(guild_id))
            except Exception as exc:
                await ctx.reply(f"```py\n{exc}\n```")
        except Exception as exc:
            await ctx.message.add_reaction("❌")
            return await ctx.reply(f"```py\n{exc}\n```")

    #r_danny's eval
    @commands.command(pass_context=True, name="eval", description="evalを実行します。", usage="rsp!eval <code>", brief="担当者のみ")
    @commands.check(util.is_admin)
    async def eval(self, ctx, *, body: str=None):
        if not body:
            await ctx.reply("> 評価するコードを入力してね！")
            try:
                body = (await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=600)).content
            except asyncio.TimeoutError:
                return await ctx.reply("タイムアウトしたよ...")

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'self': self,
            '_': self._last_result
        }

        env.update(globals())

        body = self.strip_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as exc:
            await ctx.message.add_reaction("❌")
            return await ctx.reply(f"```py\n{exc.__class__.__name__}: {exc}\n```")

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            await ctx.message.add_reaction("❌")
            value = stdout.getvalue()
            await ctx.reply(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\U00002b55")
            except:
                pass

            if ret is None:
                if value:
                    await ctx.reply(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.reply(f'```py\n{value}{ret}\n```')

def setup(bot):
    bot.add_cog(mido_admins(bot))
