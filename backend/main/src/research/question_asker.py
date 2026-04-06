from .gemini_client import GeminiClient
from typing import List, Optional

class QuestionAsker:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def ask_clarifying_questions(self, query: str, context: str = None, findings: List[dict] = None) -> List[str]:
        """
        Analyzes current research state and generates questions to keep research on track.
        """
        system_instruction = """
        You are a Research Quality Controller. 
        Your job is to identify ambiguities, missing perspectives, or gaps in the current research.
        Generate 2-3 targeted clarifying questions that would help refine the research direction.
        Return a JSON object with a 'questions' key containing a list of strings.
        """

        prompt = f"""
        Original Query: {query}
        Current Context: {context or 'None'}
        Findings so far: {findings or 'None'}
        
        What questions should we ask the user to ensure the research stays on track and deepens correctly?
        """

        data = await self.gemini.generate_structured_response(
            "gemini-3.1-pro-preview",
            prompt,
            system_instruction
        )

        return data.get("questions", [])
