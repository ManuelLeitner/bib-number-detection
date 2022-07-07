import argparse
import datetime
import logging
import os.path
import sys
import threading
import time
import warnings
import globals
import numpy as np

from detection.BibNumberDetector import BibNumberDetector

warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning)


def main():
    if not os.path.exists("logs"):
        os.mkdir("logs")
    logging_file_name = "logs/bib-number-detection-{}.log".format(
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))

    def num_range(x):
        x = int(x)
        if x < 1:
            raise argparse.ArgumentTypeError("Thread count must be greater than 0")
        elif x > 10:
            raise argparse.ArgumentTypeError("Thread count must be less than or equal 10")
        return x

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", help="path to output directory", default="./out")
    parser.add_argument("imgs", help="path to input image(s)", nargs="+")
    parser.add_argument("-t", "--threads", help="number of threads 1 <= t <= 10", default=1, type=num_range)
    parser.add_argument("-log", "--log", help="log level", default="info",
                        choices=["debug", "info", "warning", "error", "critical"])
    parser.description = "Parses a given image and outputs the detected bib numbers"

    args = parser.parse_args()
    globals.LOG_LEVEL = getattr(logging, args.log.upper())
    logging.basicConfig(level=globals.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S',
                        filename=logging_file_name, filemode='w')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    IMG_PATHS = args.imgs
    OUT_PATH = args.out
    NUM_THREADS = args.threads

    startTime = time.time()
    with BibNumberDetector(OUT_PATH, NUM_THREADS) as detector:
        for img_path in IMG_PATHS:
            if not os.path.exists(img_path):
                logging.error("Image path does not exist: {}".format(img_path))
                continue
            detector.detect_bib_numbers(img_path)
        for t in threading.enumerate():
            if t is not threading.current_thread():
                t.join()  # wait for all threads to finish
        logging.info(
            f"Processed {detector.img_counter} images with {detector.img_with_bibs_ctr} images where at least 1 bib number was found ({detector.img_with_bibs_ctr / detector.img_counter * 100}%)")
    logging.info(
        f"Total time: {datetime.timedelta(seconds=time.time() - startTime)}s with average of {datetime.timedelta(seconds=(time.time() - startTime) / detector.img_counter)}s per image")


if __name__ == '__main__':
    main()
