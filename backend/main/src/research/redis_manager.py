import redis.asyncio as redis
import json
import os
import asyncio
from datetime import datetime
from .models import RedisEvent, JobStatus

class RedisManager:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.event_stream_key = "research:events"
        self.job_store_prefix = "research:job:"

    async def update_job_state(self, job_id: str, state: dict):
        key = f"{self.job_store_prefix}{job_id}"
        await self.client.hset(key, "state", json.dumps(state))
        await self.client.hset(key, "updated_at", datetime.utcnow().isoformat())

    async def get_job_state(self, job_id: str):
        key = f"{self.job_store_prefix}{job_id}"
        state = await self.client.hget(key, "state")
        return json.loads(state) if state else None

    async def get_multiple_job_states(self, job_ids: list):
        """
        Retrieves multiple job states in one go.
        """
        results = {}
        for job_id in job_ids:
            state = await self.get_job_state(job_id)
            if state:
                results[job_id] = state
        return results

    async def emit_event(self, event: RedisEvent):
        payload = event.json()
        # Push to Redis Stream
        await self.client.xadd(self.event_stream_key, {"event": payload, "job_id": event.job_id})
        
        # Update job status in hash
        key = f"{self.job_store_prefix}{event.job_id}"
        await self.client.hset(key, "status", event.status)
        await self.client.hset(key, "last_message", event.message)

    async def get_stream_events(self, job_id: str, last_id: str = "0"):
        """
        Generator that yields new events from the Redis stream for a specific job.
        """
        while True:
            # Read from stream
            events = await self.client.xread({self.event_stream_key: last_id}, count=10, block=5000)
            if events:
                for stream, stream_events in events:
                    for event_id, event_data in stream_events:
                        last_id = event_id
                        # Filter by job_id
                        if event_data.get("job_id") == job_id:
                            yield event_data.get("event")
            await asyncio.sleep(0.1)

    async def push_to_pending_queue(self, query: dict):
        await self.client.lpush("research:pending_queries", json.dumps(query))
