"""
## Module: imageEmbedder

### Description

Provides image embedding capabilities for the Deep Researcher application
using a SigLIP vision model exported to ONNX format. This module handles
loading images (including SVG and animated formats), preprocessing them
to match the model's expected input, and generating normalized embedding
vectors suitable for similarity search and retrieval tasks.

### Key Components

- **SigLIPEmbedder class**: Main interface for loading images and generating embeddings.
- **_log_image_embed_event function**: Internal logging utility for image embedding operations.

### Usage Example

```python
from main.src.utils.core.ai.imageEmbedder import SigLIPEmbedder

embedder = SigLIPEmbedder()
vector = embedder.embed("path/to/image.png")
print("Embedding dimension:", len(vector))
```

### Dependencies

- `onnxruntime`: For running the SigLIP ONNX model.
- `Pillow (PIL)`: For image loading, conversion, and resizing.
- `numpy`: For numerical preprocessing and normalization.
- `DRLogger`: Custom logging utility for structured event logging.
- `version_constants`: Provides application version information.
"""

import io
import numpy as np
from PIL import Image
import onnxruntime as ort
from pathlib import Path
from typing import Literal, List
from main.src.utils.DRLogger import dr_logger
from main.src.utils.version_constants import get_raw_version

DIR = Path(__file__).parent
MODEL_PATH = DIR / "models" / "vision_model_fp16.onnx"

MAX_RESOLUTION = 1024
LOG_SOURCE = "system"  # log source for all events in this module

_session = None  # global cached session


def _log_image_embed_event(
    message: str,
    level: Literal["success", "error", "warning", "info"] = "info",
    urgency: Literal["none", "moderate", "critical"] = "none",
):
    """
    ## Description

    Internal utility function for logging image embedding events with structured
    metadata. Ensures all embedding-related operations are tracked with appropriate
    urgency levels and log sources.

    ## Parameters

    - `message` (`str`)
      - Description: Human-readable description of the image embedding event.
      - Constraints: Must be non-empty.
      - Example: "ONNX session initialized successfully."

    - `level` (`Literal["success", "error", "warning", "info"]`, optional)
      - Description: Log severity level indicating the nature of the event.
      - Constraints: Must be one of: "success", "error", "warning", "info".
      - Default: "info"
      - Example: "error"

    - `urgency` (`Literal["none", "moderate", "critical"]`, optional)
      - Description: Priority indicator for the logged event.
      - Constraints: Must be one of: "none", "moderate", "critical".
      - Default: "none"
      - Example: "critical"

    ## Returns

    `None`

    ## Side Effects

    - Writes log entry to the DRLogger system.
    - Includes application version in all log entries.
    - Routes logs to the "UTILS" module table.

    ## Debug Notes

    - Use appropriate urgency levels: "critical" for model loading failures,
      "moderate" for non-fatal warnings.
    - Check logger output in the `utils_logs` table.

    ## Customization

    To change log source globally, modify the module-level constant:
    - `LOG_SOURCE`: Change from "system" to custom value.
    """
    dr_logger.log(
        log_type=level,
        message=message,
        origin=LOG_SOURCE,
        urgency=urgency,
        module="UTILS",
        app_version=get_raw_version(),
    )


