import requests


class ApiClient:
    def __init__(self, url: str, user: str, password: str):
        (self.url, self.auth) = (url, (user, password))

    def send(self, pending: [int]) -> bool:
        response = requests.post(self.url, data=pending, auth=self.auth)
        return response.status_code == 200
