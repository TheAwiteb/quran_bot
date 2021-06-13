#!./venv/bin/python3.8
import telebot
from telebot import types
import urllib.request
import time
import json
import os
import logging

logging.basicConfig(filename="bot.log", format="%(asctime)s - %(levelname)s - %(message)s",
                        datefmt="%Y/%m/%d %I:%M:%S %p", level=0)

SUDO_ID = int() # your id 
TOKEN = ""
BOT = telebot.TeleBot(TOKEN)
bot_name = BOT.get_me().first_name
bot_username = BOT.get_me().username
bot_url = "https://t.me/"+bot_username
error_img = "https://image.freepik.com/free-vector/error-neon-signs-style-text_118419-3023.jpg"
PAGES_URL = "http://mp3quran.net/api/quran_pages_arabic/"
with open('./messages.json', 'r') as j:
    messages = json.load(j)


def get_page(page_number, is_start):
    page_number = page_number if page_number > 1 and page_number < 604 else 604 if page_number < 1 else 1
    page_number = f"{'00' if page_number < 10 else '0' if page_number < 100 else ''}{page_number}"
    page_url = None if is_start else f"{PAGES_URL}{page_number}.png"
    return int(page_number), page_url

def send_page(user_id, first_name, chat_id, 
                message_id, page_number, is_start=False, 
                    send=False, with_markup=True):
    page_number, page_url= get_page(page_number, is_start)
    markup = get_markup(user_id, first_name, page_number,
                            is_start, with_markup)
    logging.info(f"send_page:is_start, with_markup, send = {is_start, with_markup, send}")
    if is_start or send:
        BOT.send_photo(chat_id, page_url if page_url else open('./img/start_img.jpg', 'rb'),
                        reply_to_message_id=message_id,reply_markup=markup if with_markup else None,
                            caption=messages.get('start') if is_start else None)
    else:
        urllib.request.urlretrieve(page_url, f"{page_number}.png")
        with open(f"{page_number}.png", 'rb') as page:
            BOT.edit_message_media(types.InputMediaPhoto(page), chat_id, message_id, 
                                        reply_markup=markup if with_markup else None)
        os.remove(f"{page_number}.png")

def get_markup(user_id, first_name, page_number,
                    is_start, with_markup):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton
    next_button = button(text="▶️الصفحة التالية", callback_data=f"{page_number + 1} {user_id} {first_name}")\
                    if with_markup else None
    back_button = button(text="◀️الصفحة السابقة", callback_data=f"{page_number - 1} {user_id} {first_name}")\
                    if with_markup else None
    start_button = button(text="فتح المصحف 🕋", callback_data=f"{1} {user_id} {first_name}")\
                    if with_markup else None
    buttons_list = [start_button] if is_start else [back_button, next_button]\
                    if with_markup else []
    markup.add(*buttons_list)
    return markup

def open_page(text, user_id=None, first_name=None,
                chat_id=None,message_id=None,
                    with_markup=None, send=True):
    s_text = text.split()
    user_info = [user_id, first_name, chat_id, message_id]
    if len(s_text) > 2 and s_text[2].isnumeric():
        page_number = int(s_text[2])
        if page_number > 0 and page_number < 604:
            if send:
                send_page(*user_info,
                            page_number, send=True, with_markup=with_markup)
            else:
                return get_page(page_number,is_start=False)
        else:
            raise Exception("عدد صفحات القران 604")
    else:
        raise Exception("الرجاء ادخال رقم الصفحة مثال:\n%s 10" % (' '.join(s_text[:2])))

def get_info(ob):
    if ob.__class__ == types.Message:
        message_id = ob.id
        chat_id = ob.chat.id
    else:
        try:
            message_id = ob.message.id
            chat_id = ob.message.chat.id
        except Exception:
            message_id = chat_id = None
    user_id = ob.from_user.id
    first_name = ob.from_user.first_name
    return {"user_id":user_id, "first_name":first_name, 
                "chat_id":chat_id, "message_id":message_id}


@BOT.message_handler(commands=['start', 'help'])
def command_handler(message):
    text = str(message.text)
    user_info = get_info(message)
    if text.startswith(('/start')):
        send_page(*user_info.values(),
                    page_number=1, is_start=True)
    elif text.startswith('/help'):
        BOT.reply_to(message, messages.get('help').format(bot_username), 
                        parse_mode="Markdown", disable_web_page_preview=True)

@BOT.message_handler(func=lambda msg:True, content_types=['text'])
def message_handler(message):
    text = str(message.text)
    user_info = get_info(message)
    if text.startswith('فتح القران'):
        send_page(*user_info.values(),
                    page_number=1, send=True)
    elif text.startswith(('فتح صفحه', 'جلب صفحه','فتح صفحة', 'جلب صفحة')):
        try:
            open_page(text, *user_info.values(), with_markup= not text.startswith(('جلب صفحه', 'جلب صفحة')))
        except Exception as err:
            BOT.reply_to(message, err)
    elif text in ['سورس', 'السورس']:
        BOT.reply_to(message, "https://github.com/Awiteb/quran_bot")

@BOT.callback_query_handler(func=lambda call:True)
def query_handler(call):
    user_info = get_info(call)
    page_number, user_id, first_name = call.data.split(maxsplit=3)
    requester = call.from_user.id
    logging.info(f"query_handler:user_id == requester ={int(user_id) == requester}")
    if int(user_id) == requester:
        send_page(*user_info.values(), 
                    int(page_number), is_start=False)
    else:
        BOT.answer_callback_query(call.id, f"هذا المصحف خاص بـ {first_name}")

@BOT.inline_handler(lambda query: True)
def inline_handler(inline_query):
    text = inline_query.query
    true_text = False
    page_number = None
    if text == '':
        msg = "الاوامر:\nجلب صفحة"
    elif text.startswith(('جلب صفحه', 'جلب صفحة')):
        try:
            page_number, msg = open_page(text,send=False)
            true_text = True
        except Exception as err:
            msg = str(err)
    else:
        msg = "الاوامر:\nجلب صفحة"
    logging.info(f"inline_handler:true_text={true_text}")
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(bot_name, bot_url))
    if true_text:
        r = types.InlineQueryResultPhoto('1',photo_url=msg, thumb_url=msg, photo_width=20, photo_height=20,
                                            caption=f"صفحة {page_number}", reply_markup=markup)
    else:
        r = types.InlineQueryResultArticle('1', title="ERROR", input_message_content=types.InputTextMessageContent("ERROR"),
                                            description=msg, thumb_url=error_img, thumb_height=20, thumb_width=20)
    BOT.answer_inline_query(inline_query.id, [r], cache_time=1)
while True:
    print(f"Start\t{bot_name} @{bot_username}\n{bot_url}")
    logging.info(f"Start @{bot_username}")
    try:
        BOT.polling(none_stop=True, interval=0, timeout=0)
    except Exception as err:
        logging.error(str(err))
        BOT.send_document(SUDO_ID, open('bot.log', 'rb'), caption=str(err))
        time.sleep(10)