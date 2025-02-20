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
        Optimized for preserving text clarity and chart details.
        """
        try:
            # Convert bytes to numpy array
            image_array = np.frombuffer(image_data, np.uint8)
            # Decode image
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            # Apply enhancements directly without quality check
            enhanced_image = ImageEnhancer._apply_optimal_enhancements(image)

            # Convert back to bytes
            success, buffer = cv2.imencode('.png', enhanced_image)
            if not success:
                raise ValueError("Failed to encode enhanced image")

            return buffer.tobytes()

        except Exception as e:
            logger.error(f"Error enhancing image: {str(e)}")
            return image_data  # Return original image if enhancement fails

    @staticmethod
    def _apply_optimal_enhancements(image: np.ndarray) -> np.ndarray:
        """
        Applies optimized enhancements for better clarity and reduced brightness.
        """
        try:
            # Convert to RGB color space
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Minimal denoising with reduced parameters
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 2, 2, 3, 5)

            # Contrast enhancement with reduced clipLimit
            lab = cv2.cvtColor(denoised, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=0.8, tileGridSize=(8,8))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl,a,b))
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

            # Increased sharpening for better text clarity
            kernel = np.array([[-0.3,-0.3,-0.3],
                             [-0.3, 3.4,-0.3],
                             [-0.3,-0.3,-0.3]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            # Convert back to BGR for OpenCV
            final = cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR)

            logger.info("Successfully applied optimized enhancements to the image")
            return final

        except Exception as e:
            logger.error(f"Error in _apply_optimal_enhancements: {str(e)}")
            return image  # Return original image if enhancement fails