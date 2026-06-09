import cv2
from pathlib import Path
from paddleocr import TextImageUnwarping, PaddleOCR
import numpy as np


"""
This file is related to preprocessing, which includes:
- Document unwarping (PaddleOCR)
- Upscaling (cv2)
- Grayscale Conversion (cv2)
- Binary Conversion (cv2)
- Morphology Dilation (cv2)
- Morphology Opening (cv2)
- OCR (PaddleOCR)
"""


"""
This is the main function that you will use.
It expects an array of strings which represents paths of receipt images

Returns:
- path for each json files of receipts
"""
def preprocess_receipt(paths):

    if not paths:
        return None

    unwarped = document_unwarping(paths)
    preprocessed = document_preprocess(unwarped)
    output = document_OCR(preprocessed)

    return output

"""
This function unwarps receipt image for better image preprocessing via PaddleOCR

Returns:
- Unwarped receipt image(s)
"""
# source: https://huggingface.co/PaddlePaddle/UVDoc
def document_unwarping(paths):
    Path("./temp/unwarped/").mkdir(parents=True, exist_ok=True)
    
    model = TextImageUnwarping(model_name="UVDoc")
    unwarped_paths = []

    for path in paths:
        output = model.predict(path, batch_size=1)
        for res in output:
            save_path = f"./temp/unwarped/{Path(path).stem}.png"
            res.save_to_img(save_path=save_path)
            unwarped_paths.append(save_path)
    
    return unwarped_paths


"""
This function executes image operations onto unwarped documents
- Upscaling (cv2)
- Grayscale Conversion (cv2)
- Binary Conversion (cv2)
- Morphology Dilation (cv2)
- Morphology Opening (cv2)

Returns:
- preprocessed documents image(s)
"""
def document_preprocess(paths):
    Path("./temp/preprocessed/").mkdir(parents=True, exist_ok=True)  
    preprocessed_paths = []

    for path in paths:

        # Read image with path
        image = cv2.imread(path)
        image = upscale(image, target_height=2000)

        # Convert to grayscale then binary
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, image = cv2.threshold(image, 160, 255, cv2.THRESH_BINARY)

        # Invert the binary pixels first
        image = cv2.bitwise_not(image)

        # Morphology
        image = cv2.morphologyEx(image, cv2.MORPH_OPEN, np.ones((2,2),np.uint8), iterations= 1)

        # Invert again
        image = cv2.bitwise_not(image)

        # Define save path
        save_path = f"./temp/preprocessed/{Path(path).stem}.png"
        
        # Save the image
        cv2.imwrite(str(save_path), image)
        
        # Store the path
        preprocessed_paths.append(str(save_path))

    return preprocessed_paths

"""
Just a helper function
To upscale images
OCR works better with appropriate sized images (around 300 DPI)
"""
def upscale(image, target_height=2000, method=cv2.INTER_LANCZOS4):
    """
    Upscale image optimally
    """
    height, width = image.shape[:2]

    if height >= target_height:
        print(f"Image already adequate at {height}px tall")
        return image

    scale = target_height / height
    new_width = int(width * scale)
    new_height = int(height * scale)

    upscaled = cv2.resize(image, (new_width, new_height),
                          interpolation=method)

    return upscaled


"""
This function operated OCR via PaddleOCR

Returns:
- json file for all receipt image(s)
- receipt image(s) with bounding boxes on detected texts
"""
def document_OCR(paths):
    Path("./temp/output/").mkdir(parents=True, exist_ok=True)  
    json_paths = []

    # Instantiate OCR model
    ocr = PaddleOCR(
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="en_PP-OCRv5_mobile_rec",
        use_doc_orientation_classify=True,
        use_doc_unwarping=False,
        use_textline_orientation=True,
        device="cpu",
        lang="en"
    ) 

    #
    for path in paths:

        result = ocr.predict(path)  
        for res in result:  
            res.print()  
            res.save_to_img(f"./temp/output/image/{Path(path).stem}.png")  
            res.save_to_json(f"./temp/output/json/{Path(path).stem}.json")

            json_paths.append(f"./temp/output/json/{Path(path).stem}.json")
    
    return json_paths


"""
Run the program to
Test the code here
"""
if __name__ == "__main__":

    # # Get all image paths in images/ folder
    # image_folder = Path("../../Receipt_Dataset/fullDataset/images")
    # image_paths = list(image_folder.glob("*"))  # All files

    # # OR filter by extensions
    # image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff"]
    # image_paths = []
    # for ext in image_extensions:
    #     image_paths.extend(image_folder.glob(ext))

    # # Convert to strings if needed
    # image_paths = [str(path) for path in image_paths]


    preprocess_receipt(image_paths)
