"""Truth or Dare game plugin for MusicLyrics bot."""

import random
from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from MusicLyrics.bot import bot

TRUTHS = [
    "তোমার সবচেয়ে বড় ভয় কি? / What is your biggest fear?",
    "তুমি কি কখনো কারো কাছে মিথ্যা বলেছো? / Have you ever lied to someone close?",
    "তোমার সবচেয়ে লজ্জাজনক মুহূর্ত কি ছিলো? / What was your most embarrassing moment?",
    "তুমি কি কখনো কারো ওপর ক্রাশ খেয়েছো? / Have you ever had a crush on someone here?",
    "তোমার ফোনে শেষ কাকে কল করেছো? / Who was the last person you called?",
    "তুমি কি কখনো কান্না করেছো সিনেমা দেখে? / Have you ever cried watching a movie?",
    "তোমার সবচেয়ে বাজে অভ্যাস কি? / What's your worst habit?",
    "তুমি কি কখনো পরীক্ষায় নকল করেছো? / Have you ever cheated in an exam?",
    "What's the most childish thing you still do?",
    "If you could be invisible for a day, what would you do?",
    "তোমার সবচেয়ে প্রিয় মানুষ কে? / Who is your favorite person?",
    "What's a secret you've never told anyone?",
    "তুমি কি কখনো কারো ডায়েরি পড়েছো? / Have you ever read someone's diary?",
    "What's the worst gift you've ever received?",
    "তোমার জীবনে সবচেয়ে বোকামি কি করেছো? / What's the dumbest thing you've done?",
    "Have you ever pretended to be sick to skip school/work?",
    "তুমি কি কখনো কারো সাথে ghosting করেছো? / Have you ever ghosted someone?",
    "What's your most unpopular opinion?",
    "তোমার ফোনে সবচেয়ে বেশি কোন অ্যাপ ব্যবহার করো? / What app do you use most?",
    "Have you ever stalked someone on social media?",
    "তুমি কি কখনো কারো জিনিস চুরি করেছো? / Have you ever stolen something?",
    "What's the worst lie you've ever told your parents?",
    "তোমার প্রথম crush কে ছিলো? / Who was your first crush?",
    "What is something you're glad your parents don't know about?",
    "Have you ever been rejected? What happened?",
    "তোমার সবচেয়ে খারাপ স্বপ্ন কি ছিলো? / What was your worst nightmare?",
    "What's the most embarrassing thing on your phone?",
    "তুমি কি কখনো কাউকে block করেছো? কেন? / Have you ever blocked someone? Why?",
    "If you had to delete one app forever, which would it be?",
    "What's the longest you've gone without showering?",
    "তুমি কি কখনো প্রেমে পড়েছো? / Have you ever been in love?",
    "What is the most trouble you've ever been in?",
    "তোমার সবচেয়ে বড় আফসোস কি? / What's your biggest regret?",
    "Have you ever lied to your best friend?",
    "তুমি কি কখনো কারো সাথে ঝগড়া করে পরে লজ্জা পেয়েছো?",
    "What's a movie that made you cry like a baby?",
    "তোমার সবচেয়ে পছন্দের গান কি? কেন? / What's your fav song and why?",
    "Have you ever faked a laugh?",
    "What's the weirdest dream you've ever had?",
    "তুমি কি কখনো কাউকে ভুলে যেতে পারোনি? / Is there someone you can't forget?",
    "What's your biggest insecurity?",
    "তুমি কি কখনো কারো ওপর রাগ করে পরে ভুল বুঝেছো?",
    "If you could change one thing about yourself, what would it be?",
    "What's the most cringe thing you've done on social media?",
    "তুমি কি কখনো কারো ফোন চেক করেছো? / Have you ever checked someone's phone?",
    "What's the biggest misconception people have about you?",
    "তোমার জীবনের সবচেয়ে ভালো দিন কোনটা ছিলো?",
    "Have you ever had a paranormal experience?",
    "What's something you pretend to hate but secretly love?",
    "তুমি কি কখনো মনে মনে কাউকে গালি দিয়েছো? 😅",
]

