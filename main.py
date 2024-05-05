from telebot import TeleBot
from telebot.types import Message, BotCommand
from config import IEM_TOKEN_INFO, BOT_TOKEN, ADMIN_ID, SYSTEM_PROMPT
from validations import (is_user_amount_limit, is_tts_symbol_limit_per_person, is_tts_symbol_limit_per_message,
                         is_stt_blocks_limit_per_person, is_stt_blocks_limit_per_message,
                         is_gpt_tokens_limit_per_person, is_gpt_tokens_limit_per_message)
from database import (create_table_prompts, create_table_limits, user_in_table, insert_row_into_limits,
                      update_tts_tokens_in_limits, insert_row_into_prompts, update_stt_blocks_in_limits,
                      update_gpt_tokens_in_limits, get_user_prompts)
from speechkit import text_to_speech, speech_to_text
from gpt import gpt, check_and_create_IEM_token
import logging
from math import ceil


bot = TeleBot(BOT_TOKEN)


@bot.message_handler(commands=['start'])
def start(message: Message):
    user_id = message.from_user.id
    # Проверяем, достигли ли мы лимита пользователей
    if not is_user_amount_limit(user_id):
        bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                   'К сожалению, вы не сможете им воспользоваться.'))
        logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
        return
    # Проверяем, есть ли пользователь в нашей таблице лимитов токенов, если нет - добавляем.
    if not user_in_table(user_id):
        insert_row_into_limits(user_id)
        logging.info(f'New user_id {user_id} just connected')

    bot.send_message(user_id, 'Здравствуйте, это бот мультипомощник.')


@bot.message_handler(commands=['help'])
def helping(message: Message):
    user_id = message.from_user.id

    bot.send_message(user_id, ('Бот взаимодействует с вами в том же типе, в котором вы взаимодействуете с ним.'
                               'Если вы пишите текст - бот отвечает вам текстом, на голосовое сообщение он отвечает'
                               'голосовым сообщением.'
                               'Также данный бот имеет пару дополнительных команд: /tts - озвучивает ваше текстовое'
                               'сообщение; /stt - расшифровывает голосовое сообщение, которое вы введете.'))


@bot.message_handler(commands=['debug'])
def debugging(message: Message):
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        with open('logging.txt', 'rb') as file:
            try:
                bot.send_document(user_id, file)
            except Exception as File_is_empty:
                bot.send_message(user_id, 'Файл с логами пустой')

        logging.info(f'Admin got access to the logging file')

    logging.info(f'Someone tried to get access to the logging file')


@bot.message_handler(commands=['tts'])
def tts_handler(message: Message):
    user_id = message.from_user.id

    if not is_user_amount_limit(user_id):
        bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                   'К сожалению, вы не сможете им воспользоваться.'))
        logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
        return
    # Если пользователь каким-либо образом добрался до команд, предварительно не занеся себе в БД
    if not user_in_table(user_id):
        bot.send_message(user_id, 'Нажмите для начала /start, для регистрации.')
        logging.warning(f'User_id {user_id} got access to commands without registration')
        return
    # Проверяем, достиг ли пользователь лимитов по токенам /tts
    if not is_tts_symbol_limit_per_person(user_id):
        bot.send_message(user_id, 'Ваши токены для озвучивания сообщений исчерпаны.')
        logging.info(f'User_id {user_id} ran out of tts tokens')
        return

    bot.send_message(user_id, 'Введите текст, который вы хотите озвучить.')
    bot.register_next_step_handler(message, tts)


