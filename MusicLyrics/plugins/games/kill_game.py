"""Kill game plugin for MusicLyrics bot."""

import random
from pyrogram import filters
from pyrogram.types import Message

from MusicLyrics.bot import bot

KILL_MESSAGES = [
    "{attacker} {victim}-কে একটা রকেট লাঞ্চার দিয়ে উড়িয়ে দিলো! 🚀💥",
    "{attacker} slapped {victim} with a mass-produced mass-destruction weapon! 💣",
    "{attacker} threw {victim} into a volcano! 🌋",
    "{attacker} fed {victim} to the sharks! 🦈",
    "{attacker} pushed {victim} off a cliff! 🏔️",
    "{attacker} {victim}-কে একটা বিশাল মাছ দিয়ে থাপ্পড় মারলো! 🐟👋",
    "{attacker} ran over {victim} with a mass destruction tractor! 🚜",
    "{attacker} dropped an anvil on {victim}'s head! 🔨",
    "{attacker} sent {victim} to the shadow realm! 🌑",
    "{attacker} yeeted {victim} into the sun! ☀️",
    "{attacker} {victim}-কে পুকুরে ডুবিয়ে দিলো! 🏊",
    "{attacker} electrocuted {victim} with a toaster in the bathtub! ⚡🛁",
    "{attacker} launched {victim} from a trebuchet! 🏰",
    "{attacker} fed {victim} a poisoned biryani! 🍛☠️",
    "{attacker} turned {victim} into a frog with dark magic! 🐸✨",
    "{attacker} {victim}-কে স্পেসে পাঠিয়ে দিলো বিনা স্যুটে! 🚀🌌",
    "{attacker} dropped {victim} from an airplane without a parachute! ✈️",
    "{attacker} crushed {victim} with a giant piano! 🎹",
    "{attacker} tickled {victim} to death! 🤣💀",
    "{attacker} eliminated {victim} with a rubber chicken! 🐔",
    "{attacker} {victim}-কে একটা বিশাল কেক দিয়ে চাপা দিলো! 🎂",
    "{attacker} challenged {victim} to a dance-off and won! 💃🕺☠️",
    "{attacker} used the Infinity Gauntlet on {victim}! 🧤✨",
    "{attacker} sent {victim} to the gulag! ⚔️",
    "{attacker} planted a whoopee cushion that exploded under {victim}! 💨💥",
    "{attacker} {victim}-কে চাঁদে পাঠিয়ে দিলো! 🌙",
    "{attacker} hit {victim} with a blue shell! 🐚💙",
    "{attacker} dropped the ban hammer on {victim}! 🔨⚡",
    "{attacker} finished {victim} with a Hadouken! 🔥👊",
    "{attacker} used {victim} as target practice for a potato cannon! 🥔💥",
    "{attacker} {victim}-কে একটা পচা ডিম ছুড়ে মারলো! 🥚🤢",
    "{attacker} summoned a dragon to roast {victim}! 🐉🔥",
    "{attacker} replaced {victim}'s oxygen with helium permanently! 🎈",
    "{attacker} trapped {victim} in an infinite loop! ♾️💻",
    "{attacker} deleted {victim} from the matrix! 🖥️❌",
    "{attacker} {victim}-কে একটা ব্ল্যাক হোলে ফেলে দিলো! 🕳️",
    "{attacker} threw {victim} into a pit of LEGO bricks! 🧱😱",
    "{attacker} forced {victim} to listen to baby shark on loop! 🦈🎵",
    "{attacker} unleashed 1000 angry cats on {victim}! 🐱🐱🐱",
    "{attacker} used Ctrl+Alt+Delete on {victim}! ⌨️💀",
]


@bot.on_message(filters.command(["kill"]))
async def kill_cmd(_, message: Message):
    victim = None

    if message.reply_to_message:
        victim = message.reply_to_message.from_user
    elif message.entities:
        for ent in message.entities:
            if ent.type.value == "mention":
                username = message.text[ent.offset + 1 : ent.offset + ent.length]
                try:
                    victim = await bot.get_users(username)
                except Exception:
                    pass
                break

    if not victim:
        await message.reply(
            "❌ **কাউকে মেনশন করুন বা রিপ্লাই দিন!**\n"
            "Mention someone to kill them (in a fun way)!\n\n"
            "Usage: `/kill @username` or reply to someone with `/kill`"
        )
        return

    if victim.id == message.from_user.id:
        await message.reply("😂 নিজেকে মারবে? আত্মঘাতী হওয়া ভালো না!\nYou can't kill yourself!")
        return

    attacker = message.from_user.mention
    victim_name = victim.mention

    msg_template = random.choice(KILL_MESSAGES)
    kill_text = msg_template.format(attacker=attacker, victim=victim_name)

    await message.reply(f"⚔️ **Kill Game!**\n\n{kill_text}")
