import json
from pathlib import Path

DIR = Path(__file__).parent


def getImageUnderstandingSchema():
    """
    Returns the JSON schema for the image understanding API.

    The returned dictionary describes the structure of objects expected for image analysis tasks, with keys and example values as follows:

    Example output:
        {
            "title": "Title for the image",
            "description": "Description for the image under 100 words",
            "tags": ["tags", "related", "to", "the", "image"],
            "colors": [
                {
                    "color": "color name",
                    "percentage": "percentage of the color in the image"
                },
                {
                    "color": "color name 2",
                    "percentage": "percentage of the color in the image"
                }
            ],
            "objects": [
                "objects",
                "inside",
                "to",
                "the",
                "image"
            ]
        }

    Returns:
        dict: The image_understanding schema loaded from the corresponding JSON file.
    """
    jsonschema = json.load(open(DIR / "json" / "schemas.json"))
    return jsonschema["image_understanding"]

