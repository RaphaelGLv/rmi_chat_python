class ResponseDto:
    def __init__(self, status: str, message: str = "", data: dict = None):
        self.status = status
        self.message = message
        self.data = data or {}

    def to_json(self):
        return {
            "status": self.status,
            "message": self.message,
            "data": self.data
        }