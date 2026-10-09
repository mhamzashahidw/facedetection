import asyncio
from typing import Callable, Dict, List, Any

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._queue = asyncio.Queue()

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        print(f"[EventBus] Subscribed to {event_type}")

    async def publish(self, event_type: str, payload: Any):
        await self._queue.put((event_type, payload))
        print(f"[EventBus] Published {event_type}")

    async def start_processing(self):
        print("[EventBus] Started processing events...")
        while True:
            event_type, payload = await self._queue.get()
            if event_type in self._subscribers:
                for handler in self._subscribers[event_type]:
                    try:
                        # Assuming handlers are async
                        asyncio.create_task(handler(payload))
                    except Exception as e:
                        print(f"[EventBus] Error in handler for {event_type}: {e}")
            self._queue.task_done()

event_bus = EventBus()
