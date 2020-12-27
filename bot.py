import telebot
import config
import json

bot = telebot.TeleBot(config.api_token)

try:
    datafile = open(config.data_file, "r")
    data = json.load(datafile)
    datafile.close()
except FileNotFoundError:
    data = {}


def save_data():
    data_file = open(config.data_file, "w")
    json.dump(data, data_file, ensure_ascii=False)


@bot.message_handler(commands=["list_bets"])
def cmd_list_bets(message):
    admins = [x.user.id for x in bot.get_chat_administrators(message.chat.id)]
    if message.from_user.id not in admins:
        bot.reply_to(message, "Эта команда доступна только администраторам")
        return
    chat_id = str(message.chat.id)
    if chat_id not in data.keys():
        bot.reply_to(message, "В данном чате никто не гадает")
    if chat_id in data.keys():
        bot.reply_to(message, "\n".join(["Активные поводы:"] + list(data[chat_id]['subjects'])))


@bot.message_handler(commands=["print_bet"])
def cmd_print_bet(message):
    admins = [x.user.id for x in bot.get_chat_administrators(message.chat.id)]
    if message.from_user.id not in admins:
        bot.reply_to(message, "Эта команда доступна только администраторам")
        return
    words = message.text.split(maxsplit=1)
    if len(words) < 2:
        bot.reply_to(message, "Формат команды: print_bet <имя повода>")
        return
    subject = words[1]
    chat_id = str(message.chat.id)
    if chat_id not in data.keys() or subject not in data[chat_id]['subjects']:
        bot.reply_to(message, "Повод не найден")
        return
    data[chat_id]['msgs'][
        str(bot.reply_to(message, get_bets(chat_id, subject), parse_mode="MarkdownV2").message_id)
    ] = subject


@bot.message_handler(commands=["stop_bet"])
def cmd_stop_bet(message):
    admins = [x.user.id for x in bot.get_chat_administrators(message.chat.id)]
    if message.from_user.id not in admins:
        bot.reply_to(message, "Эта команда доступна только администраторам")
        return
    words = message.text.split(maxsplit=1)
    if len(words) < 2:
        bot.reply_to(message, "Формат команды: stop_bet <имя повода>")
        return
    subject = words[1]
    chat_id = str(message.chat.id)
    if chat_id not in data.keys() or subject not in data[chat_id]['subjects']:
        bot.reply_to(message, "Повод не найден")
        return
    del data[chat_id]['subjects'][subject]
    cleanup()
    save_data()
    bot.reply_to(message, "Повод удалён")


@bot.message_handler(commands=["result_bet"])
def cmd_result_bet(message):
    admins = [x.user.id for x in bot.get_chat_administrators(message.chat.id)]
    if message.from_user.id not in admins:
        bot.reply_to(message, "Эта команда доступна только администраторам")
        return
    words = message.text.split(maxsplit=1)
    real_result = None
    if len(words) == 2:
        words = words[1].split()
        if len(words) > 1:
            try:
                real_result = int(words[-1])
            except ValueError:
                pass
    if real_result is None:
        bot.reply_to(message, "Формат команды: result_bet <имя повода> <итог>")
        return
    subject = " ".join(words[:-1])
    chat_id = str(message.chat.id)
    if chat_id not in data.keys() or subject not in data[chat_id]['subjects']:
        bot.reply_to(message, "Повод не найден")
        return
    bot.reply_to(message, get_bets(chat_id, subject, real_result), parse_mode="MarkdownV2")
    del data[chat_id]['subjects'][subject]
    cleanup()
    save_data()


@bot.message_handler(commands=["start_bet"])
def cmd_start_bet(message):
    admins = [x.user.id for x in bot.get_chat_administrators(message.chat.id)]
    if message.from_user.id not in admins:
        bot.reply_to(message, "Начинать приём могут только администраторы")
        return
    words = message.text.split(maxsplit=1)
    if len(words) < 2:
        bot.reply_to(message, "Формат команды: start_bet <имя повода>")
        return
    subject = words[1]
    chat_id = str(message.chat.id)
    if chat_id not in data.keys():
        data[chat_id] = {'msgs': {}, 'subjects': {subject: {}}}
    else:
        data[chat_id]['subjects'][subject] = {}
    data[chat_id]['msgs'] = dict([x for x in data[chat_id]['msgs'].items() if x[1] != subject])
    data[chat_id]['msgs'][
        str(bot.reply_to(message, "Начат приём вариантов по поводу {}".format(subject)).message_id)
    ] = subject
    data[chat_id]['msgs'][
        str(bot.reply_to(message, get_bets(chat_id, subject), parse_mode="MarkdownV2").message_id)
    ] = subject
    save_data()


