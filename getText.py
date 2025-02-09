from paddleocr import PaddleOCR

def ocr_with_paddle(image):
    ocr = PaddleOCR(
        lang='en',
        use_angle_cls=True,
        det_model_dir="textModel/en_PP-OCRv3_det_infer",
        rec_model_dir="textModel/en_PP-OCRv4_rec_infer",
        cls_model_dir="textModel/ch_ppocr_mobile_v2.0_cls_infer"
    )

    result = ocr.ocr(image)

    finaltext = ''
    if isinstance(result[0], list):
        for i in range(len(result[0])):
            text = result[0][i][1][0]
            finaltext += ' ' + text
    return finaltext