def tts(message: Message):
    user_id = message.from_user.id

    if not is_user_amount_limit(user_id):
        bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                   'К сожалению, вы не сможете им воспользоваться.'))
        logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
        return

    if message.content_type != 'text':
        bot.send_message(user_id, 'Введите, пожалуйста, текст')
        bot.register_next_step_handler(message, tts)
        logging.info(f'User_id {user_id} sent not the text to /tts')
        return
    # Проверяем, чтобы пользователь не ввел слишком большой единичный промпт.
    if not is_tts_symbol_limit_per_message(message.text):
        bot.send_message(user_id, 'Введите сообщение покороче')
        bot.register_next_step_handler(message, tts)
        logging.info(f'User_id {user_id} sent too large message to /tts')
        return
    # При каждом вызове GPT, STT, TTS, TOKENIZER мы будем проверять, не вышло ли наше время использования IEM-токена
    if not check_and_create_IEM_token(IEM_TOKEN_INFO['EXPIRES_IN']):
        bot.send_message(user_id, 'Произошла ошибка взаимодействия с нейронной сетью. Приносим свои извинения.')
        return
    status, audio = text_to_speech(message.text)

    if status:
        bot.send_voice(user_id, audio)
        update_tts_tokens_in_limits(user_id, len(message.text)) # обновляем информацию о лимитах пользователя
        insert_row_into_prompts((user_id, 'user', message.text)) # добавляем сообщение в таблицу
    else:
        bot.send_message(user_id, 'Что-то пошло не так. Приносим свои извинения.')
        logging.error(f'User_id {user_id} got error accessing SpeachKit tts')


@bot.message_handler(commands=['stt'])
def stt_handler(message: Message):
    user_id = message.from_user.id

    if not is_user_amount_limit(user_id):
        bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                   'К сожалению, вы не сможете им воспользоваться.'))
        logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
        return

    if not user_in_table(user_id):
        bot.send_message(user_id, 'Нажмите для начала /start, для регистрации.')
        logging.warning(f'User_id {user_id} got access to commands without registration')
        return
    # Проверяем, достиг ли пользователь лимита по stt блокам
    if not is_stt_blocks_limit_per_person(user_id):
        bot.send_message(user_id, 'Ваш лимит расшифровывания голосового сообщения, к сожалению, исчерпан.')
        logging.info(f'User_id {user_id} run out of stt blocks')
        return

    bot.send_message(user_id, 'Запишите голосовое сообщение, которое хотите расшифровать.')
    bot.register_next_step_handler(message, stt)


def stt(message: Message):
    user_id = message.from_user.id

    if not is_user_amount_limit(user_id):
        bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                   'К сожалению, вы не сможете им воспользоваться.'))
        logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
        return

    if message.content_type != 'voice':
        bot.send_message(user_id, 'Пожалуйста, запишите голосовое сообщение, которое вы хотите расшифровать.')
        bot.register_next_step_handler(message, stt)
        logging.info(f'User_id {user_id} sent not the voice format message to stt')
        return

    if not is_stt_blocks_limit_per_message(message.voice.duration):
        bot.send_message(user_id, 'Слишком длинное голосовое сообщение, должно быть меньше 30 секунд.')
        bot.register_next_step_handler(message, stt)
        logging.info(f'User_id sent too large voice message (over or equal to 30 second)')
        return

    file_id = message.voice.file_id  # получаем id голосового сообщения
    file_info = bot.get_file(file_id)  # получаем информацию о голосовом сообщении
    file = bot.download_file(file_info.file_path)  # скачиваем голосовое сообщение

    if not check_and_create_IEM_token(IEM_TOKEN_INFO['EXPIRES_IN']):
        bot.send_message(user_id, 'Произошла ошибка взаимодействия с нейронной сетью. Приносим свои извинения.')
        return
    status, text = speech_to_text(file)

    if status:
        bot.send_message(user_id, text)
        update_stt_blocks_in_limits(user_id, ceil(message.voice.duration / 15))
        insert_row_into_prompts((user_id, 'system', text))
    else:
        bot.send_message(user_id, 'Что-то пошло не так. Приносим свои извинения.')
        logging.error(f'User_id {user_id} got an error accessing SpeachKit stt')


