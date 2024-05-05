import requests
from config import TTS, STT


def text_to_speech(text):
    data = TTS.data.copy()
    data['text'] = text
    response = requests.post(url=TTS.url, headers=TTS.headers, data=data)

    # Проверяем, не произошла ли ошибка при запросе
    if response.status_code == 200:
        return True, response.content  # возвращаем статус и аудио
    else:
        return False, "При запросе в SpeechKit возникла ошибка"


def speech_to_text(text):
    response = requests.post(url=STT.url, headers=TTS.headers, data=text)
    decoded_data = response.json()

    # Проверяем, не произошла ли ошибка при запросе
    if decoded_data.get("error_code") is None:
        return True, decoded_data.get("result")  # Возвращаем статус и текст из аудио
    else:
        return False, "При запросе в SpeechKit возникла ошибка"