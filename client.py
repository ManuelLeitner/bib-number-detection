import requests

from result import Result


class ApiClient:
    def __init__(self, url: str, user: str, password: str):
        (self.url, self.auth) = (url, (user, password))

    def send(self, pending: [int]) -> bool:
        data = Result.header+"\n"+"\n".join(pending)
        response = requests.post(self.url, data=data.encode("utf-8"), auth=self.auth,
                                 headers={"Content-Type": "text/csv; charset=utf-8"})
        return response.status_code//100 == 2