@bot.message_handler(commands=["help"])
def cmd_start_bet(message):
    bot.reply_to(message, """list_bets - Get a list of active bets
print_bet <subject> - Print current bets of specified subject
result_bet <subject> <result> - Print results and winners for specified bet, stop bet. 
stop_bet <subject> - Stop specified bet
start_bet <subject> - Start new bet
help - List of commands""")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def process_msg(message):
    chat_id = str(message.chat.id)
    if message.reply_to_message is not None:
        reply_id = str(message.reply_to_message.message_id)
        if chat_id in data.keys() and reply_id in data[chat_id]['msgs'].keys():
            subject = data[chat_id]['msgs'][reply_id]
            words = message.text.split(maxsplit=1)
            try:
                bet = int(words[0])
            except ValueError:
                bot.reply_to(message, "Не могу разобрать значение")
                return
            if bet >= config.max_bet or bet * -1 >= config.max_bet:
                bot.reply_to(message, "Простите, слишком большое число")
                return
            username = message.from_user.username
            if username is None:
                username = message.from_user.first_name
                if message.from_user.last_name is not None:
                    username += " {}".format(message.from_user.last_name)
            data[chat_id]['subjects'][subject][str(message.from_user.id)] = {'name': username, 'bet': bet}
            data[chat_id]['msgs'][
                str(bot.reply_to(message, get_bets(chat_id, subject), parse_mode="MarkdownV2").message_id)
            ] = subject
            save_data()


def result_line(name, val, max_len, max_bet_len):
    line = name
    line += " " * (max_len - len(line))
    line += " - "
    bet_s = str(val)
    line += " " * (max_bet_len - len(bet_s)) + bet_s
    return line + "\n"


def get_bets(chat_id, subject, real_result=None):
    bets = list(data[chat_id]['subjects'][subject].values())
    bets.sort(key=lambda a: a['bet'])
    max_len = 0
    max_bet_len = 0
    for bet in bets:
        if len(bet['name']) > max_len:
            max_len = len(bet['name'])
        bet_len = len(str(bet['bet']))
        if bet_len > max_bet_len:
            max_bet_len = bet_len
    if real_result is None:
        result = "Предположения по поводу"
    else:
        result = "Итоги по поводу"
    header_len = max(len(result), len(subject))
    result += "\n" + subject + "\n"
    max_len = max(header_len - 3 - max_bet_len, max_len)
    line_len = max_len + max_bet_len + 3
    result += "=" * line_len + "\n"
    real_printed = real_result is None
    real_finished = real_result is None
    winners = []
    for bet in bets:
        if (not real_printed) and bet['bet'] >= real_result:
            result += "-" * line_len + "\n"
            result += result_line("Результат", real_result, max_len, max_bet_len)
            real_printed = True
        if bet['bet'] == real_result:
            winners.append(bet['name'])
        if (not real_finished) and bet['bet'] > real_result:
            result += "-" * line_len + "\n"
            real_finished = True
        result += result_line(bet['name'], bet['bet'], max_len, max_bet_len)
    if not real_finished:
        result += "-" * line_len + "\n"
    if not real_printed:
        result += result_line("Результат", real_result, max_len, max_bet_len)
        result += "-" * line_len + "\n"
    if real_result is not None:
        if len(winners) > 0:
            result += "\n\nИ наши победители: {}".format(", ".join(winners))
        else:
            result += "\n\nНикто не угадал"
    return "```\n" + result + "```"


def cleanup():
    for chat_id in data:
        data[chat_id]["msgs"] = dict(
            [x for x in data[chat_id]["msgs"].items() if x[1] in data[chat_id]["subjects"].keys()]
        )


bot.delete_webhook()
bot.polling(none_stop=True)
