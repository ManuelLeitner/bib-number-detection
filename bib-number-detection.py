import datetime
import logging
import warnings
import numpy as np
import argparse
import os.path
import sys
import random
import time
from detection.BibNumberDetector import BibNumberDetector

warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning)


def main():
    if not os.path.exists("logs"):
        os.mkdir("logs")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S',
                        filename=f"logs/bib-number-detection-{random.randint(1000, 9999)}.log", filemode='w')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", help="path to output directory", default="./out")
    parser.add_argument("imgs", help="path to input image(s)", nargs="+")
    parser.description = "Parses a given image and outputs the detected bib numbers"

    args = parser.parse_args()
    IMG_PATHS = args.imgs
    OUT_PATH = args.out

    startTime = time.time()
    with BibNumberDetector(OUT_PATH) as detector:
        for img_path in IMG_PATHS:
            if not os.path.exists(img_path):
                logging.error("Image path does not exist: {}".format(img_path))
                continue
            detector.detect_bib_numbers(img_path)
        logging.info(
            f"Processed {detector.img_counter} images with {detector.img_with_bibs_ctr} images where at least 1 bib number was found ({detector.img_with_bibs_ctr / detector.img_counter * 100}%)")
    logging.info(
        f"Total time: {datetime.timedelta(seconds=time.time() - startTime)}s with average of {datetime.timedelta(seconds=(time.time() - startTime) / detector.img_counter)}s per image")


if __name__ == '__main__':
    main()
