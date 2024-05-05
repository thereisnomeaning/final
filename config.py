from dotenv import load_dotenv
from os import getenv
import time

load_dotenv()

BOT_TOKEN = getenv('BOT_TOKEN')
FOLDER_ID = getenv('FOLDER_ID')
IEM_TOKEN_INFO = {'IEM_TOKEN': '',
                  'EXPIRES_IN': time.time()-1}

ADMIN_ID = int(getenv('ADMIN_ID'))

MAX_MODEL_TOKENS = 200
MAX_USERS = 2
MAX_STT_BLOCKS_PER_PERSON = 3
MAX_GPT_TOKENS_PER_PERSON = 200
MAX_TTS_TOKENS_PER_PERSON = 200

MAX_GPT_TOKENS_PER_MESSAGE = 200
MAX_TTS_TOKENS_PER_MESSAGE = 100

SYSTEM_PROMPT = 'Ты ведешь диалог с пользователем. Ты играешь роль психолога. Просто лаконично продолжай сообщение от лица психолога.'


class TTS:
    headers = {'Authorization': f'Bearer {IEM_TOKEN_INFO["IEM_TOKEN"]}'}
    url = getenv('TTS_URL')
    data = {
        'text': None,  # текст, который нужно преобразовать в голосовое сообщение
        'lang': 'ru-RU',  # язык текста - русский
        'voice': 'alena',
        'emotion': 'good',
        'folderId': FOLDER_ID
    }


class STT:
    # Указываем параметры запроса
    params = "&".join([
        "topic=general",  # используем основную версию модели
        f"folderId={FOLDER_ID}",
        "lang=ru-RU"  # распознаём голосовое сообщение на русском языке
    ])
    url = getenv('STT_URL') + params
    headers = {'Authorization': f'Bearer {IEM_TOKEN_INFO["IEM_TOKEN"]}'}


class TOKENIZER:
    url = getenv('TOKENIZER_URL')
    headers = {
        'Authorization': f'Bearer {IEM_TOKEN_INFO["IEM_TOKEN"]}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
        "maxTokens": MAX_MODEL_TOKENS,
        "messages": []
    }


class GPT:
    url = getenv('GPT_URL')
    headers = {
        'Authorization': f'Bearer {IEM_TOKEN_INFO["IEM_TOKEN"]}',
        'Content-Type': 'application/json'}
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",  # модель для генерации текста
        "completionOptions": {
            "stream": False,  # потоковая передача частично сгенерированного текста выключена
            "temperature": 0.3,  # чем выше значение этого параметра, тем более креативными будут ответы модели (0-1)
            "maxTokens": "50"  # максимальное число сгенерированных токенов
        },
        "messages": [
            {
                "role": "user",  # пользователь спрашивает у модели
                "text": None  # передаём текст, на который модель будет отвечать
            },
            {
                "role": "system",
                "text": None
            }
        ]
    }


class IEM:
    headers = {"Metadata-Flavor": "Google"}
    metadata_url = getenv('IEM_TOKEN_URL')


