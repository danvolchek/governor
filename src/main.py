# Governor
# Written by aquova, 2020-2023
# https://github.com/aquova/governor

import re
import urllib.parse

import discord
import requests

import custom
from client import client
from config import CMD_PREFIX, DISCORD_KEY, XP_OFF
from log import parse_log

"""
Update User Count

Updates the bot's 'activity' to reflect the number of users
"""
async def update_user_count(guild: discord.Guild):
    activity_mes = f"{guild.member_count} members!"
    activity_object = discord.Activity(name=activity_mes, type=discord.ActivityType.watching)
    await client.change_presence(activity=activity_object)

"""
On Ready

Runs when Discord bot is first brought online
"""
@client.event
async def on_ready():
    print("Logged in as:")
    if client.user:
        print(client.user.name)
        print(client.user.id)

"""
On Thread Create

Occurs when a new thread is created in the server
"""
@client.event
async def on_thread_create(thread: discord.Thread):
    await thread.join()

"""
On Guild Available

Runs when a guild (server) that the bot is connected to becomes ready
"""
@client.event
async def on_guild_available(guild: discord.Guild):
    # This is 100% going to cause issues if we ever want to host on more than one server
    await client.setup(guild)
    await client.sync_guild(guild)

    await update_user_count(guild)

"""
On Member Join

Runs when a user joins the server
"""
@client.event
async def on_member_join(user: discord.Member):
    await update_user_count(user.guild)

"""
On Member Remove

Runs when a member leaves the server
"""
@client.event
async def on_member_remove(user: discord.Member):
    client.tracker.remove_from_cache(user.id)
    await update_user_count(user.guild)

"""
On Message

Runs when a user posts a message
"""
@client.event
async def on_message(message: discord.Message):
    # Ignore bots completely (including ourself)
    if message.author.bot:
        return

    # For now, completely ignore DMs
    if isinstance(message.channel, discord.channel.DMChannel):
        return

    # Check first if we're toggling debug mode
    # Need to do this before we discard a message
    if client.dbg.check_toggle(message):
        await client.dbg.toggle_debug(message)
        return
    elif client.dbg.should_ignore_message(message):
        return

    # Keep track of the user's message for dynamic slowmode
    await client.thermometer.user_spoke(message)
    # Check if we need to congratulate a user on getting a new role
    # Don't award XP if posting in specified disabled channels
    if message.channel.id not in XP_OFF and message.guild is not None:
        lvl_up_message = await client.tracker.give_xp(message.author)
        if lvl_up_message:
            await message.channel.send(lvl_up_message)

    for log_link in re.findall(r"https://smapi.io/log/[a-zA-Z0-9]{32}", message.content):
        log_info = parse_log(log_link)
        await message.channel.send(log_info)

    for community_wiki_link in re.findall(r"https://stardewcommunitywiki\.com/[a-zA-Z0-9_/:\-%]*", message.content):
        new_wiki ="https://stardewvalleywiki.com"

        link_path = urllib.parse.urlparse(community_wiki_link).path
        new_url = urllib.parse.urljoin(new_wiki, link_path)
        await message.channel.send(f"I notice you're linking to the old wiki, that wiki has been in a read-only state for several months. Here are the links to that page on the new wiki: {new_url}")


    for attachment in message.attachments:
        if attachment.filename == "SMAPI-latest.txt" or attachment.filename == "SMAPI-crash.txt":
            r = requests.get(attachment.url)
            log = urllib.parse.quote(r.text)
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }

            s = requests.post('https://smapi.io/log/', data="input={0}".format(log), headers=headers)
            logurl = s.text.split('</strong> <code>')[1].split('</code>')[0]
            await message.channel.send("Log found, uploaded to: " + logurl)

    # Check if someone is trying to use a custom command
    if message.content != "" and message.content[0] == CMD_PREFIX:
        raw_command = message.content[1:]
        command = raw_command.split(" ")[0].lower()
        if custom.is_allowed(command, message.channel.id):
            # Check if they're using a user-defined command
            response = custom.parse_response(command)
            await message.channel.send(response)

client.run(DISCORD_KEY)
