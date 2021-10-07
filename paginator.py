import asyncio

class CannotPaginate(Exception):
    pass

class EmbedPaginator:

    def __init__(self, ctx, *, entries, timeout=30.0):
        self.ctx = ctx
        self.bot = ctx.bot
        self.entries = entries
        self.max_page = len(entries) - 1
        self.page = 0
        self.timeout = timeout

        if ctx.guild is None:
            perm = self.ctx.channel.permissions_for(ctx.bot.user)
        else:
            perm = self.ctx.channel.permissions_for(ctx.guild.me)

        if not perm.embed_links:
            raise CannotPaginate("Embed Links permission is required")
        if not perm.send_messages:
            raise CannotPaginate("Send Messages permission is required")
        if not perm.add_reactions:
            raise CannotPaginate("Add Reactions permission is required")
        if not perm.read_message_history:
            raise CannotPaginate("Read Message History permission is required")

    def get_page(self, page:int):
        self.page = page
        return self.entries[page]

    async def paginate(self):
        msg = await self.ctx.send(embed=self.entries[self.page])

        tasks = [msg.add_reaction('⏮'),
                 msg.add_reaction('◀'),
                 msg.add_reaction('⏹️'),
                 msg.add_reaction('▶'),
                 msg.add_reaction('⏭'),
                 msg.add_reaction('🔢')
                ]

        asyncio.gather(*tasks)

        check = lambda r,u: r.message.id == msg.id and u.id == self.ctx.message.author.id

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=self.timeout)
            except asyncio.TimeoutError:
                cl = [msg.remove_reaction('⏮', self.bot.user),
                      msg.remove_reaction('◀', self.bot.user),
                      msg.remove_reaction('⏹️', self.bot.user),
                      msg.remove_reaction('▶', self.bot.user),
                      msg.remove_reaction('⏭', self.bot.user),
                      msg.remove_reaction('🔢', self.bot.user)
                     ]
                asyncio.gather(*cl)

                break
            except:
                cl = [msg.remove_reaction('⏮', self.bot.user),
                      msg.remove_reaction('◀', self.bot.user),
                      msg.remove_reaction('⏹️', self.bot.user),
                      msg.remove_reaction('▶', self.bot.user),
                      msg.remove_reaction('⏭', self.bot.user),
                      msg.remove_reaction('🔢', self.bot.user)
                     ]
                asyncio.gather(*cl)

                break

            try:
                await msg.remove_reaction(reaction, user)
            except:
                pass

            if str(reaction) == "⏮":
                embed = self.get_page(0)
            elif str(reaction) == "◀":
                if self.page == 0:
                    embed = self.get_page(self.max_page)
                else:
                    embed = self.get_page(self.page - 1)
            elif str(reaction) == "⏹️":
                cl = [msg.remove_reaction('⏮', self.bot.user),
                      msg.remove_reaction('◀', self.bot.user),
                      msg.remove_reaction('⏹️', self.bot.user),
                      msg.remove_reaction('▶', self.bot.user),
                      msg.remove_reaction('⏭', self.bot.user),
                      msg.remove_reaction('🔢', self.bot.user)
                     ]
                asyncio.gather(*cl)

                break
            elif str(reaction) == "▶":
                if self.page == self.max_page:
                    embed = self.get_page(0)
                else:
                    embed = self.get_page(self.page + 1)
            elif str(reaction) == "⏭️":
                embed = self.get_page(self.max_page)
            elif str(reaction) == "🔢":
                try:
                    check = await self.ctx.reply("> 何ページに移動しますか？")
                except:
                    check = await self.ctx.send("> 何ページに移動しますか？")

                try:
                    m = await self.bot.wait_for("message", check=lambda message: message.channel.id == self.ctx.channel.id and message.author.id == self.ctx.message.author.id and str(message.content).isdigit(), timeout=self.timeout)
                except:
                    embed = self.get_page(0)
                else:
                    task = [check.delete(),
                            m.delete()
                           ]
                    asyncio.gather(*task)

                    p = int(m.content) - 1

                    if p > self.max_page:
                        embed = self.get_page(self.max_page)
                    elif p < 0:
                        embed = self.get_page(0)
                    else:
                        embed = self.get_page(p)

            await msg.edit(embed=embed)
