class RequestFailed(Exception):
    def __init__(self, message="Falha na requisição."):
        self.message = message
        super().__init__(self.message)