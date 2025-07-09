import logging
from paddleocr import PaddleOCR

logging.getLogger("ppocr").setLevel(logging.ERROR)

ocr_instance = None

def get_ocr_instance():
    global ocr_instance
    if ocr_instance is None:
        print("Loading OCR model...")
        ocr_instance = PaddleOCR(
            lang='en',
            use_angle_cls=True,
            det_model_dir="textModel/en_PP-OCRv3_det_infer",
            rec_model_dir="textModel/en_PP-OCRv4_rec_infer",
            cls_model_dir="textModel/ch_ppocr_mobile_v2.0_cls_infer"
        )
        print("OCR model loaded.")
    return ocr_instance


def ocr_with_paddle(image):
    ocr = get_ocr_instance()
    result = ocr.ocr(image)

    finaltext = ''
    if isinstance(result[0], list):
        for i in range(len(result[0])):
            text = result[0][i][1][0]
            finaltext += ' ' + text
    return finaltext
