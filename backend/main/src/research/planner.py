from .gemini_client import GeminiClient
from .models import ResearchPlan, ResearchStep

class ResearchPlanner:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def create_plan(self, query: str, context: str = None) -> ResearchPlan:
        system_instruction = """
        You are a Research Planner. Break down the user's research query into a logical sequence of steps.
        Each step should be actionable.
        Return a JSON object matching the ResearchPlan structure.
        """

        prompt = f"""
        User Query: {query}
        Context: {context or 'None'}
        
        Generate a multi-step research plan.
        """

        plan_data = await self.gemini.generate_structured_response(
            "gemini-3.1-pro-preview",
            prompt,
            system_instruction
        )

        steps = []
        for idx, s in enumerate(plan_data.get("steps", [])):
            desc = s.get("description") if isinstance(s, dict) else s
            steps.append(ResearchStep(
                id=f"step_{idx + 1}",
                description=desc,
                status="pending"
            ))

        return ResearchPlan(
            title=plan_data.get("title", "Research Plan"),
            steps=steps
        )
