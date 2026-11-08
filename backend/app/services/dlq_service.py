import uuid
import time
from typing import Dict, List, Optional
from backend.app.schemas.dlq_schemas import (
    DLQMessage, DLQEnqueueRequest, DLQReplayResponse, DLQStats
)

class DeadLetterQueueService:
    def __init__(self, base_backoff_sec: float = 1.0, backoff_multiplier: float = 2.0):
        self.base_backoff_sec = base_backoff_sec
        self.backoff_multiplier = backoff_multiplier
        self._messages: Dict[str, DLQMessage] = {}

    def clear(self) -> None:
        self._messages.clear()

    def enqueue(self, req: DLQEnqueueRequest) -> DLQMessage:
        msg_id = f'dlq-{uuid.uuid4().hex[:10]}'
        now = time.time()
        msg = DLQMessage(
            message_id=msg_id,
            run_id=req.run_id,
            payload=req.payload,
            error_reason=req.error_reason,
            retry_count=0,
            max_retries=req.max_retries,
            poison_pill=False,
            enqueued_at=now,
            next_retry_at=now + self.base_backoff_sec,
            resolved=False
        )
        self._messages[msg_id] = msg
        return msg

    def record_failure(self, message_id: str, new_error: str) -> DLQMessage:
        if message_id not in self._messages:
            raise KeyError(f'DLQ message {message_id} not found')
        msg = self._messages[message_id]
        msg.retry_count += 1
        msg.error_reason = new_error
        if msg.retry_count >= msg.max_retries:
            msg.poison_pill = True
            msg.next_retry_at = 0.0
        else:
            backoff = self.base_backoff_sec * (self.backoff_multiplier ** msg.retry_count)
            msg.next_retry_at = time.time() + backoff
        return msg

    def mark_resolved(self, message_id: str) -> DLQMessage:
        if message_id not in self._messages:
            raise KeyError(f'DLQ message {message_id} not found')
        msg = self._messages[message_id]
        msg.resolved = True
        return msg

    def replay_messages(self, run_id: Optional[str] = None, force_poison: bool = False) -> DLQReplayResponse:
        replayed = []
        for msg in self._messages.values():
            if msg.resolved:
                continue
            if msg.poison_pill and not force_poison:
                continue
            if run_id and msg.run_id != run_id:
                continue
            msg.resolved = True
            replayed.append(msg.message_id)
        return DLQReplayResponse(replayed_count=len(replayed), message_ids=replayed, success=True)

    def get_stats(self) -> DLQStats:
        total = len(self._messages)
        pending = sum(1 for m in self._messages.values() if not m.resolved and not m.poison_pill)
        poison = sum(1 for m in self._messages.values() if m.poison_pill and not m.resolved)
        resolved = sum(1 for m in self._messages.values() if m.resolved)
        return DLQStats(
            total_enqueued=total,
            pending_retries=pending,
            poison_pills=poison,
            resolved_count=resolved
        )

dlq_service = DeadLetterQueueService()
