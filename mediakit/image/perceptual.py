"""
Perceptual image features: pHash and average color (LAB).
"""
from pathlib import Path
from typing import Optional, Tuple, List
import logging

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    imagehash = None

try:
    from PIL import Image
    import numpy as np
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    Image = None
    np = None

logger = logging.getLogger(__name__)


import cv2
import numpy as np
from PIL import Image
from imagehash import ImageHash

def fast_phash(img, hash_size=8, highfreq_factor=4):
    # Convertir imagen a escala de grises
    img = img.convert('L')
    
    # Redimensionar la imagen
    img_size = hash_size * highfreq_factor
    img.thumbnail((img_size, img_size))
    
    # Convertir a un array de NumPy para optimizar operaciones
    pixels = np.array(img, dtype=np.float32)

    # Aplicar la DCT de manera eficiente con OpenCV y NumPy
    dct = cv2.dct(pixels)
    dct_lowfreq = dct[:hash_size, :hash_size]  # Coeficientes de baja frecuencia

    # Obtener la mediana para comparar
    med = np.median(dct_lowfreq)
    diff = dct_lowfreq > med
    
    # Convertir el resultado a un hash binario
    return ImageHash(diff)



def calculate_phash(image_path: Path = None, image: Image.Image = None) -> Optional[str]:
    """
    Calculate perceptual hash (pHash) for an image.
    
    pHash is useful for near-duplicate detection and similarity search.
    Returns a hexadecimal string representation of the hash.
    
    Args:
        image_path: Path to image file (optional if image is provided)
        image: PIL Image object (optional, if provided will use this instead of opening file)
        
    Returns:
        Hexadecimal string of pHash (64 characters for 8x8 hash) or None on error
    """
    if not IMAGEHASH_AVAILABLE:
        logger.warning("imagehash library not available. Install with: pip install imagehash")
        return None
    
    if not PILLOW_AVAILABLE:
        logger.warning("PIL/Pillow not available")
        return None
    
    try:
        # Use provided image if available, otherwise open from path
        if image is not None:
            # Use provided image directly
            img = image.copy() if hasattr(image, 'copy') else image
            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")
            # Calculate hash
            hash_obj = fast_phash(img, hash_size=8)
            phash_str = str(hash_obj)
            logger.debug(f"Calculated pHash from image object: {phash_str}")
            return phash_str
        else:
            # Open from path
            if image_path is None or not image_path.exists():
                logger.error(f"Image file does not exist: {image_path}")
                return None
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")
                # Calculate hash (img will be closed after with block, so process it here)
                hash_obj = fast_phash(img, hash_size=8)
                phash_str = str(hash_obj)
                logger.debug(f"Calculated pHash for {image_path.name}: {phash_str}")
                return phash_str
            
    except Exception as e:
        logger.error(f"Error calculating pHash: {e}", exc_info=True)
        return None




def rgb_to_lab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    Convert RGB to LAB color space.
    
    Args:
        r, g, b: RGB values (0-255)
        
    Returns:
        Tuple of (L, a, b) values
    """
    # Normalize RGB to 0-1
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0
    
    # Convert to linear RGB
    def gamma_correct(c):
        if c > 0.04045:
            return ((c + 0.055) / 1.055) ** 2.4
        return c / 12.92
    
    r = gamma_correct(r)
    g = gamma_correct(g)
    b = gamma_correct(b)
    
    # Convert to XYZ (using sRGB matrix)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    
    # Normalize by D65 white point
    x = x / 0.95047
    z = z / 1.08883
    
    # Convert to LAB
    def f(t):
        if t > 0.008856:
            return t ** (1.0/3.0)
        return (7.787 * t) + (16.0/116.0)
    
    fx = f(x)
    fy = f(y)
    fz = f(z)
    
    L = (116.0 * fy) - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    
    return (L, a, b)


def calculate_avg_color_lab(image_path: Path = None, image: Image.Image = None) -> Optional[List[float]]:
    """
    Calculate average color in LAB color space.
    
    LAB is perceptually uniform, making it ideal for color-based filtering.
    Returns [L, a, b] where:
    - L: Lightness (0-100)
    - a: Green-Red axis (-128 to 127)
    - b: Blue-Yellow axis (-128 to 127)
    
    Args:
        image_path: Path to image file (optional if image is provided)
        image: PIL Image object (optional, if provided will use this instead of opening file)
        
    Returns:
        List of [L, a, b] values or None on error
    """
    if not PILLOW_AVAILABLE:
        logger.warning("PIL/Pillow not available")
        return None
    
    try:
        # Use provided image if available, otherwise open from path
        if image is not None:
            # Use provided image directly
            img = image.copy() if hasattr(image, 'copy') else image
            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")
            # If image is already small (like a thumbnail), no need to resize
            if max(img.size) > 200:
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            
            # Get pixel data as numpy array
            pixels = np.array(img)
            h, w = pixels.shape[:2]
            
            # Calculate average RGB
            avg_r = np.mean(pixels[:, :, 0])
            avg_g = np.mean(pixels[:, :, 1])
            avg_b = np.mean(pixels[:, :, 2])
            
            # Convert to LAB
            L, a, b = rgb_to_lab(avg_r, avg_g, avg_b)
            
            # Round to 2 decimal places
            lab = [round(L, 2), round(a, 2), round(b, 2)]
            
            logger.debug(f"Calculated avg_color LAB from image object: {lab}")
            return lab
        else:
            # Open from path
            if image_path is None or not image_path.exists():
                logger.error(f"Image file does not exist: {image_path}")
                return None
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Resize to smaller size for faster processing (keep aspect ratio)
                max_size = 200
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Get pixel data as numpy array
                pixels = np.array(img)
                h, w = pixels.shape[:2]
                
                # Calculate average RGB
                avg_r = np.mean(pixels[:, :, 0])
                avg_g = np.mean(pixels[:, :, 1])
                avg_b = np.mean(pixels[:, :, 2])
                
                # Convert to LAB
                L, a, b = rgb_to_lab(avg_r, avg_g, avg_b)
                
                # Round to 2 decimal places
                lab = [round(L, 2), round(a, 2), round(b, 2)]
                
                logger.debug(f"Calculated avg_color LAB for {image_path.name}: {lab}")
                return lab
            
    except Exception as e:
        logger.error(f"Error calculating avg_color LAB: {e}", exc_info=True)
        return None
