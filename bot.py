import logging
import os
import uuid

import speech_recognition as sr
import telebot
from dotenv import load_dotenv
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO)

load_dotenv()

token = os.environ.get('TOKEN')
bot = telebot.TeleBot(token)


def oga2wav(filename):
    """
    Конвертирует аудиофайл из формата .oga в формат .wav.

    :param filename: Имя файла с расширением .oga
    :return: Имя нового файла с расширением .wav или None в случае ошибки
    """
    try:
        new_filename = filename.replace('.oga', '.wav')
        audio = AudioSegment.from_file(filename)
        audio.export(new_filename, format='wav')
        return new_filename
    except Exception as e:
        logging.error(f"Ошибка конвертации файла: {e}")
        return None


def recognize_speech(oga_filename):
    """
    Распознает речь из аудиофайла и возвращает текст.

    :param oga_filename: Имя файла с расширением .oga
    :return: Распознанный текст или сообщение об ошибке """
    wav_filename = oga2wav(oga_filename)
    if not wav_filename:
        return "Ошибка конвертации аудио."

    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(wav_filename) as source:
            wav_audio = recognizer.record(source)
            text = recognizer.recognize_google(wav_audio, language='ru')
    except sr.UnknownValueError:
        text = "Не удалось распознать речь."
    except sr.RequestError as e:
        text = f"Ошибка сервиса распознавания речи: {e}"
    except Exception as e:
        text = f"Ошибка обработки аудио: {e}"
    finally:
        # Удаление временных файлов
        if os.path.exists(oga_filename):
            os.remove(oga_filename)
        if os.path.exists(wav_filename):
            os.remove(wav_filename)

    return text


def download_file(bot, file_id):
    """
    Скачивает файл с сервера Telegram и сохраняет его локально.

    :param bot: Экземпляр бота TeleBot
    :param file_id: Идентификатор файла в Telegram
    :return: Путь к сохраненному файлу или None в случае ошибки
    """
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        directory = 'voice'
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = f"{uuid.uuid4()}{os.path.basename(file_info.file_path)}"
        filepath = os.path.join(directory, filename)
        with open(filepath, 'wb') as f:
            f.write(downloaded_file)
        return filepath
    except Exception as e:
        logging.error(f"Ошибка скачивания файла: {e}")
        return None


@bot.message_handler(commands=['start'])
def say_hello(message):
    """
    Обрабатывает команду /start и отправляет приветственное сообщение.

    :param message: Сообщение от пользователя
    """
    bot.send_message(message.chat.id, f'Привет, {
                     message.from_user.first_name}!)')


@bot.message_handler(content_types=['voice'])
def transcript(message):
    """
    Обрабатывает голосовые сообщения, преобразует их в текст и
    отправляет ответ.

    :param message: Сообщение от пользователя
    """
    filename = download_file(bot, message.voice.file_id)
    if filename and os.path.exists(filename):
        text = recognize_speech(filename)
        bot.send_message(message.chat.id, text)
        if os.path.exists(filename):
            os.remove(filename)
    else:
        bot.send_message(
            message.chat.id, 'Не удалось скачать или обработать файл')


bot.polling()
