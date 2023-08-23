import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram.error import TelegramError

from exceptions import CheckResponseError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

ENV_VARS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(funcName)s',
    encoding='UTF-8',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - %(funcName)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверяет доступность переменных окружения, необходимых для работы."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot: telegram.Bot, message):
    """Oтправляет сообщение в Telegram чат"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Вам отправлено сообщение! {message}')

    except TelegramError as error:
        logging.error(f'Не удалось отправить сообщение {error}')


def get_api_answer(timestamp):
    """ Делает запрос к единственному эндпоинту API-сервиса"""
    try:
        params = {'from_date': timestamp}
        logging.info(f'Отправка запроса на {ENDPOINT} с параметрами {params}')
        homework = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        logging.info(f'Получен ответ {homework.json()}')
        if homework.status_code != HTTPStatus.OK:
            raise requests.RequestException()
    except requests.RequestException('Ошибка GET-запроса к эндпоинту'):
        logging.error('Исключение из-за ошибки GET-запроса к эндпоинту')
        raise requests.RequestException()
    return homework.json()


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if not response:
        message = 'Содержит пустой словарь.'
        logging.error(message)
        raise CheckResponseError(message)

    if not isinstance(response, dict):
        message = 'Ошибка в типе данных.'
        logging.error(message)
        raise TypeError(message)

    if 'homeworks' not in response or 'current_date' not in response:
        message = 'Ошибка словаря по ключу.'
        logging.error(message)
        raise KeyError(message)

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        message = 'Homeworks не является списком.'
        logging.error(message)
        raise TypeError(message)
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе, статус работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if 'homework_name' not in homework:
        logging.warning('Отсутствует ключ homework_name в ответе API.')
        raise KeyError('Нет ключа homework_name в ответе API')
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Отсутстует ключ homework_status в HOMEWORK_VERDICTS.'
        logging.error(message)
        raise KeyError('Нет ключа homework_status в ответе API')

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = "Отсутствует обязательная переменная окружения."
        logging.critical(message)
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            logging.info(homework.get("status"))
            new_status = homework.get("status")
            if new_status != last_status and homeworks:
                message = parse_status(homework)
                send_message(bot, message)
                last_status = new_status
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            try:
                send_message(bot, message)
            except TelegramError:
                logger.error("Ошибка при отправке сообщения в Telegram.")
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