DARES = [
    "পরবর্তী ৫ মিনিট সবকিছু ইংরেজিতে বলো! / Speak only English for 5 min!",
    "তোমার গ্যালারির শেষ ছবি পোস্ট করো! / Post the last photo from your gallery!",
    "গ্রুপে তোমার সবচেয়ে বাজে সেলফি পাঠাও! / Send your worst selfie!",
    "পরবর্তী ব্যক্তিকে 'I love you' বলো! / Say 'I love you' to the next person!",
    "তোমার ফোনের ব্যাটারি পার্সেন্টেজ বলো! / Share your battery percentage!",
    "একটা গান গেয়ে ভয়েস মেসেজ পাঠাও! / Send a voice message singing a song!",
    "তোমার স্ক্রিন টাইম শেয়ার করো! / Share your screen time!",
    "Change your profile picture to a potato for 1 hour!",
    "Send a voice note saying 'I am a beautiful butterfly' 🦋",
    "Type with your eyes closed for the next 2 messages!",
    "তোমার ওয়ালপেপার শেয়ার করো! / Share your wallpaper!",
    "Do 10 pushups and send a video! 💪",
    "গ্রুপের এডমিনকে একটা compliment দাও! / Compliment the group admin!",
    "পরবর্তী ৩ মিনিট শুধু emoji দিয়ে কথা বলো!",
    "Send a message to the 5th person in your contacts saying 'Hi!'",
    "তোমার ফোনে শেষ ৩টা সার্চ হিস্টোরি বলো!",
    "Do your best impression of a cat! 🐱 (voice msg)",
    "Write a short poem about the person above you!",
    "Put your status as 'I lost a dare' for 30 minutes!",
    "তোমার প্রিয় ইমোজি ১০ বার পাঠাও!",
    "Record yourself doing a funny dance! 💃",
    "Speak in a British accent for the next 5 minutes!",
    "তোমার crush-এর প্রথম অক্ষর বলো! / Tell the first letter of your crush's name!",
    "Send a voice note laughing for 15 seconds straight! 😂",
    "Make up a rap about this group!",
    "Text your best friend 'I see dead people' with no context!",
    "তোমার ফোনে সবচেয়ে পুরোনো ফটো শেয়ার করো!",
    "Hold your breath for 20 seconds and record it!",
    "Write a love letter to pizza! 🍕",
    "Send the 3rd photo in your gallery, no cheating!",
    "গ্রুপের প্রত্যেককে একটা করে compliment দাও!",
    "Sing the national anthem in a voice note! 🎵",
    "Act like a robot for the next 3 messages! 🤖",
    "Tell us your most used emoji and why!",
    "তোমার নামের মানে কি সেটা বলো!",
    "Send a selfie right now, no fixing your hair!",
    "Describe yourself in 3 emojis only!",
    "তোমার সবচেয়ে funny ছবি পাঠাও!",
    "Call the last person who texted you and say 'quack quack' 🦆",
    "Write your name with your non-dominant hand and send a photo!",
    "তোমার জীবনের motto কি বলো!",
    "Do 5 jumping jacks right now!",
    "Send a voice message in the highest pitch you can!",
    "Change your name to 'Dare Victim' for 1 hour!",
    "Tell us 3 things on your bucket list!",
    "পরবর্তী ব্যক্তির নাম দিয়ে একটা acrostic poem লেখো!",
    "Imitate your favorite celebrity in a voice note!",
    "Send a message using only the predictive text on your keyboard!",
    "তোমার সবচেয়ে গুরুত্বপূর্ণ possession কি?",
    "Dance to the first song that comes on shuffle and record it!",
]

BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🤔 Truth", callback_data="tod_truth"),
        InlineKeyboardButton("😈 Dare", callback_data="tod_dare"),
    ],
    [InlineKeyboardButton("🔄 Spin Again", callback_data="tod_spin")],
])


@bot.on_message(filters.command(["truth"]))
async def truth_cmd(_, message: Message):
    q = random.choice(TRUTHS)
    await message.reply(
        f"🤔 **Truth / সত্যি বলো!**\n\n{q}",
        reply_markup=BUTTONS,
    )


@bot.on_message(filters.command(["dare"]))
async def dare_cmd(_, message: Message):
    d = random.choice(DARES)
    await message.reply(
        f"😈 **Dare / চ্যালেঞ্জ!**\n\n{d}",
        reply_markup=BUTTONS,
    )


@bot.on_callback_query(filters.regex(r"^tod_truth$"))
async def tod_truth_cb(_, cq: CallbackQuery):
    q = random.choice(TRUTHS)
    await cq.message.edit_text(
        f"🤔 **Truth / সত্যি বলো!**\n\n"
        f"🎯 {cq.from_user.mention} এর জন্য:\n\n{q}",
        reply_markup=BUTTONS,
    )
    await cq.answer()


@bot.on_callback_query(filters.regex(r"^tod_dare$"))
async def tod_dare_cb(_, cq: CallbackQuery):
    d = random.choice(DARES)
    await cq.message.edit_text(
        f"😈 **Dare / চ্যালেঞ্জ!**\n\n"
        f"🎯 {cq.from_user.mention} এর জন্য:\n\n{d}",
        reply_markup=BUTTONS,
    )
    await cq.answer()


@bot.on_callback_query(filters.regex(r"^tod_spin$"))
async def tod_spin_cb(_, cq: CallbackQuery):
    is_truth = random.choice([True, False])
    if is_truth:
        q = random.choice(TRUTHS)
        await cq.message.edit_text(
            f"🎰 **Spin Result: Truth! / সত্যি!**\n\n"
            f"🎯 {cq.from_user.mention} এর জন্য:\n\n{q}",
            reply_markup=BUTTONS,
        )
    else:
        d = random.choice(DARES)
        await cq.message.edit_text(
            f"🎰 **Spin Result: Dare! / চ্যালেঞ্জ!**\n\n"
            f"🎯 {cq.from_user.mention} এর জন্য:\n\n{d}",
            reply_markup=BUTTONS,
        )
    await cq.answer()
