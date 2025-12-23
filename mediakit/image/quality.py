import numpy as np
import time

JPEG_LUMA_BASE = np.array([
    16,11,10,16,24,40,51,61,
    12,12,14,19,26,58,60,55,
    14,13,16,24,40,57,69,56,
    14,17,22,29,51,87,80,62,
    18,22,37,56,68,109,103,77,
    24,35,55,64,81,104,113,92,
    49,64,78,87,103,121,120,101,
    72,92,95,98,112,100,103,99
], dtype=np.float32)

# Pre-calcular el inverso para multiplicación más rápida
JPEG_LUMA_BASE_INV = (100.0 / JPEG_LUMA_BASE).astype(np.float32)

def estimate_quality(jpeg_table):
    # Convertir a float32 una sola vez si no es array
    if not isinstance(jpeg_table, np.ndarray):
        jpeg_table = np.array(jpeg_table, dtype=np.float32)
    else:
        jpeg_table = jpeg_table.astype(np.float32, copy=False)

    # Multiplicación es más rápida que división
    scales = jpeg_table * JPEG_LUMA_BASE_INV
    scale = np.median(scales)

    # Guard against division by zero
    if scale <= 0:
        return 100
    
    # Optimizar cálculo de quality
    if scale <= 100:
        quality = 100.0 - scale * 0.5
    else:
        quality = 5000.0 / scale

    return int(round(np.clip(quality, 1, 100)))
