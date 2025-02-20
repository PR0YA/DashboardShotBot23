import cv2
import numpy as np
from PIL import Image, ImageEnhance
import io
from utils.logger import logger

class ImageEnhancer:
    def enhance_screenshot(self, image_data: bytes, clip_limit: float = 0.8, 
                         sharpness: float = 3.4) -> bytes:
        """
        Enhances the screenshot using customizable parameters.

        Args:
            image_data (bytes): Original screenshot data
            clip_limit (float): CLAHE clip limit for contrast enhancement
            sharpness (float): Sharpening intensity
        """
        try:
            # Convert bytes to numpy array
            image_array = np.frombuffer(image_data, np.uint8)
            # Decode image
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            # Convert to RGB color space
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Minimal denoising with reduced parameters
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 2, 2, 3, 5)

            # Contrast enhancement with custom clipLimit
            lab = cv2.cvtColor(denoised, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8,8))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl,a,b))
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

            # Custom sharpening intensity
            kernel = np.array([[-0.3,-0.3,-0.3],
                             [-0.3, sharpness,-0.3],
                             [-0.3,-0.3,-0.3]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            # Convert back to BGR for OpenCV
            final = cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR)

            # Convert to bytes
            success, buffer = cv2.imencode('.png', final)
            if not success:
                raise ValueError("Failed to encode enhanced image")

            logger.info(f"Successfully enhanced image with clip_limit={clip_limit}, sharpness={sharpness}")
            return buffer.tobytes()

        except Exception as e:
            logger.error(f"Error in enhance_screenshot: {str(e)}")
            return image_data  # Return original image if enhancement fails