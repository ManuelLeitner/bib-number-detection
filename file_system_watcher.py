from threading import Thread
import os
from time import sleep

from result_collector import ResultCollector, ResultState
from typing import Callable


class FileSystemWatcher:

    def __init__(self, image_directory: str, result_collector: ResultCollector):
        self.image_directory =os.path.normpath(image_directory)
        self.listeners: [Callable[[[str]], None]] = []
        self.result_collector = result_collector

        self.watching = True
        self.watcher = Thread(target=self.watch)
        self.watcher.start()

    def add_listener(self, listener: Callable[[[str]], None]):
        self.listeners.append(listener)

    def watch(self):
        while self.watching:
            files = [os.path.join(self.image_directory,f) for f in os.listdir(self.image_directory)]
            done = [r.get_image() for r in self.result_collector.results.values() if r.get_state() != ResultState.FTP_UPLOADED]
            files = [f for f in files if f not in done]
            if len(files) > 0:
                self.result_collector.add_images(files)
                for li in self.listeners:
                    li(files)
            sleep(1)

    def stop(self):
        self.watching = False
