from datetime import datetime
import os
import jsonpickle
from client import ApiClient
from typing import Dict, List, Tuple
from enum import IntEnum, Flag


class InvalidStateException(Exception):
    pass


class ResultState(Flag):
    DETECTING = 1
    FTP_UPLOADED = 2
    DETECTING_AI = 5
    PENDING_MANUALLY = 8
    DETECTING_MANUALLY = 17
    PENDING_UPLOAD = 32
    UPLOADED = 64


class ResultType(IntEnum):
    CAR = 1  # "car"
    FINISH = 2  # "finish"


class Result:
    header = "tag_id;timestamp;is_car"

    def __init__(self, img: str | Dict, result_type: ResultType | None = None):
        self.__numbers = []
        if type(img) == str:
            self.__image = img
            self.__time = datetime.utcfromtimestamp(os.path.getmtime(img))
            self.__state = ResultState.FTP_UPLOADED
            self.__type = result_type
        else:
            self.__dict__ = img

    def add_numbers(self, numbers: [int]) -> None:
        if self.__state & ResultState.DETECTING:
            self.__numbers.extend(numbers)
            self.__state = ResultState((self.__state.value - 1) << 1)
        else:
            raise InvalidStateException

    def next_state(self):
        v = self.__state.value << 1
        if v == 16 or v == 4: v += 1
        self.__state = ResultState(v)
        return self

    def get_state(self) -> ResultState:
        return self.__state

    def get_image(self) -> str:
        return self.__image

    def get_csv(self) -> [str]:
        return [f'{self.__time:yyyy-MM-dd HH:mm:ss};{number};{self.__type};{self.__image}' for number in self.__image]

    def detection_started(self):
        if self.__state == ResultState.FTP_UPLOADED:
            self.__state = ResultState.DETECTING_AI
        else:
            raise InvalidStateException


class ResultCollector:
    results: Dict[str, Result]

    def __init__(self, client: ApiClient, result_type: ResultType, buffer_file: str,
                 batch_size: int = 10):
        self.client = client
        self.buffer_file = buffer_file
        self.batchSize = batch_size
        self.result_type = result_type

        if os.path.exists(buffer_file):
            with open(buffer_file, 'r') as f:
                res = [r for r in jsonpickle.loads(f.read())]
                if len(res) > 0:
                    self.results = {r.get_image(): r for r in res}
                    return
        self.results = {}

    def add_manually(self, numbers: [int], image_file: str) -> None:

        self.results[image_file].add_numbers(numbers)

        pending = [r for r in self.results.values() if r.get_state() == ResultState.PENDING_UPLOAD]
        lines = [l for r in pending for l in r.get_csv()]

        if self.client.send(lines):
            for r in pending:
                r.next_state()

        self.__buffer()

    def add_ai(self, res: Dict[str, List[int]]) -> None:
        for r in res:
            self.results[r].add_numbers(res[r])
        self.__buffer()

    def get_manual_pending(self) -> Tuple[str, List[int]] | None:
        p = [r for r in self.results.values() if r.get_state() == ResultState.PENDING_MANUALLY]
        if len(p)==0:
            return None
        return p[0].next_state().get_image()


    def get_ai_pending(self) -> [Result]:
        return [r.next_state() for r in self.results.values() if r.get_state() == ResultState.FTP_UPLOADED]

    def __buffer(self) -> None:
        with open(self.buffer_file, 'w') as f:
            f.write(jsonpickle.dumps(list(self.results.values())))

    def add_images(self, files: [str]) -> None:
        for f in files:
            self.results[f] = Result(f, self.result_type)
        self.__buffer()

    def detection_started(self, files):
        for f in files:
            self.results[f].detection_started()
