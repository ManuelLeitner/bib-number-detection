import os
from datetime import datetime
from enum import Flag, IntEnum
from typing import Dict, Set


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

    def __init__(self, img: str | Dict, result_type: ResultType | None = None, state=ResultState.FTP_UPLOADED,
                 numbers: Set[int] = None):
        self.__numbers = numbers or set()
        if type(img) == str:
            self.__image = img
            self.__time = datetime.utcfromtimestamp(os.path.getmtime(img))
            self.__state = state
            self.__type = result_type
        else:
            self.__dict__ = img

    def add_numbers(self, numbers: [int]) -> None:
        if self.__state & ResultState.DETECTING:
            for n in numbers:
                self.__numbers.add(n)
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
        return [f'{number};{self.__time.strftime("%Y-%m-%d %H:%M:%S")};{self.__type.name.lower()}' for number in
                self.__numbers]

    def get_one_line_csv(self) -> str:
        return f'{self.__image};{self.__type};{self.__state.name};{";".join([str(v) for v in self.__numbers])}\n'

    @staticmethod
    def parse_one_line_csv(line) -> [str]:
        p = line.strip().split(";")
        return Result(p[0], ResultType(int(p[1])), ResultState[p[2]], {int(v) for v in p[3:] if len(v) > 0})

    def detection_started(self):
        if self.__state == ResultState.FTP_UPLOADED:
            self.__state = ResultState.DETECTING_AI
        else:
            raise InvalidStateException
