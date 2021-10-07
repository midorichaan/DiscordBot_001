import discord
from discord.ext import commands

import threads
import asyncio
import util

class mido_thread(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.threadutil = threads.ThreadHTTP(bot)

    #reactions
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if str(payload.emoji) == "📝":
            try:
                await self.threadutil.create_thread_with_message(payload.channel_id, payload.message_id, f"thread-{payload.user_id}", 1440)
            except Exception as exc:
                print(f"[Error] {exc}")
            else:
                await self.bot.get_channel(payload.channel_id).send(f"> スレッドを作成しました！\n→ <#{payload.message_id}>")

    #threads
    @commands.group(name="threads", aliases=["thread"], description="thread関連のコマンドです。", usage="rsp!threads <args> [args]", invoke_without_command=True)
    async def threads(self, ctx):
        pass

    #threads help
    @threads.command(name="help", description="threadsのヘルプです。", usage="rsp!threads help [command]")
    async def help(self, ctx, cmd=None):
        e = discord.Embed(title="Threads help", description="処理中...", color=self.bot.color, timestamp=ctx.message.created_at)
        m = await ctx.send(embed=e)

        e.description = None

        if cmd:
            c = self.bot.get_command("threads").get_command(cmd)

            if c:
                e.title = f"Threads - {c.name}"
                e.add_field(name="説明", value=c.description or "説明なし")
                e.add_field(name="使用法", value=c.usage or "不明")
                e.add_field(name="エイリアス", value=", ".join([f"`{row}`" for row in c.aliases]))
                return await m.edit(embed=e)
            else:
                for c in self.bot.get_command("threads").commands:
                    e.add_field(name=c.name, value=c.description or "説明なし")

                return await m.edit(embed=e)
        else:
            for c in self.bot.get_command("threads").commands:
                e.add_field(name=c.name, value=c.description or "説明なし")

            return await m.edit(embed=e)

    #addmember
    @threads.command(name="addmember", description="メンバーをスレッドに追加します。", usage="rsp!threads addmember <thread_id> <members>", brief="運営チームのみ")
    @commands.check(util.is_risupu_staff)
    async def addmember(self, ctx, thread_id: int=None, members:commands.Greedy[discord.Member]=None):
        m = await ctx.send("> 処理中...")

        if not thread_id:
            return await m.edit(content="> スレッドIDを指定してね！")

        if not members:
            return await m.edit(content="> メンバーを指定してね！")


        tasks = []
        for i in members:
            tasks.append(self.threadutil.add_member(thread_id, i.id))

        try:
            await asyncio.gather(*tasks)
        except Exception as exc:
            return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
        else:
            return await m.edit(content=f"> {len(members)}人のメンバーをスレッドに追加しました！")

    #removemember
    @threads.command(name="removemember", aliases=["rmmember"], description="メンバーをスレッドから削除します。", usage="rsp!threads removemember <thread_id> <members>", brief="運営チームのみ")
    @commands.check(util.is_risupu_staff)
    async def removemember(self, ctx, thread_id: int=None, members:commands.Greedy[discord.Member]=None):
        m = await ctx.send("> 処理中...")

        if not thread_id:
            return await m.edit(content="> スレッドIDを指定してね！")

        if not members:
            return await m.edit(content="> メンバーを指定してね！")

        tasks = []
        for i in members:
            tasks.append(self.threadutil.remove_member(thread_id, i.id))

        try:
            await asyncio.gather(*tasks)
        except Exception as exc:
            return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
        else:
            return await m.edit(content=f"> {len(members)}人のメンバーをスレッドから削除しました！")

    #create
    @threads.command(name="create", description="スレッドを作成します。", usage="rsp!threads create <name> [channel] [message] [archive]")
    async def create(self, ctx, name: str=None, channel: commands.TextChannelConverter=None, message: commands.MessageConverter=None, archive: int=1440):
        m = await ctx.send("> 処理中...")

        if not name:
            return await m.edit(content="> スレッド名を指定してください。")

        if not channel:
            channel = ctx.channel

        if message:
            try:
                pl = await self.threadutil.create_thread_with_message(channel.id, message.id, name, archive)
            except Exception as exc:
                return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
            else:
                return await m.edit(content=f"> スレッドを作成しました！ \n → <#{pl['id']}>")
        else:
            try:
                pl = await self.threadutil.create_thread(channel.id, name, archive)
            except Exception as exc:
                return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
            else:
                return await m.edit(content=f"> スレッドを作成しました！ \n → <#{pl['id']}>")

    #archive
    @threads.command(name="archive", description="スレッドをアーカイブします。", usage="rsp!threads archive <thread_id>", brief="運営チームのみ")
    @commands.check(util.is_risupu_staff)
    async def archive(self, ctx, thread: int=None):
        m = await ctx.send("> 処理中...")

        if not thread:
            return await m.edit(content="> スレッドのIDを指定してください。")

        try:
            await self.threadutil.archive_thread(thread)
        except Exception as exc:
            return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
        else:
            return await m.edit(content="> スレッドをアーカイブしました！")

    #delete
    @threads.command(name="delete", description="スレッドを削除します。", usage="rsp!threads delete <thread_id>", brief="運営チームのみ")
    @commands.check(util.is_risupu_staff)
    async def delete(self, ctx, thread_id: int=None):
        m = await ctx.send("> 処理中...")

        if not thread_id:
            return await m.edit(content="> スレッドのIDを指定してください。")

        try:
            await self.bot.http.delete_channel(thread_id)
        except Exception as exc:
            return await m.edit(content=f"> エラー \n```py\n{exc}\n```")
        else:
            return await m.edit(content="> スレッドを削除しました！")

def setup(bot):
    bot.add_cog(mido_thread(bot))