class SigLIPEmbedder:
    """
    ## Description

    Wraps a SigLIP vision model (ONNX format) to produce normalized image
    embeddings. The ONNX inference session is lazily initialized and cached
    globally so that subsequent instantiations reuse the same loaded model,
    avoiding redundant memory allocation.

    ## Parameters

    - `model_path` (`Path`, optional)
      - Description: File-system path to the ONNX model file.
      - Constraints: Must point to a valid `.onnx` file.
      - Default: `vision_model_fp16.onnx` located in the `models/` subdirectory.

    ## Returns

    `None`
    Instantiates an object.

    ## Raises

    - `Exception`
      - When the ONNX model file cannot be loaded or session creation fails.

    ## Side Effects

    - Initializes a global `_session` on first instantiation.
    - Logs model loading events to the DRLogger system.

    ## Debug Notes

    - Verify that `vision_model_fp16.onnx` exists in the `models/` directory.
    - Check `utils_logs` table for session initialization errors.

    ## Customization

    - Pass a different `model_path` to use an alternative ONNX model.
    - Adjust `intra_op_num_threads` inside `__init__` for CPU parallelism.
    """

    def __init__(self, model_path=MODEL_PATH):
        """
        ## Description

        Initializes the SigLIP embedder by loading the ONNX model into a
        cached inference session. If the session already exists globally,
        it is reused without reloading the model.

        ## Parameters

        - `model_path` (`Path`, optional)
          - Description: Path to the ONNX vision model file.
          - Constraints: Must be a valid file path to an `.onnx` model.
          - Default: `MODEL_PATH` (module-level constant).

        ## Returns

        `None`

        ## Raises

        - `Exception`
          - When ONNX runtime fails to create an inference session.

        ## Side Effects

        - Sets the global `_session` variable on first call.
        - Caches session reference in `self.session`.
        - Caches input tensor name in `self.input_name`.
        - Logs session creation and reuse events.

        ## Debug Notes

        - If loading fails, check ONNX runtime version compatibility.
        - Monitor memory after initialization for large models.

        ## Customization

        Adjust session options (graph optimization, thread count) inside
        this method to tune inference performance.
        """
        global _session

        if _session is None:
            _log_image_embed_event(f"Loading ONNX model from {model_path}.")

            try:
                opts = ort.SessionOptions()
                opts.graph_optimization_level = (
                    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                )
                opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                opts.intra_op_num_threads = 2

                _session = ort.InferenceSession(
                    str(model_path),
                    providers=["CPUExecutionProvider"],
                    sess_options=opts,
                )

                _log_image_embed_event(
                    "ONNX inference session created successfully.",
                    level="success",
                )
            except Exception as e:
                _log_image_embed_event(
                    f"Failed to create ONNX inference session. Error: {str(e)}",
                    level="error",
                    urgency="critical",
                )
                raise
        else:
            _log_image_embed_event("Reusing cached ONNX inference session.")

        self.session = _session
        self.input_name = self.session.get_inputs()[0].name

        _log_image_embed_event(
            f"SigLIPEmbedder initialized. Input tensor name: '{self.input_name}'.",
            level="success",
        )

    def _load_image(self, path: str) -> Image.Image:
        """
        ## Description

        Loads an image from disk, handling SVG conversion, animated frame
        selection, RGB conversion, and resolution capping. Returns a PIL
        Image ready for preprocessing.

        ## Parameters

        - `path` (`str`)
          - Description: File-system path to the image to load.
          - Constraints: Must be a valid path to a supported image format
            (PNG, JPEG, WEBP, GIF, SVG, etc.).
          - Example: "C:/images/photo.jpg"

        ## Returns

        `Image.Image`

        A PIL RGB image with its longest side capped at `MAX_RESOLUTION` (1024).

        ## Raises

        - `FileNotFoundError`
          - When the image file does not exist at the given path.
        - `Exception`
          - When SVG conversion or image decoding fails.

        ## Side Effects

        - May import `cairosvg` lazily for SVG files.
        - Logs each loading step and any errors.

        ## Debug Notes

        - For SVG issues, ensure `cairosvg` is installed.
        - For animated images, only the first frame is used.

        ## Customization

        Change `MAX_RESOLUTION` at module level to allow larger input images.
        """
        _log_image_embed_event(f"Loading image from path: {path}")

        try:
            if path.lower().endswith(".svg"):
                _log_image_embed_event(
                    "Detected SVG format. Converting to PNG via cairosvg."
                )
                import cairosvg

                png = cairosvg.svg2png(url=path)
                img = Image.open(io.BytesIO(png))
                _log_image_embed_event(
                    "SVG converted to PNG successfully.", level="success"
                )
            else:
                img = Image.open(path)
                _log_image_embed_event(
                    f"Image opened successfully. Format: {img.format}."
                )

            if getattr(img, "is_animated", False):
                _log_image_embed_event(
                    "Animated image detected. Selecting first frame."
                )
                img.seek(0)

            img = img.convert("RGB")

            w, h = img.size
            _log_image_embed_event(f"Original image size: {w}x{h}.")

            if max(w, h) > MAX_RESOLUTION:
                scale = MAX_RESOLUTION / max(w, h)
                new_w, new_h = int(w * scale), int(h * scale)
                img = img.resize((new_w, new_h), Image.LANCZOS)
                _log_image_embed_event(
                    f"Image downscaled to {new_w}x{new_h} (max resolution: {MAX_RESOLUTION})."
                )

            _log_image_embed_event(
                "Image loaded and prepared successfully.", level="success"
            )
            return img

        except Exception as e:
            _log_image_embed_event(
                f"Failed to load image at '{path}'. Error: {str(e)}",
                level="error",
                urgency="critical",
            )
            raise

    def _preprocess(self, img: Image.Image) -> np.ndarray:
        """
        ## Description

        Preprocesses a PIL image into a normalized float32 tensor suitable
        for the SigLIP ONNX model. Resizes to 224x224, scales pixel values
        to [0, 1], applies ImageNet-style mean/std normalization, and
        rearranges axes to NCHW format.

        ## Parameters

        - `img` (`Image.Image`)
          - Description: A PIL RGB image to preprocess.
          - Constraints: Must be an RGB image (3 channels).
          - Example: Output of `_load_image()`.

        ## Returns

        `np.ndarray`

        Structure:

        ```json
        {
            "shape": [1, 3, 224, 224],
            "dtype": "float32"
        }
        ```

        A 4-D tensor in NCHW format with normalized pixel values.

        ## Raises

        - `Exception`
          - When resizing or array conversion fails.

        ## Side Effects

        - Logs preprocessing steps and completion status.

        ## Debug Notes

        - Ensure the input image is RGB (3 channels). Grayscale or RGBA
          images will produce incorrect tensor shapes.
        - Normalization constants are from the OpenAI CLIP family.

        ## Customization

        To use a different normalization scheme, update the `mean` and `std`
        arrays to match the target model's training distribution.
        """
        _log_image_embed_event("Starting image preprocessing.")

        try:
            img = img.resize((224, 224), Image.BICUBIC)
            _log_image_embed_event("Image resized to 224x224.")

            arr = np.asarray(img, dtype=np.float32) / 255.0

            mean = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
            std = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

            arr = (arr - mean) / std
            arr = arr.transpose(2, 0, 1)
            arr = np.expand_dims(arr, axis=0)

            _log_image_embed_event(
                f"Preprocessing complete. Tensor shape: {arr.shape}.",
                level="success",
            )
            return arr

        except Exception as e:
            _log_image_embed_event(
                f"Image preprocessing failed. Error: {str(e)}",
                level="error",
                urgency="critical",
            )
            raise

    def embed(self, image_path: str) -> List[float]:
        """
        ## Description

        End-to-end pipeline that loads an image, preprocesses it, runs
        inference through the SigLIP ONNX model, and returns a unit-length
        embedding vector.

        ## Parameters

        - `image_path` (`str`)
          - Description: File-system path to the image to embed.
          - Constraints: Must be a valid path to a supported image format.
          - Example: "C:/images/photo.jpg"

        ## Returns

        `List[float]`

        Structure:

        ```json
        {
            "type": "list",
            "element_type": "float",
            "length": 768,
            "description": "Unit-normalized embedding vector."
        }
        ```

        A list of floats representing the L2-normalized image embedding.

        ## Raises

        - `FileNotFoundError`
          - When the image file does not exist.
        - `Exception`
          - When image loading, preprocessing, or model inference fails.

        ## Side Effects

        - Loads and preprocesses the image in memory.
        - Runs ONNX model inference on CPU.
        - Logs each pipeline stage and the final embedding dimension.

        ## Debug Notes

        - Check logs for the specific stage that failed.
        - Verify embedding dimension matches expected model output (typically 768).

        ## Customization

        To return a numpy array instead of a list, modify the last return statement.
        """
        _log_image_embed_event(f"Starting embedding pipeline for: {image_path}")

        try:
            img = self._load_image(image_path)

            tensor = self._preprocess(img)

            _log_image_embed_event("Running ONNX model inference.")
            embedding = self.session.run(None, {self.input_name: tensor})[0][0]
            _log_image_embed_event(
                f"Inference complete. Raw embedding dimension: {len(embedding)}.",
                level="success",
            )

            embedding /= np.linalg.norm(embedding)
            _log_image_embed_event("Embedding L2-normalized.")

            result = embedding.tolist()

            _log_image_embed_event(
                f"Embedding pipeline complete. Final vector length: {len(result)}.",
                level="success",
            )
            return result

        except Exception as e:
            _log_image_embed_event(
                f"Embedding pipeline failed for '{image_path}'. Error: {str(e)}",
                level="error",
                urgency="critical",
            )
            raise


# Usage example
# if __name__ == "__main__":

#     model = SigLIPEmbedder()

#     vec = model.embed(r"C:\Users\ranaw\Downloads\unnamed (1).jpg")
#     vec2 = model.embed(r"C:\Users\ranaw\Downloads\unnamed (1).jpg")
#     vec3 = model.embed(r"C:\Users\ranaw\Downloads\unnamed (1).jpg")

#     print("Embedding dimension:", len(vec))
#     print(vec[:10])
#     print("Embedding dimension:", len(vec2))
#     print(vec2[:10])
#     print("Embedding dimension:", len(vec3))
#     print(vec3[:10])
