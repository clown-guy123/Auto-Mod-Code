import os
import discord
import logging
import json
import random
import asyncio
from discord.ext import commands, tasks
from discord import app_commands

# Configure logging to both file and console.
logging.basicConfig(level=logging.INFO,
                    filename="bot.log",
                    format="%(asctime)s:%(levelname)s:%(name)s: %(message)s")

# Set up intents.
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create the bot instance.
bot = commands.Bot(command_prefix="!", intents=intents)

# Global settings (customizable via /settings).
settings = {
    "prefix": "!",
    "mod_mail_channel": None,    # Set the channel ID for mod mail.
    "logging_channel": None,     # Set the channel ID for moderation logs.
    "questions": [
        "Why Do You Want To Be A Mod?",
        "What Experience Do You Have?"
    ],
    "banned_words": ["badword1", "badword2"]  # Example banned words.
}

# Background task to update the bot's status every 30 minutes.
@tasks.loop(minutes=30)
async def update_status():
    server_count = len(bot.guilds)
    status = f"🤡 MADE BY CLOWN ⭐ | WATCHING {server_count} SERVERS 👮"
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))

@update_status.before_loop
async def before_update_status():
    await bot.wait_until_ready()

# Utility function: Log moderation actions.
async def log_action(guild: discord.Guild, message: str):
    logging.info(message)
    if settings.get("logging_channel"):
        channel = guild.get_channel(settings["logging_channel"])
        if channel:
            await channel.send(message)

