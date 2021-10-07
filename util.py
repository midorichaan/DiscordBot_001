from discord.ext import commands

#is_owner
def is_owner(ctx):
    if getattr(ctx.bot, "owner_id", None):
        return ctx.author.id == ctx.bot.owner_id
    elif getattr(ctx.bot, "owner_ids", None):
        return ctx.author.id in ctx.bot.owner_ids
    else:
        return False

#is_admin
def is_admin(ctx):
    #RisuPu本サーバー @RisuPu Bot課
    if ctx.author.id in [m.id for m in ctx.bot.get_guild(461153681971216384).get_role(865875738624131072).members]:
        return True
    else:
        return False

#is_mcs
def is_mcs(ctx):
    #RisuPu本サーバー @MCS担当課-管理係
    if ctx.author.id in [m.id for m in ctx.bot.get_guild(461153681971216384).get_role(811106010877263914).members]:
        return True
    else:
        return False

#is_infra
def is_infra(ctx):
    #RisuPu本サーバー @インフラ担当課
    if ctx.author.id in [m.id for m in ctx.bot.get_guild(461153681971216384).get_role(783487218903810058).members]:
        return True
    else:
        return False

#is_support
def is_support(ctx):
    #RisuPuサポートサーバー @Admin-Teams
    if ctx.author.id in [m.id for m in ctx.bot.get_guild(703920815652995072).get_role(703921568719437844).members]:
        return True
    else:
        return False

#is_risupu_staff
def is_risupu_staff(ctx):
    #RisuPu本サーバー @運営チーム
    if ctx.author.id in [m.id for m in ctx.bot.get_guild(461153681971216384).get_role(668792082680250368).members]:
        return True
    else:
        return False

#is_risupu_manager
def is_risupu_manager(ctx):
    if ctx.author.id in [m.id for m in ctx.bot.get_guild(461153681971216384).get_role(680992224435240989).members]:
        return True
    else:
        return False

#FetchUserConverter
class FetchUserConverter(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except:
            try:
                return await commands.UserConverter().convert(ctx, argument)
            except:
                return None
