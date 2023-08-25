class CheckResponseError(Exception):
    """Проверка ответа API."""
    pass


class ApiRequestException(Exception):
    """Исключение из-за ошибки GET-запроса к эндпоинту."""
    pass
