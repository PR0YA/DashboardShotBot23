import cv2
import numpy as np
from PIL import Image, ImageEnhance
import io
from utils.logger import logger

class ImageEnhancer:
    @staticmethod
    def enhance_screenshot(image_data: bytes) -> bytes:
        """
        Enhances the screenshot using AI-powered image processing techniques.

        Args:
            image_data (bytes): Original screenshot image data

        Returns:
            bytes: Enhanced image data
        """
        try:
            # Convert bytes to numpy array
            image_array = np.frombuffer(image_data, np.uint8)
            # Decode image
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            # Apply enhancements
            enhanced_image = ImageEnhancer._apply_enhancements(image)

            # Convert back to bytes
            success, buffer = cv2.imencode('.png', enhanced_image)
            if not success:
                raise ValueError("Failed to encode enhanced image")

            return buffer.tobytes()

        except Exception as e:
            logger.error(f"Error enhancing image: {str(e)}")
            return image_data  # Return original image if enhancement fails

    @staticmethod
    def _apply_enhancements(image: np.ndarray) -> np.ndarray:
        """
        Applies various AI-powered enhancements to the image.
        Optimized for text clarity and chart visibility.
        """
        try:
            # Convert to RGB color space
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # 1. Gentle denoising with reduced strength
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 5, 5, 3, 9)

            # 2. Enhance contrast using CLAHE with optimized parameters
            lab = cv2.cvtColor(denoised, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4,4))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl,a,b))
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

            # 3. Apply moderate sharpening
            kernel = np.array([[-0.5,-0.5,-0.5],
                             [-0.5, 5.0,-0.5],
                             [-0.5,-0.5,-0.5]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            # Convert back to BGR for OpenCV
            final = cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR)

            logger.info("Successfully applied optimized AI enhancements to the image")
            return final

        except Exception as e:
            logger.error(f"Error in _apply_enhancements: {str(e)}")
            return image  # Return original image if enhancement fails