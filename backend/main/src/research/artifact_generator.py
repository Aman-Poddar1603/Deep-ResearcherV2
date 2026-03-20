from .gemini_client import GeminiClient
from .models import Artifact


class ArtifactGenerator:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def generate(
        self, query: str, findings: list, videos: list, images: list
    ) -> Artifact:
        system_instruction = """
        You are a Research Artifact Generator.
        Your goal is to produce a HIGH-VALUE, structured deliverable based on research findings.

        CRITICAL: You must also generate a 'markdown_content' field which is a PURE MARKDOWN FILE.
        The markdown MUST include:
        - A clear title and summary
        - Key insights as a bulleted list
        - Detailed sections with headings
        - Embedded YouTube videos (using markdown links)
        - Multiple images (using markdown image syntax)
        - Highlighted content (using > blockquotes or **bolding**)
        - A sources section

        Return a JSON object matching the Artifact structure.
        """

        prompt = f"""
        Original Query: {query}
        Research Findings: {findings}
        Relevant Videos: {videos}
        Relevant Images: {images}

        Generate the artifact. Ensure the 'markdown_content' is comprehensive and ready-to-use.
        """

        artifact_data = await self.gemini.generate_structured_response(
            "gemini-3.1-pro-preview", prompt, system_instruction
        )

        return Artifact(**artifact_data)
