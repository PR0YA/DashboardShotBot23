import cv2
import numpy as np
from PIL import Image, ImageEnhance
import io
import logging

logger = logging.getLogger(__name__)

class ImageEnhancer:
    def enhance_screenshot(self, image_data: bytes, clip_limit: float = 0.8, 
                         sharpness: float = 3.4) -> bytes:
        """
        Улучшает скриншот с использованием настраиваемых параметров.

        Args:
            image_data (bytes): Исходные данные изображения
            clip_limit (float): Предел CLAHE для улучшения контраста
            sharpness (float): Интенсивность повышения резкости
        """
        try:
            # Конвертируем bytes в numpy array
            image_array = np.frombuffer(image_data, np.uint8)
            # Декодируем изображение
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            # Конвертируем в цветовое пространство RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Минимальное подавление шума с уменьшенными параметрами
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 2, 2, 3, 5)

            # Улучшение контраста с пользовательским clipLimit
            lab = cv2.cvtColor(denoised, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8,8))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl,a,b))
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)

            # Настраиваемая интенсивность повышения резкости
            kernel = np.array([[-0.3,-0.3,-0.3],
                             [-0.3, sharpness,-0.3],
                             [-0.3,-0.3,-0.3]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            # Конвертируем обратно в BGR для OpenCV
            final = cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR)

            # Конвертируем в bytes
            success, buffer = cv2.imencode('.png', final)
            if not success:
                raise ValueError("Failed to encode enhanced image")

            logger.info(f"Successfully enhanced image with clip_limit={clip_limit}, sharpness={sharpness}")
            return buffer.tobytes()

        except Exception as e:
            logger.error(f"Error in enhance_screenshot: {str(e)}")
            return image_data  # Возвращаем оригинальное изображение в случае ошибки