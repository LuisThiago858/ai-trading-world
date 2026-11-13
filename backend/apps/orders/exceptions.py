class TradingError(Exception):
    def __init__(self, code, detail, *, http_status=409, data=None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.http_status = http_status
        self.data = data or {}

    def as_dict(self):
        return {"code": self.code, "detail": self.detail, **self.data}