@bot.message_handler(content_types=['text'])
def ttt(message: Message):
    user_id = message.from_user.id

    if not is_user_amount_limit(user_id):
        bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                   'К сожалению, вы не сможете им воспользоваться.'))
        logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
        return

    if not user_in_table(user_id):
        bot.send_message(user_id, 'Нажмите для начала /start, для регистрации.')
        logging.warning(f'User_id {user_id} got access to commands without registration')
        return

    if not check_and_create_IEM_token(IEM_TOKEN_INFO['EXPIRES_IN']):
        bot.send_message(user_id, 'Произошла ошибка взаимодействия с нейронной сетью. Приносим свои извинения.')
        return

    if not is_gpt_tokens_limit_per_person(user_id):
        bot.send_message(user_id, 'Ваши токены для взаимодействия с языковой моделью закончились.')
        logging.info(f'User_id {user_id} ran out of gpt tokens')
        return

    is_limit, tokens = is_gpt_tokens_limit_per_message(message.text, SYSTEM_PROMPT)
    if not is_limit:
        bot.send_message(user_id, 'Слишком длинное сообщение, укоротите его.')
        bot.register_next_step_handler(message, ttt)
        logging.info(f'User_id {user_id} sent too large message to gpt model')
        return

    if get_user_prompts(user_id):
        prompt = 'Продолжи общение с пользователем, вот ваша переписка: '+get_user_prompts(user_id) +' '+ message.text
    else:
        prompt = 'Вот сообщение пользователя:' + message.text
    print(prompt)

    if not check_and_create_IEM_token(IEM_TOKEN_INFO['EXPIRES_IN']):
        bot.send_message(user_id, 'Произошла ошибка взаимодействия с нейронной сетью. Приносим свои извинения.')
        return
    status, text = gpt(prompt, SYSTEM_PROMPT)

    if status:
        bot.send_message(user_id, text)
        insert_row_into_prompts((user_id, 'user', message.text))
        update_gpt_tokens_in_limits(user_id, tokens)
        insert_row_into_prompts((user_id, 'system', text))
    else:
        bot.send_message(user_id, 'Что-то пошло не так. Приносим свои извинения.')
        logging.error(f'User_id {user_id} got an error accessing gpt model: {text}')


