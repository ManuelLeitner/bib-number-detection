import os
from typing import Dict, List, Tuple

from client import ApiClient
from result import Result, ResultType, ResultState


class ResultCollector:
    results: Dict[str, Result]

    def __init__(self, client: ApiClient, result_type: ResultType, buffer_file: str, image_dir: str,
                 batch_size: int = 1):
        self.client = client
        self.buffer_file = buffer_file
        self.batchSize = batch_size
        self.result_type = result_type
        self.image_dir = image_dir

        if os.path.exists(buffer_file):
            with open(buffer_file, 'r') as f:
                c = f.readlines()
                res = [Result.parse_one_line_csv(r) for r in c]
                if len(res) > 0:
                    self.results = {r.get_image(): r for r in res}
                    self.__send()
                    return
        self.results = {}

    def add_manually(self, numbers: [int], image_file: str) -> None:

        img = os.path.normpath(os.path.join(self.image_dir, image_file))
        self.results[img].add_numbers(numbers)

        self.__send()

    def add_ai(self, res: Dict[str, List[int]]) -> None:
        for r in res:
            self.results[r].add_numbers(res[r])
        self.__buffer()

    def get_manual_pending(self) -> Tuple[str, List[int]] | None:
        p = [r for r in self.results.values() if r.get_state() == ResultState.PENDING_MANUALLY]
        if len(p) == 0:
            return None
        return p[0].next_state().get_image()

    def get_ai_pending(self) -> [Result]:
        return [r.next_state() for r in self.results.values() if r.get_state() == ResultState.FTP_UPLOADED]

    def __buffer(self) -> None:
        with open(self.buffer_file, 'w') as f:
            c = [v.get_one_line_csv() for v in self.results.values()]
            f.writelines(c)

    def add_images(self, files: [str]) -> None:
        for f in files:
            self.results[f] = Result(f, self.result_type)
        self.__buffer()

    def detection_started(self, files):
        for f in files:
            self.results[f].detection_started()

    def __send(self):
        pending = [r for r in self.results.values() if r.get_state() == ResultState.PENDING_UPLOAD]
        lines = [l for r in pending for l in r.get_csv()]
        try:
            if self.client.send(lines):
                for r in pending:
                    r.next_state()
        except:
            pass

        self.__buffer()
