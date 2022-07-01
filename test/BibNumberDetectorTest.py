import os.path
import unittest
from detection.BibNumberDetector import BibNumberDetector


class BibNumberDetectorTest(unittest.TestCase):
    def test_detect_bib_number_single_success(self):
        det = BibNumberDetector("res/test/output")
        bibs = det.detect_bib_numbers_single("res/test/imgs/test1.jpg")

        self.assertListEqual([518], bibs)

    def test_detect_bib_number_single_fail(self):
        det = BibNumberDetector("res/test/output")
        bibs = det.detect_bib_numbers_single("res/test/imgs/test_fail.jpg")

        self.assertListEqual([], bibs)

    def test_detect_bib_number_single_not_a_picture(self):
        det = BibNumberDetector("res/test/output")
        bibs = det.detect_bib_numbers_single("res/test/imgs/not_an_img.txt")

        self.assertIsNone(bibs)

    def test_detect_bib_number_success(self):
        det = BibNumberDetector("res/test/output")
        bibs = det.detect_bib_numbers("res/test/imgs/imgdirectory")

        self.assertDictEqual({os.path.normpath('res/test/imgs/imgdirectory/test1.jpg'): [518],
                              os.path.normpath('res/test/imgs/imgdirectory/test2.jpg'): [376, 246]}, bibs)


if __name__ == '__main__':
    unittest.main()
