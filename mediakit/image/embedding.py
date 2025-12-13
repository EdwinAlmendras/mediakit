"""
Image embedding generation using CLIP.
"""
import os
from pathlib import Path
from typing import Optional, List
import logging

try:
    import clip
    import torch
    from PIL import Image
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    clip = None
    torch = None
    Image = None

logger = logging.getLogger(__name__)


class ImageEmbeddingGenerator:
    """
    Generate image embeddings using CLIP (ViT-B/32).
    
    Uses CLIP to generate normalized embeddings for image similarity search.
    """
    
    def __init__(self, model_name: str = "ViT-B/32", device: Optional[str] = None):
        """
        Initialize CLIP model.
        
        Args:
            model_name: CLIP model name (default: "ViT-B/32")
            device: Device to use ("cuda", "cpu", or None for auto-detect)
        """
        if not CLIP_AVAILABLE:
            raise ImportError(
                "CLIP is not available. Install with: pip install git+https://github.com/openai/CLIP.git"
            )
        
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model = None
        self._preprocess = None
        self._loaded = False
    
    def _load_model(self):
        """Lazy load CLIP model."""
        if self._loaded:
            return
        
        logger.info(f"Loading CLIP model '{self.model_name}' on device '{self.device}'...")
        self._model, self._preprocess = clip.load(self.model_name, device=self.device)
        self._model.eval()  # Set to evaluation mode
        self._loaded = True
        logger.info("CLIP model loaded successfully")
    
    def generate_embedding(self, image_path: Path) -> Optional[List[float]]:
        """
        Generate normalized embedding for an image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Normalized embedding vector (list of floats) or None on error
        """
        if not CLIP_AVAILABLE:
            logger.error("CLIP is not available")
            return None
        
        if not image_path.exists():
            logger.error(f"Image file does not exist: {image_path}")
            return None
        
        try:
            # Lazy load model
            self._load_model()
            
            # Load and preprocess image
            with Image.open(image_path) as pil_image:
                # Convert to RGB if needed
                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")
                
                # Preprocess image
                image_tensor = self._preprocess(pil_image).unsqueeze(0).to(self.device)
            
            # Generate embedding
            with torch.no_grad():
                image_features = self._model.encode_image(image_tensor)
                # Normalize the embedding (L2 normalization)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                # Convert to CPU and numpy, then to list
                embedding = image_features.cpu().numpy()[0].tolist()
            
            logger.debug(f"Generated embedding for {image_path.name} (dimension: {len(embedding)})")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding for {image_path}: {e}", exc_info=True)
            return None
    
    def generate_embedding_batch(self, image_paths: List[Path]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple images (batch processing).
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            List of embeddings (None for failed images)
        """
        if not CLIP_AVAILABLE:
            logger.error("CLIP is not available")
            return [None] * len(image_paths)
        
        try:
            # Lazy load model
            self._load_model()
            
            # Load and preprocess all images
            image_tensors = []
            valid_indices = []
            
            for idx, image_path in enumerate(image_paths):
                if not image_path.exists():
                    logger.warning(f"Image file does not exist: {image_path}")
                    continue
                
                try:
                    with Image.open(image_path) as pil_image:
                        if pil_image.mode != "RGB":
                            pil_image = pil_image.convert("RGB")
                        image_tensor = self._preprocess(pil_image).to(self.device)
                        image_tensors.append(image_tensor)
                        valid_indices.append(idx)
                except Exception as e:
                    logger.warning(f"Error loading image {image_path}: {e}")
                    continue
            
            if not image_tensors:
                return [None] * len(image_paths)
            
            # Batch process
            batch_tensor = torch.stack(image_tensors)
            
            with torch.no_grad():
                image_features = self._model.encode_image(batch_tensor)
                # Normalize embeddings
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                # Convert to CPU and numpy
                embeddings = image_features.cpu().numpy().tolist()
            
            # Map back to original indices
            result = [None] * len(image_paths)
            for i, idx in enumerate(valid_indices):
                result[idx] = embeddings[i]
            
            logger.debug(f"Generated {len(embeddings)} embeddings in batch")
            return result
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}", exc_info=True)
            return [None] * len(image_paths)
    
    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings generated by this model."""
        if not self._loaded:
            self._load_model()
        # ViT-B/32 produces 512-dimensional embeddings
        return 512