@bot.message_handler(content_types=['voice'])
def sts(message: Message):
    user_id = message.from_user.id

    if not is_user_amount_limit(user_id):
        bot.send_message(user_id, ('Бот достиг максимального числа пользователей. '
                                   'К сожалению, вы не сможете им воспользоваться.'))
        logging.info(f'Amount of users is full and user_id {user_id} tried to connect to the bot')
        return

    if not user_in_table(user_id):
        bot.send_message(user_id, 'Нажмите для начала /start, для регистрации.')
        logging.warning(f'User_id {user_id} got access to commands without registration')
        return

    if not is_stt_blocks_limit_per_person(user_id):
        bot.send_message(user_id, 'Ваш лимит расшифровывания голосового сообщения, к сожалению, исчерпан.')
        logging.info(f'User_id {user_id} run out of stt blocks')
        return

    if not is_stt_blocks_limit_per_message(message.voice.duration):
        bot.send_message(user_id, 'Слишком длинное голосовое сообщение, должно быть меньше 30 секунд.')
        bot.register_next_step_handler(message, stt)
        logging.info(f'User_id sent too large voice message (over 30 second)')
        return

    file_id = message.voice.file_id  # получаем id голосового сообщения
    file_info = bot.get_file(file_id)  # получаем информацию о голосовом сообщении
    file = bot.download_file(file_info.file_path)  # скачиваем голосовое сообщение

    if not check_and_create_IEM_token(IEM_TOKEN_INFO['EXPIRES_IN']):
        bot.send_message(user_id, 'Произошла ошибка взаимодействия с нейронной сетью. Приносим свои извинения.')
        return
    status, text = speech_to_text(file)

    if not status:
        bot.send_message(user_id, 'Что то пошло не так. Приносим свои извинения.')
        logging.error(f'User_id {user_id} got an error accessing SpeachKit stt in sts')
        return

    update_stt_blocks_in_limits(user_id, ceil(message.voice.duration / 15))
    insert_row_into_prompts((user_id, 'system', text))

    if not is_gpt_tokens_limit_per_person(user_id):
        bot.send_message(user_id, ('Ваши токены взаимодействия с языковой моделью закончились, '
                                   'вот по крайней мере ваше расшифрованное голосовое:'))
        bot.send_message(user_id, text)
        logging.info(f'User_id {user_id} ran out of gpt tokens')
        return

    is_limit, tokens = is_gpt_tokens_limit_per_message(text, SYSTEM_PROMPT)
    if not is_limit:
        bot.send_message(user_id, ('Слишком длинное голосовое сообщение, укоротите его. '
                                   'Зато вот ваше расшифрованное голосовое:'))
        bot.send_message(user_id, text)
        bot.register_next_step_handler(message, ttt)
        logging.info(f'User_id {user_id} sent too large voice message by its characters to pass it to gpt in sts')
        return

    if not check_and_create_IEM_token(IEM_TOKEN_INFO['EXPIRES_IN']):
        bot.send_message(user_id, 'Произошла ошибка взаимодействия с нейронной сетью. Приносим свои извинения.')
        return

    if get_user_prompts(user_id):
        prompt = 'Продолжи общение с пользователем, вот ваша переписка: '+get_user_prompts(user_id) +' '+ text
    else:
        prompt = 'Вот сообщение пользователя:' + text

    status, gpt_text = gpt(prompt, SYSTEM_PROMPT)

    if not status:
        bot.send_message(user_id, ('Что-то пошло не так с языковой моделькой.'
                                   'В качестве извинений приподносим вам ваше расшифрованное голосовое:'))
        bot.send_message(user_id, text)
        logging.error(f'User_id {user_id} got an error accessing gpt model: {text}')
        return

    update_gpt_tokens_in_limits(user_id, tokens)
    insert_row_into_prompts((user_id, 'system', gpt_text))

    if not is_tts_symbol_limit_per_person(user_id):
        bot.send_message(user_id, ('Ваши лимиты перевода извучки текста исчерпаны.'
                                   'Ответ языковой модели текстом:'))
        bot.send_message(user_id, gpt_text)
        logging.info(f'User_id {user_id} ran out of tts tokens')
        return

    if not check_and_create_IEM_token(IEM_TOKEN_INFO['EXPIRES_IN']):
        bot.send_message(user_id, 'Произошла ошибка взаимодействия с нейронной сетью. Приносим свои извинения.')
    status, audio = text_to_speech(gpt_text)

    if not status:
        bot.send_message(user_id, ('Что-то пошло не так с преобразованием текста языковой модели в аудио формат.'
                                   'В качестве извинения приподносим вам текст языковой модели.'))
        bot.send_message(user_id, gpt_text)
        logging.error(f'User_id {user_id} got an error accessing SpeachKit tts')
        return

    update_tts_tokens_in_limits(user_id, len(gpt_text))
    bot.send_voice(user_id, audio)


if __name__ == '__main__':

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename='logging.txt',
        filemode='w'
    )
    # Создаем две таблицы: одна для лимитов токенов и блоков пользователей, другая - для промптов.
    create_table_limits()
    create_table_prompts()
    logging.info('Tables are created')
    # Создаем меню в телеграмме
    c1 = BotCommand(command='start', description='Начать взаимодействие с ботом')
    c2 = BotCommand(command='help', description='Помощь с ботом')
    c3 = BotCommand(command='tts', description='Озвучка текста')
    c4 = BotCommand(command='stt', description='Перевод аудио в текст')

    bot.set_my_commands([c1, c2, c3, c4])

    bot.polling()