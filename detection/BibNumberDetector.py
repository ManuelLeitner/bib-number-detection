import numpy as np
import logging
import os
import sys

import cv2
import pytesseract
from craft_text_detector import Craft

from detection.service.MockBibNumberService import MockBibNumberService
from detection.service.interface.IBibNumberService import IBibNumberService


class BibNumberDetector:
    def __init__(self, OUT_PATH: str):
        self.__TESSERACT_CONFIG__ = "--psm 13"

        self.__supported_image_formats__ = ["jpg", "jpeg", "png", "tif", "tiff", "bmp", "dib", "webp"]

        self.craft = Craft(output_dir=OUT_PATH, crop_type="poly", cuda=False)

        self.bib_number_svc: IBibNumberService = MockBibNumberService()

        if not os.path.exists(OUT_PATH):
            os.makedirs(OUT_PATH)
        if not os.path.isdir(OUT_PATH):
            logging.fatal("Output path is not a directory: {}".format(OUT_PATH))
            sys.exit(-1)
        self.OUT_PATH = OUT_PATH

    def __enter__(self):
        return self

    def detect_bib_numbers(self, img_path):

        if os.path.isdir(img_path):
            for img_file in os.listdir(img_path):
                self.detect_bib_numbers(os.path.join(img_path, img_file))
        else:
            self.detect_bib_numbers_single(img_path)

    def detect_bib_numbers_single(self, img_path: str):
        if img_path.split(".")[-1] not in self.__supported_image_formats__:
            logging.warning("Image format not supported: {}".format(img_path))
            return
        logging.info("Processing image: {}".format(img_path))

        image = cv2.imread(img_path)


        # apply craft text detection and export detected regions to output directory
        prediction_result = self.craft.detect_text(img_path)

        for box in prediction_result["boxes"]:
            cropped_img = rectify_poly(image, box)

            result: str = pytesseract.image_to_string(cropped_img, config=self.__TESSERACT_CONFIG__)
            logging.debug("Detected text: {}".format(result))
            try:
                if self.bib_number_svc.find_number(int(result.strip())) is not None:
                    logging.info("Found bib number: {}".format(result))
            except:
                logging.debug("Could not parse bib number: {}".format(result))

        logging.info("Done processing image: {}".format(img_path))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.craft.unload_craftnet_model()
        self.craft.unload_refinenet_model()


def rectify_poly(img, poly):
    # Use Affine transform
    n = int(len(poly) / 2) - 1
    width = 0
    height = 0
    for k in range(n):
        box = np.float32([poly[k], poly[k + 1], poly[-k - 2], poly[-k - 1]])
        width += int(
            (np.linalg.norm(box[0] - box[1]) + np.linalg.norm(box[2] - box[3])) / 2
        )
        height += np.linalg.norm(box[1] - box[2])
    width = int(width)
    height = int(height / n)

    output_img = np.zeros((height, width, 3), dtype=np.uint8)
    width_step = 0
    for k in range(n):
        box = np.float32([poly[k], poly[k + 1], poly[-k - 2], poly[-k - 1]])
        w = int((np.linalg.norm(box[0] - box[1]) + np.linalg.norm(box[2] - box[3])) / 2)

        # Top triangle
        pts1 = box[:3]
        pts2 = np.float32(
            [[width_step, 0], [width_step + w - 1, 0], [width_step + w - 1, height - 1]]
        )
        M = cv2.getAffineTransform(pts1, pts2)
        warped_img = cv2.warpAffine(
            img, M, (width, height), borderMode=cv2.BORDER_REPLICATE
        )
        warped_mask = np.zeros((height, width, 3), dtype=np.uint8)
        warped_mask = cv2.fillConvexPoly(warped_mask, np.int32(pts2), (1, 1, 1))
        output_img[warped_mask == 1] = warped_img[warped_mask == 1]

        # Bottom triangle
        pts1 = np.vstack((box[0], box[2:]))
        pts2 = np.float32(
            [
                [width_step, 0],
                [width_step + w - 1, height - 1],
                [width_step, height - 1],
            ]
        )
        M = cv2.getAffineTransform(pts1, pts2)
        warped_img = cv2.warpAffine(
            img, M, (width, height), borderMode=cv2.BORDER_REPLICATE
        )
        warped_mask = np.zeros((height, width, 3), dtype=np.uint8)
        warped_mask = cv2.fillConvexPoly(warped_mask, np.int32(pts2), (1, 1, 1))
        cv2.line(
            warped_mask, (width_step, 0), (width_step + w - 1, height - 1), (0, 0, 0), 1
        )
        output_img[warped_mask == 1] = warped_img[warped_mask == 1]

        width_step += w
    return output_img
