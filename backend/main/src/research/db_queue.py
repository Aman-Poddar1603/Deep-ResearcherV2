import asyncio


class DatabaseQueue:
    """
    Mimics a background database saving mechanism.
    Functionality: queue.push(methodname, param1, param2, ...)
    """

    def __init__(self):
        self.queue = asyncio.Queue()
        self._worker_task = None

    async def start(self):
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        while True:
            item = await self.queue.get()
            method_name, args = item
            try:
                # Mimic the "database save" action
                print(f"[DB_QUEUE] Executing {method_name} with args: {args}")
                # In a real system, this would call actual DB methods
                await asyncio.sleep(0.1)  # Simulate I/O
            except Exception as e:
                print(f"[DB_QUEUE] Error executing {method_name}: {e}")
            finally:
                self.queue.task_done()

    def push(self, method_name: str, *args):
        """
        Pushes a task to the background queue.
        """
        print(f"[DB_QUEUE] Task pushed: {method_name}")
        self.queue.put_nowait((method_name, args))


# Singleton instance
db_queue = DatabaseQueue()
