"""Quiz game plugin for MusicLyrics bot."""

import asyncio
import random
import time

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)

from MusicLyrics.bot import bot
from MusicLyrics.mongo.games_db import save_game_score, get_leaderboard

# Each question: (question, [options], correct_index)
QUESTIONS = [
    ("What is the capital of France?", ["Berlin", "Madrid", "Paris", "Rome"], 2),
    ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Saturn"], 1),
    ("What is the chemical symbol for water?", ["H2O", "CO2", "NaCl", "O2"], 0),
    ("Who painted the Mona Lisa?", ["Van Gogh", "Picasso", "Da Vinci", "Monet"], 2),
    ("What is the largest ocean on Earth?", ["Atlantic", "Indian", "Arctic", "Pacific"], 3),
    ("How many continents are there?", ["5", "6", "7", "8"], 2),
    ("What is the speed of light?", ["300,000 km/s", "150,000 km/s", "500,000 km/s", "100,000 km/s"], 0),
    ("Which element has the chemical symbol 'Au'?", ["Silver", "Gold", "Iron", "Copper"], 1),
    ("What year did World War II end?", ["1943", "1944", "1945", "1946"], 2),
    ("Who wrote 'Romeo and Juliet'?", ["Dickens", "Shakespeare", "Austen", "Hemingway"], 1),
    ("What is the largest mammal?", ["Elephant", "Blue Whale", "Giraffe", "Hippo"], 1),
    ("Which country has the most population?", ["USA", "India", "China", "Indonesia"], 1),
    ("What is the boiling point of water in Celsius?", ["90", "100", "110", "120"], 1),
    ("Who discovered penicillin?", ["Einstein", "Fleming", "Newton", "Curie"], 1),
    ("What is the capital of Japan?", ["Osaka", "Kyoto", "Tokyo", "Hiroshima"], 2),
    ("Which gas do plants absorb?", ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"], 2),
    ("What is the smallest planet in our solar system?", ["Mars", "Venus", "Mercury", "Pluto"], 2),
    ("How many bones does an adult human have?", ["186", "206", "216", "256"], 1),
    ("What is the currency of UK?", ["Euro", "Dollar", "Pound", "Franc"], 2),
    ("Who invented the telephone?", ["Edison", "Bell", "Tesla", "Marconi"], 1),
    ("What is the tallest mountain in the world?", ["K2", "Kangchenjunga", "Everest", "Lhotse"], 2),
    ("Which planet has the most moons?", ["Jupiter", "Saturn", "Uranus", "Neptune"], 1),
    ("What is the hardest natural substance?", ["Gold", "Iron", "Diamond", "Quartz"], 2),
    ("What is the national flower of Japan?", ["Rose", "Tulip", "Cherry Blossom", "Lily"], 2),
    ("How many players are on a soccer team?", ["9", "10", "11", "12"], 2),
    ("What is the capital of Australia?", ["Sydney", "Melbourne", "Canberra", "Perth"], 2),
    ("Who developed the theory of relativity?", ["Newton", "Einstein", "Hawking", "Bohr"], 1),
    ("What is the largest desert in the world?", ["Sahara", "Gobi", "Antarctic", "Arabian"], 2),
    ("Which blood type is the universal donor?", ["A", "B", "AB", "O"], 3),
    ("What is the chemical symbol for iron?", ["Ir", "Fe", "In", "I"], 1),
    ("Who is the founder of Microsoft?", ["Steve Jobs", "Bill Gates", "Elon Musk", "Jeff Bezos"], 1),
    ("What is the longest river in the world?", ["Amazon", "Nile", "Yangtze", "Mississippi"], 1),
    ("Which country invented pizza?", ["France", "USA", "Italy", "Spain"], 2),
    ("What is the capital of Bangladesh?", ["Chittagong", "Dhaka", "Sylhet", "Rajshahi"], 1),
    ("How many letters in the English alphabet?", ["24", "25", "26", "27"], 2),
    ("What is the powerhouse of the cell?", ["Nucleus", "Ribosome", "Mitochondria", "Golgi Body"], 2),
    ("Which ocean is the smallest?", ["Pacific", "Indian", "Atlantic", "Arctic"], 3),
    ("What year was the first iPhone released?", ["2005", "2006", "2007", "2008"], 2),
    ("Who wrote 'Harry Potter'?", ["Tolkien", "J.K. Rowling", "C.S. Lewis", "Roald Dahl"], 1),
    ("What is the largest organ of the human body?", ["Liver", "Brain", "Skin", "Heart"], 2),
    ("What is the capital of Canada?", ["Toronto", "Vancouver", "Montreal", "Ottawa"], 3),
    ("Which animal is known as the King of the Jungle?", ["Tiger", "Lion", "Elephant", "Bear"], 1),
    ("What is photosynthesis?", ["Animal eating", "Plant making food from light", "Rock formation", "Water cycle"], 1),
    ("Who was the first person to walk on the Moon?", ["Buzz Aldrin", "Neil Armstrong", "Yuri Gagarin", "John Glenn"], 1),
    ("What is the square root of 144?", ["10", "11", "12", "14"], 2),
    ("Which country gifted the Statue of Liberty to the USA?", ["UK", "Germany", "France", "Italy"], 2),
    ("What is the main ingredient in bread?", ["Rice", "Flour", "Sugar", "Salt"], 1),
    ("How many colors are in a rainbow?", ["5", "6", "7", "8"], 2),
    ("What is the fastest land animal?", ["Lion", "Horse", "Cheetah", "Leopard"], 2),
    ("Which vitamin does the sun provide?", ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D"], 3),
    ("What is the national animal of India?", ["Lion", "Tiger", "Elephant", "Peacock"], 1),
    ("Who founded Facebook?", ["Jack Dorsey", "Mark Zuckerberg", "Larry Page", "Elon Musk"], 1),
    ("What is the freezing point of water in Fahrenheit?", ["0", "32", "100", "212"], 1),
    ("Which planet is closest to the Sun?", ["Venus", "Earth", "Mercury", "Mars"], 2),
    ("What is the national language of Brazil?", ["Spanish", "Portuguese", "English", "French"], 1),
    ("How many teeth does an adult human have?", ["28", "30", "32", "34"], 2),
    ("What is the capital of Egypt?", ["Cairo", "Alexandria", "Luxor", "Giza"], 0),
    ("Which instrument has 88 keys?", ["Guitar", "Violin", "Piano", "Flute"], 2),
    ("What is the symbol for potassium?", ["Po", "Pt", "K", "Ka"], 2),
    ("Who is the CEO of Tesla?", ["Jeff Bezos", "Tim Cook", "Elon Musk", "Sundar Pichai"], 2),
    ("What is DNA short for?", ["Deoxyribonucleic acid", "Dioxin acid", "Dynamic nuclear acid", "None"], 0),
    ("Which sport uses a shuttlecock?", ["Tennis", "Badminton", "Cricket", "Golf"], 1),
    ("What is the SI unit of force?", ["Joule", "Watt", "Newton", "Pascal"], 2),
    ("Which country is the Eiffel Tower in?", ["Italy", "Spain", "France", "Germany"], 2),
    ("What does HTTP stand for?", ["HyperText Transfer Protocol", "High Tech Transfer Protocol", "HyperText Transmission Process", "None"], 0),
    ("How many weeks are in a year?", ["48", "50", "52", "54"], 2),
    ("What is the chemical formula for table salt?", ["NaOH", "NaCl", "KCl", "HCl"], 1),
    ("Which is the largest country by area?", ["China", "USA", "Canada", "Russia"], 3),
    ("What is the national sport of Japan?", ["Karate", "Judo", "Sumo", "Baseball"], 2),
    ("Who invented the light bulb?", ["Tesla", "Edison", "Bell", "Franklin"], 1),
    ("What is the capital of Germany?", ["Munich", "Frankfurt", "Berlin", "Hamburg"], 2),
    ("Which animal can change its color?", ["Frog", "Chameleon", "Snake", "Lizard"], 1),
    ("What is the value of Pi (approx)?", ["2.14", "3.14", "4.14", "1.14"], 1),
    ("Which country hosted the 2020 Olympics?", ["China", "Brazil", "Japan", "UK"], 2),
    ("What is the main gas in Earth's atmosphere?", ["Oxygen", "Carbon Dioxide", "Nitrogen", "Hydrogen"], 2),
    ("Who painted 'Starry Night'?", ["Monet", "Picasso", "Van Gogh", "Da Vinci"], 2),
    ("What is the capital of South Korea?", ["Busan", "Seoul", "Incheon", "Daegu"], 1),
    ("How many sides does a hexagon have?", ["5", "6", "7", "8"], 1),
    ("What is the largest bird in the world?", ["Eagle", "Ostrich", "Albatross", "Condor"], 1),
    ("Which metal is liquid at room temperature?", ["Lead", "Mercury", "Iron", "Gold"], 1),
    ("What is the capital of Russia?", ["St. Petersburg", "Moscow", "Kiev", "Minsk"], 1),
    ("Who discovered gravity?", ["Einstein", "Galileo", "Newton", "Hawking"], 2),
    ("What is the currency of Japan?", ["Won", "Yuan", "Yen", "Ringgit"], 2),
    ("Which is the largest freshwater lake?", ["Victoria", "Superior", "Baikal", "Huron"], 1),
    ("What does RAM stand for?", ["Random Access Memory", "Read Access Memory", "Rapid Access Mode", "None"], 0),
    ("Which fruit is known as the King of Fruits?", ["Apple", "Mango", "Durian", "Banana"], 2),
    ("What is the national anthem of Bangladesh?", ["Joy Bangla", "Amar Sonar Bangla", "Ode to Joy", "None"], 1),
    ("Which vitamin is good for eyesight?", ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D"], 0),
    ("What is the largest planet in our solar system?", ["Saturn", "Neptune", "Jupiter", "Uranus"], 2),
    ("Who invented the World Wide Web?", ["Bill Gates", "Steve Jobs", "Tim Berners-Lee", "Vint Cerf"], 2),
    ("What is the capital of Turkey?", ["Istanbul", "Ankara", "Izmir", "Antalya"], 1),
    ("Which language has the most native speakers?", ["English", "Spanish", "Hindi", "Mandarin"], 3),
    ("What is the pH of pure water?", ["5", "6", "7", "8"], 2),
    ("How many strings does a standard guitar have?", ["4", "5", "6", "8"], 2),
    ("What is the capital of Italy?", ["Milan", "Venice", "Rome", "Naples"], 2),
    ("Which element is the most abundant in Earth's crust?", ["Iron", "Silicon", "Oxygen", "Aluminum"], 2),
    ("What year did the Titanic sink?", ["1910", "1911", "1912", "1913"], 2),
    ("Who wrote 'The Republic'?", ["Aristotle", "Socrates", "Plato", "Homer"], 2),
    ("What is the speed of sound in air (approx)?", ["243 m/s", "343 m/s", "443 m/s", "543 m/s"], 1),
    ("Which country has the largest coastline?", ["Australia", "Indonesia", "Russia", "Canada"], 3),
    ("What is the smallest bone in the human body?", ["Femur", "Stapes", "Radius", "Patella"], 1),
]

# Active quizzes: key = f"{chat_id}_{msg_id}"
active_quizzes = {}

OPTION_LABELS = ["🅰", "🅱", "🅲", "🅳"]


def make_quiz_markup(options, quiz_id):
    buttons = []
    for i, opt in enumerate(options):
        buttons.append(
            [InlineKeyboardButton(
                f"{OPTION_LABELS[i]} {opt}",
                callback_data=f"quiz_{quiz_id}_{i}",
            )]
        )
    return InlineKeyboardMarkup(buttons)


@bot.on_message(filters.command(["quiz"]))
async def quiz_start(_, message: Message):
    q_data = random.choice(QUESTIONS)
    question, options, correct = q_data

    sent = await message.reply(
        f"🧠 **Quiz Time! / কুইজ!**\n\n"
        f"📝 {question}\n\n"
        f"⏰ ৩০ সেকেন্ড আছে! / 30 seconds to answer!",
        reply_markup=make_quiz_markup(options, "temp"),
    )

    quiz_id = f"{sent.chat.id}_{sent.id}"
    active_quizzes[quiz_id] = {
        "question": question,
        "options": options,
        "correct": correct,
        "answered": set(),
        "end_time": time.time() + 30,
        "chat_id": sent.chat.id,
        "msg_id": sent.id,
    }

    await sent.edit_reply_markup(make_quiz_markup(options, quiz_id))

    # Auto-end timer
    asyncio.create_task(_quiz_timeout(quiz_id, 30))


async def _quiz_timeout(quiz_id, delay):
    await asyncio.sleep(delay)
    quiz = active_quizzes.pop(quiz_id, None)
    if quiz:
        correct_text = quiz["options"][quiz["correct"]]
        try:
            await bot.edit_message_text(
                quiz["chat_id"],
                quiz["msg_id"],
                f"⏰ **সময় শেষ! / Time's up!**\n\n"
                f"📝 {quiz['question']}\n\n"
                f"✅ সঠিক উত্তর / Correct answer: **{correct_text}**",
            )
        except Exception:
            pass


@bot.on_callback_query(filters.regex(r"^quiz_-?\d+_\d+_\d$"))
async def quiz_answer(_, cq: CallbackQuery):
    # callback_data format: quiz_{chat_id}_{msg_id}_{chosen}
    # chat_id can be negative for groups (e.g. -1001234567890)
    data = cq.data
    # Extract chosen (last character after final _)
    last_underscore = data.rfind("_")
    chosen = int(data[last_underscore + 1:])
    # Extract quiz_id (everything between "quiz_" and the last _)
    quiz_id = data[5:last_underscore]

    quiz = active_quizzes.get(quiz_id)
    if not quiz:
        await cq.answer("কুইজ শেষ হয়ে গেছে! / Quiz ended!", show_alert=True)
        return

    if cq.from_user.id in quiz["answered"]:
        await cq.answer("তুমি আগেই উত্তর দিয়েছো! / Already answered!", show_alert=True)
        return

    quiz["answered"].add(cq.from_user.id)

    if chosen == quiz["correct"]:
        active_quizzes.pop(quiz_id, None)
        correct_text = quiz["options"][quiz["correct"]]
        await save_game_score(cq.from_user.id, "quiz", 1, quiz["chat_id"])
        await cq.message.edit_text(
            f"🎉 **সঠিক! / Correct!**\n\n"
            f"📝 {quiz['question']}\n\n"
            f"✅ উত্তর / Answer: **{correct_text}**\n\n"
            f"🏆 বিজয়ী / Winner: {cq.from_user.mention}\n\n"
            f"আবার খেলতে /quiz দাও!"
        )
        await cq.answer("✅ সঠিক! Correct!", show_alert=True)
    else:
        await cq.answer(
            f"❌ ভুল! Wrong! তোমার উত্তর: {quiz['options'][chosen]}",
            show_alert=True,
        )


@bot.on_message(filters.command(["quizboard"]))
async def quiz_leaderboard(_, message: Message):
    leaders = await get_leaderboard("quiz", 10)
    if not leaders:
        await message.reply(
            "📊 **কুইজ লিডারবোর্ড খালি!**\n"
            "No quiz scores yet! Start with /quiz"
        )
        return

    text = "🏆 **Quiz Leaderboard / কুইজ লিডারবোর্ড**\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, entry in enumerate(leaders):
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        try:
            user = await bot.get_users(entry["_id"])
            name = user.mention
        except Exception:
            name = f"User {entry['_id']}"
        text += f"{medal} {name} — **{entry['best_score']}** points\n"

    await message.reply(text)
