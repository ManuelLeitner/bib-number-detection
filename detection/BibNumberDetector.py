import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import pytesseract
from craft_text_detector import (
    load_craftnet_model,
    load_refinenet_model,
    get_prediction,
    export_detected_regions,
    export_extra_results,
    empty_cuda_cache
)

from detection.service.MockBibNumberService import MockBibNumberService
from detection.service.interface.IBibNumberService import IBibNumberService
import globals


class BibNumberDetector:
    def __init__(self, OUT_PATH: str, NUM_THREADS: int = 1):
        self.threadLock = threading.Lock()
        self.img_with_bibs_ctr = 0
        self.img_counter = 0
        self.img_count_all = -1
        self.__TESSERACT_CONFIG__ = "--psm 13"
        self.NUM_THREADS = NUM_THREADS

        self.__supported_image_formats__ = ["jpg", "jpeg", "png", "tif", "tiff", "bmp", "dib", "webp"]

        self.refine_net = load_refinenet_model()
        self.craft_net = load_craftnet_model()

        self.bib_number_svc: IBibNumberService = MockBibNumberService()

        if not os.path.exists(OUT_PATH):
            os.makedirs(OUT_PATH)
        if not os.path.isdir(OUT_PATH):
            logging.fatal("Output path is not a directory: {}".format(OUT_PATH))
            sys.exit(-1)
        self.OUT_PATH = OUT_PATH

    def __enter__(self):
        return self

    def detect_bib_numbers(self, img_path) -> dict[str, list[int]]:
        ret: dict[str, list[int]] = {}
        return self._detect_bib_numbers(img_path, ret)

    def _detect_bib_numbers(self, img_path, ret: dict[str, list[int]]) -> dict[str, list[int]]:
        try:
            if type(img_path) == list or os.path.isdir(img_path):

                img_files = img_path or [os.path.join(img_path, img_file) for img_file in os.listdir(img_path)]
                self.img_count_all = len(img_files)
                with ThreadPoolExecutor(max_workers=self.NUM_THREADS) as executor:
                    futures = [executor.submit(self._detect_bib_numbers,img_file, ret) for
                               img_file in img_files]
                    for f in futures:
                        ret.update(f.result())

            else:
                ret[os.path.normpath(img_path)] = self.detect_bib_numbers_single(img_path)
        except Exception as e:
            logging.error(e)
            logging.error("FATAL: Could not process img_path: {}".format(img_path))
        return ret

    def detect_bib_numbers_single(self, img_path: str) -> list[int] | None:
        if img_path.split(".")[-1] not in self.__supported_image_formats__:
            logging.warning("Image format not supported: {}".format(img_path))
            return None
        output_dir = os.path.join(self.OUT_PATH, os.path.basename(img_path))

        with self.threadLock:
            self.img_counter += 1
        logging.info("Processing image{}: {}".format(
            "" if self.img_count_all == -1 else f" ({self.img_counter}/{self.img_count_all})",
            os.path.abspath(img_path)))
        logging.info("Output path: {}".format(os.path.abspath(output_dir)))
        t0 = time.time()

        # apply craft text detection and export detected regions to output directory
        prediction_result = get_prediction(
            image=img_path,
            craft_net=self.craft_net,
            refine_net=self.refine_net,
            text_threshold=0.7,
            link_threshold=0.4,
            low_text=0.4,
            cuda=False,
            long_size=1280
        )
        regions = prediction_result["polys"]
        if type(img_path) == str:
            file_name, file_ext = os.path.splitext(os.path.basename(img_path))
        else:
            file_name = "image"
        if globals.LOG_LEVEL <= logging.INFO:
            exported_file_paths = export_detected_regions(
                image=img_path,
                regions=regions,
                file_name=file_name,
                output_dir=output_dir,
                rectify=True,
            )
        # extra results
        if globals.LOG_LEVEL <= logging.DEBUG:
            export_extra_results(
                image=img_path,
                regions=regions,
                heatmaps=prediction_result["heatmaps"],
                file_name=file_name,
                output_dir=output_dir,
            )
        image = cv2.imread(img_path)

        found_bibs: list[int] = []
        for box in regions:
            cropped_img = rectify_poly(image, box)

            result: str = pytesseract.image_to_string(cropped_img, config=self.__TESSERACT_CONFIG__).strip()
            logging.debug("Detected text: {}".format(result))
            try:
                result_number = int(result)
                if self.bib_number_svc.find_number(int(result)) is not None:
                    found_bibs.append(int(result))
                    logging.info("Found bib number: {}".format(result_number))
            except ValueError:
                logging.debug("Could not parse bib number: {}".format(result))

        with open(os.path.join(output_dir, "output.txt"), "w+") as f:
            if not len(found_bibs) == 0:
                with self.threadLock:
                    self.img_with_bibs_ctr += 1
                f.write("Found bib numbers: {}".format(found_bibs))
            else:
                f.write("No bib numbers found")
                logging.info("No bib numbers found")

        logging.info("Processing time: {} seconds".format(time.time() - t0))
        logging.info("Done processing image{}: {}\n".format(
            "" if self.img_count_all == -1 else f" ({self.img_counter}/{self.img_count_all})",
            os.path.abspath(img_path)))
        return found_bibs

    def __exit__(self, exc_type, exc_val, exc_tb):
        empty_cuda_cache()


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
