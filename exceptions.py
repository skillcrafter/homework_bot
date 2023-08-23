class CheckResponseError(Exception):
    def __init__(self, text):
        message = (
            f'Проверка ответа API: {text}'
        )
        super().__init__(message)
