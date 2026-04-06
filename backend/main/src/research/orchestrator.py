import asyncio
from datetime import datetime
from .redis_manager import RedisManager
from .gemini_client import GeminiClient
from .external_services import ExternalServices
from .planner import ResearchPlanner
from .artifact_generator import ArtifactGenerator
from .question_asker import QuestionAsker
from .db_queue import db_queue
from .models import JobStatus, ResearchStage, RedisEvent

class ResearchOrchestrator:
    def __init__(self, redis: RedisManager, gemini: GeminiClient, services: ExternalServices):
        self.redis = redis
        self.gemini = gemini
        self.services = services
        self.planner = ResearchPlanner(gemini)
        self.artifact_gen = ArtifactGenerator(gemini)
        self.question_asker = QuestionAsker(gemini)

    async def emit(self, job_id: str, stage: ResearchStage, message: str, status: JobStatus = JobStatus.RUNNING, data: dict = None):
        event = RedisEvent(
            job_id=job_id,
            stage=stage,
            status=status,
            message=message,
            data=data
        )
        await self.redis.emit_event(event)
        # Push to DB queue for persistence
        db_queue.push("save_event", job_id, event.dict())

    async def execute(self, job_id: str, input_data: dict):
        try:
            prompt = input_data.get("prompt")
            context = input_data.get("context")

            # 1. Validate
            await self.emit(job_id, ResearchStage.VALIDATING, "Validating query and context...")
            validation = await self.services.validate_query(prompt)
            refined_query = validation.get("refined_query", prompt)

            # 2. Planning & Clarification
            await self.emit(job_id, ResearchStage.PLANNING, "Generating research plan and checking for track...")
            plan = await self.planner.create_plan(refined_query, context)
            
            # Ask clarifying questions to ensure track
            questions = await self.question_asker.ask_clarifying_questions(refined_query, context)
            if questions:
                await self.emit(job_id, ResearchStage.PLANNING, "Clarifying questions generated to keep research on track.", data={"clarification_needed": questions})

            await self.redis.update_job_state(job_id, {"plan": plan.dict(), "findings": []})
            await self.emit(job_id, ResearchStage.PLANNING, "Research plan generated.", data={"plan": plan.dict()})

            # 3. Iterative Execution
            findings = []
            videos = []
            images = []
            
            # Global media search
            await self.emit(job_id, ResearchStage.SEARCHING, "Searching for relevant YouTube videos and images...")
            videos = await self.services.search_youtube(refined_query)
            images = await self.services.search_images(refined_query)

            for step in plan.steps:
                step.status = "running"
                await self.emit(job_id, ResearchStage.SEARCHING, f"Executing: {step.description}")
                
                # Search
                search_results = await self.services.search_web(step.description)
                
                # Scrape & Summarize
                step_findings = []
                for res in search_results[:2]: # Limit for demo
                    await self.emit(job_id, ResearchStage.SCRAPING, f"Scraping content from {res['url']}")
                    raw_content = await self.services.scrape_content(res['url'])
                    summary = await self.services.summarize(raw_content)
                    step_findings.append({"source": res['url'], "summary": summary})

                step.status = "completed"
                step.result = str(step_findings)
                findings.extend(step_findings)

                # Update state
                await self.redis.update_job_state(job_id, {"plan": plan.dict(), "findings": findings, "videos": videos, "images": images})
                await self.emit(job_id, ResearchStage.SUMMARIZING, f"Completed step: {step.description}")
                
                # Background save findings
                db_queue.push("save_findings", job_id, step_findings)

            # 4. Artifact Generation
            await self.emit(job_id, ResearchStage.ARTIFACT_GEN, "Compiling research data and structuring markdown artifact...")
            artifact = await self.artifact_gen.generate(prompt, findings, videos, images)
            
            # Background save artifact
            db_queue.push("save_artifact", job_id, artifact.dict())

            # 5. Finalize
            await self.emit(job_id, ResearchStage.FINALIZING, "Finalizing research output.", status=JobStatus.COMPLETED, data={"artifact": artifact.dict()})
            
            return artifact

        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            await self.emit(job_id, ResearchStage.FINALIZING, f"Research failed: {str(e)}", status=JobStatus.FAILED)
            raise e
