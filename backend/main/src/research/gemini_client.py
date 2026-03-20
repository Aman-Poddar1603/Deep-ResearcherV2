import os
import json
import google.generativeai as genai
from typing import Optional

class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")
        genai.configure(api_key=api_key)

    async def generate_structured_response(self, model_name: str, prompt: str, system_instruction: Optional[str] = None):
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        
        try:
            return json.loads(response.text)
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            return {}

    async def reason(self, model_name: str, prompt: str, system_instruction: Optional[str] = None):
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        response = await model.generate_content_async(prompt)
        return response.text
