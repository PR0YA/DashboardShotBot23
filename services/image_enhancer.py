import cv2
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ImageEnhancer:
    @staticmethod
    async def enhance_image(image_data: bytes) -> Optional[bytes]:
        """Улучшение качества изображения"""
        try:
            # Конвертируем bytes в numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Применяем улучшение контраста
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl,a,b))
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

            # Применяем увеличение резкости
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)

            # Кодируем обратно в bytes
            success, buffer = cv2.imencode('.png', enhanced)
            if not success:
                raise ValueError("Failed to encode enhanced image")

            return buffer.tobytes()

        except Exception as e:
            logger.error(f"Error enhancing image: {e}")
            return None