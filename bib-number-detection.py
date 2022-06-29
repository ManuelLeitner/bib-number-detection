import logging

# import Craft class

# OpenCV
import argparse

import sys

from detection.BibNumberDetector import BibNumberDetector
from detection.service.MockBibNumberService import MockBibNumberService
from detection.service.interface.IBibNumberService import IBibNumberService



def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S', filename='logs/bib-number-detection.log', filemode='w')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", help="path to output directory", default="./imgs/out")
    parser.add_argument("imgs", help="path to input image(s)", nargs="*", default=["./imgs/zieleinlauf/Laufend Helfen 2021-05694.jpg"])
    parser.description = "Parses a given image and outputs the detected bib numbers"

    args = parser.parse_args()
    IMG_PATHS = args.imgs
    OUT_PATH = args.out

    with BibNumberDetector(OUT_PATH) as detector:
        for img_path in IMG_PATHS:
            detector.detect_bib_numbers(img_path)


if __name__ == '__main__':
    main()