# All commands and events are organized in a Cog.
class MyBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /prefix - Set bot prefixes.
    @app_commands.command(name="prefix", description="Set The Bot Prefix(es)")
    async def prefix(self, interaction: discord.Interaction, prefixes: str):
        settings["prefix"] = prefixes
        await interaction.response.send_message(f"Prefix Updated To: {prefixes}".title(), ephemeral=True)

    # /ping - Check bot latency.
    @app_commands.command(name="ping", description="Check The Bot Latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! Latency: {latency}ms".title())

    # /ban - Ban a member.
    @app_commands.command(name="ban", description="Ban A Member")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No Reason Provided"):
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(f"{member.mention} Has Been Banned. Reason: {reason}".title())
            await log_action(interaction.guild, f"{interaction.user} banned {member} for {reason}")
        except Exception as e:
            await interaction.response.send_message(f"Failed To Ban {member.mention}. Error: {str(e)}".title(), ephemeral=True)

    # /timeout - Timeout a member.
    @app_commands.command(name="timeout", description="Timeout A Member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No Reason Provided"):
        try:
            until = discord.utils.utcnow() + discord.timedelta(seconds=duration)
            await member.timeout(until, reason=reason)
            await interaction.response.send_message(f"{member.mention} Has Been Timed Out For {duration} Seconds. Reason: {reason}".title())
            await log_action(interaction.guild, f"{interaction.user} timed out {member} for {duration} seconds: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"Failed To Timeout {member.mention}. Error: {str(e)}".title(), ephemeral=True)

    # /kick - Kick a member.
    @app_commands.command(name="kick", description="Kick A Member")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No Reason Provided"):
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"{member.mention} Has Been Kicked. Reason: {reason}".title())
            await log_action(interaction.guild, f"{interaction.user} kicked {member}: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"Failed To Kick {member.mention}. Error: {str(e)}".title(), ephemeral=True)

    # /unban - Unban a user.
    @app_commands.command(name="unban", description="Unban A Member")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: int):
        try:
            bans = await interaction.guild.bans()
            for ban_entry in bans:
                if ban_entry.user.id == user_id:
                    await interaction.guild.unban(ban_entry.user)
                    await interaction.response.send_message(f"Unbanned {ban_entry.user.mention}".title())
                    await log_action(interaction.guild, f"{interaction.user} unbanned {ban_entry.user}")
                    return
            await interaction.response.send_message("User Not Found In Ban List.".title(), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed To Unban. Error: {str(e)}".title(), ephemeral=True)

    # /dm - Send a direct message to a user.
    @app_commands.command(name="dm", description="Send A Direct Message To A User")
    async def dm(self, interaction: discord.Interaction, user: discord.User, message: str):
        try:
            await user.send(message)
            await interaction.response.send_message(f"Message Sent To {user.mention}".title())
        except Exception as e:
            await interaction.response.send_message(f"Failed To Send DM. Error: {str(e)}".title(), ephemeral=True)

    # /embed - Send an embed from JSON code (with an interactive button stub).
    @app_commands.command(name="embed", description="Send An Embed With JSON Code")
    async def embed(self, interaction: discord.Interaction, json_code: str, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        try:
            data = json.loads(json_code)
            embed_obj = discord.Embed.from_dict(data)
        except Exception as e:
            await interaction.response.send_message(f"Invalid JSON Code. Error: {str(e)}".title(), ephemeral=True)
            return

        view = discord.ui.View()
        button = discord.ui.Button(label="Enter JSON Code", style=discord.ButtonStyle.primary)
        async def button_callback(button_int: discord.Interaction):
            await button_int.response.send_message("Button Clicked! (Feature Under Development)".title(), ephemeral=True)
        button.callback = button_callback
        view.add_item(button)

        await target_channel.send(embed=embed_obj, view=view)
        await interaction.response.send_message(f"Embed Sent In {target_channel.mention}".title())

    # /apply - Start the mod application process.
    @app_commands.command(name="apply", description="Apply For Mod")
    async def apply(self, interaction: discord.Interaction):
        view = discord.ui.View()
        yes_button = discord.ui.Button(label="Yes", style=discord.ButtonStyle.success)
        no_button = discord.ui.Button(label="No", style=discord.ButtonStyle.danger)
        async def yes_callback(button_int: discord.Interaction):
            await button_int.response.send_message("Application Process Started. Please Check Your DMs For Questions.".title(), ephemeral=True)
            try:
                await interaction.user.send("**MOD APPLICATION**\n" + "\n".join(settings["questions"]))
            except Exception as e:
                await button_int.followup.send(f"Failed To DM You. Error: {str(e)}".title(), ephemeral=True)
        async def no_callback(button_int: discord.Interaction):
            await button_int.response.send_message("Application Cancelled.".title(), ephemeral=True)
        yes_button.callback = yes_callback
        no_button.callback = no_callback
        view.add_item(yes_button)
        view.add_item(no_button)
        await interaction.response.send_message("Are You Sure You Would Like To Apply For Mod? **Note: We Will Only Choose People Who Are Serious About This Job**".title(), view=view, ephemeral=True)

    # /purge - Purge messages with optional filters.
    @app_commands.command(name="purge", description="Purge Messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, count: int, filters: str = None):
        filter_list = [f.strip().lower() for f in filters.split(",")] if filters else []
        def check(msg: discord.Message):
            if "bot" in filter_list and msg.author.bot:
                return False
            return True
        try:
            deleted = await interaction.channel.purge(limit=count, check=check)
            await interaction.response.send_message(f"Purged {len(deleted)} Messages.".title(), ephemeral=True)
            await log_action(interaction.guild, f"{interaction.user} purged {len(deleted)} messages in {interaction.channel}")
        except Exception as e:
            await interaction.response.send_message(f"Failed To Purge Messages. Error: {str(e)}".title(), ephemeral=True)

    # /flip - Flip a coin.
    @app_commands.command(name="flip", description="Flip A Coin")
    async def flip(self, interaction: discord.Interaction, user: discord.User, choice: str):
        result = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(f"{user.mention} {choice.upper()} 50% OR {result.upper()} 50%? RESULT: {result.upper()}".title())

    # /vacation - For mods to set vacation status.
    @app_commands.command(name="vacation", description="Only For Mods: Go On Vacation")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def vacation(self, interaction: discord.Interaction, time: str, reason: str):
        await interaction.response.send_message(f"{interaction.user.mention} Is Now On Vacation For {time}. Reason: {reason}".title())
        await log_action(interaction.guild, f"{interaction.user} set vacation for {time}: {reason}")

    # /promote - Promote a member (add a role).
    @app_commands.command(name="promote", description="Promote A User")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def promote(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"{member.mention} Has Been Promoted With {role.name}".title())
            await log_action(interaction.guild, f"{interaction.user} promoted {member} with role {role.name}")
        except Exception as e:
            await interaction.response.send_message(f"Failed To Promote {member.mention}. Error: {str(e)}".title(), ephemeral=True)

    # /demote - Demote a member (remove a role).
    @app_commands.command(name="demote", description="Demote A User")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def demote(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role = None):
        try:
            if role:
                await member.remove_roles(role)
                await interaction.response.send_message(f"{member.mention} Has Been Demoted And {role.name} Removed".title())
                await log_action(interaction.guild, f"{interaction.user} demoted {member} by removing role {role.name}")
            else:
                if member.roles:
                    highest_role = member.roles[-1]
                    await member.remove_roles(highest_role)
                    await interaction.response.send_message(f"{member.mention} Has Been Demoted And {highest_role.name} Removed".title())
                    await log_action(interaction.guild, f"{interaction.user} demoted {member} by removing role {highest_role.name}")
                else:
                    await interaction.response.send_message("User Has No Roles To Remove.".title(), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed To Demote {member.mention}. Error: {str(e)}".title(), ephemeral=True)

    # /invite - Get the bot's invite link.
    @app_commands.command(name="invite", description="Get The Bot Invite Link")
    async def invite(self, interaction: discord.Interaction):
        invite_link = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        await interaction.response.send_message(f"Invite Me Using This Link: {invite_link}".title())

    # /settings - Display current bot settings.
    @app_commands.command(name="settings", description="Customize The Bot Settings")
    async def settings_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Bot Settings", color=discord.Color.blue())
        embed.add_field(name="Prefix", value=settings["prefix"], inline=False)
        embed.add_field(name="Mod Mail Channel", value=str(settings["mod_mail_channel"]), inline=False)
        embed.add_field(name="Logging Channel", value=str(settings["logging_channel"]), inline=False)
        embed.add_field(name="Application Questions", value="\n".join(settings["questions"]), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /modmail - Allow users to send a message to the mods.
    @app_commands.command(name="modmail", description="Send A Message To Mods")
    async def modmail(self, interaction: discord.Interaction, message: str):
        if settings.get("mod_mail_channel"):
            channel = interaction.guild.get_channel(settings["mod_mail_channel"])
            if channel:
                await channel.send(f"Mod Mail From {interaction.user.mention}: {message}".title())
                await interaction.response.send_message("Your Message Has Been Sent To The Mods.".title(), ephemeral=True)
                return
        await interaction.response.send_message("Mod Mail Channel Not Configured.".title(), ephemeral=True)

    # /feedback - Send feedback about the bot.
    @app_commands.command(name="feedback", description="Send Feedback About The Bot")
    async def feedback(self, interaction: discord.Interaction, message: str):
        logging.info(f"Feedback from {interaction.user}: {message}")
        if settings.get("logging_channel"):
            channel = interaction.guild.get_channel(settings["logging_channel"])
            if channel:
                await channel.send(f"Feedback from {interaction.user.mention}: {message}")
        await interaction.response.send_message("Thank You For Your Feedback!".title(), ephemeral=True)

    # /help - Display an interactive help message listing all commands.
    @app_commands.command(name="help", description="Display Help Information")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Bot Help", description="List Of Available Commands:", color=discord.Color.green())
        commands_list = [
            "/prefix [prefixes] - Set The Bot Prefix",
            "/ping - Check The Bot Latency",
            "/ban [member] [reason] - Ban A Member",
            "/timeout [member] [duration] [reason] - Timeout A Member",
            "/kick [member] [reason] - Kick A Member",
            "/unban [user_id] - Unban A Member",
            "/dm [user] [message] - Send A DM To A User",
            "/embed [json_code] [channel] - Send An Embed",
            "/apply - Apply For Mod",
            "/purge [count] [filters] - Purge Messages",
            "/flip [user] [choice] - Flip A Coin",
            "/vacation [time] [reason] - Go On Vacation (Mods Only)",
            "/promote [member] [role] - Promote A Member",
            "/demote [member] [role] - Demote A Member",
            "/invite - Get The Bot Invite Link",
            "/settings - Display Bot Settings",
            "/modmail [message] - Send A Message To Mods",
            "/feedback [message] - Send Feedback About The Bot",
            "/help - Display This Help Message"
        ]
        embed.description = "\n".join(commands_list)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Register the cog.
bot.add_cog(MyBot(bot))

# Auto-moderation: Delete messages containing banned words.
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if any(bad_word.lower() in message.content.lower() for bad_word in settings["banned_words"]):
        try:
            await message.delete()
            await message.channel.send("Message Deleted Due To Inappropriate Content.".title(), delete_after=5)
            await log_action(message.guild, f"Deleted message from {message.author} for banned content.")
        except Exception as e:
            logging.error(f"Error deleting message: {e}")
    await bot.process_commands(message)

# Global error handler for app commands.
@bot.event
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You Do Not Have Permission To Use This Command.".title(), ephemeral=True)
    else:
        await interaction.response.send_message(f"An Error Occurred: {str(error)}".title(), ephemeral=True)
    logging.error(f"Error in command {interaction.command}: {error}")

# On ready: Sync commands and start background tasks.
@bot.event
async def on_ready():
    print(f"BOT IS READY. LOGGED IN AS {bot.user}".upper())
    update_status.start()
    try:
        synced = await bot.tree.sync()
        print(f"SYNCHED {len(synced)} COMMANDS".upper())
    except Exception as e:
        print(f"Error Syncing Commands: {e}".title())

# Run the bot using the token from environment variables.
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("TOKEN not found in environment variables!")
else:
    bot.run(TOKEN)
