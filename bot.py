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


@bot.message_handler(func=lambda message: True, content_types=['text'])
def process_msg(message):
    chat_id = str(message.chat.id)
    if message.reply_to_message is not None:
        reply_id = str(message.reply_to_message.message_id)
        if reply_id in data[chat_id]['msgs'].keys():
            subject = data[chat_id]['msgs'][reply_id]
            words = message.text.split(maxsplit=1)
            try:
                bet = int(words[0])
            except ValueError:
                bot.reply_to(message, "Не могу разобрать значение")
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


def get_bets(chat_id, subject):
    bets = data[chat_id]['subjects'][subject].values()
    max_len = 0
    max_bet_len = 0
    for bet in bets:
        if len(bet['name']) > max_len:
            max_len = len(bet['name'])
        if len(str(bet['bet'])) > max_bet_len:
            max_bet_len = len(str(bet['bet']))
    result = "Предположения по поводу"
    header_len = max(len(result), len(subject))
    result += "\n" + subject + "\n"
    max_len = max(header_len - 3 - max_bet_len, max_len)
    result += "=" * (max_len + max_bet_len + 3) + "\n"
    for bet in bets:
        line = bet['name']
        line += " " * (max_len - len(line))
        line += " - "
        bet_s = str(bet['bet'])
        line += " " * (max_bet_len - len(bet_s)) + bet_s
        result += line + "\n"
    return "```\n" + result + "```"


bot.delete_webhook()
bot.polling(none_stop=True)
