"""Pointer-free request lifecycle. Callbacks never wait for the network or a lock."""

from dataclasses import dataclass
import queue
import threading
import time
import uuid

from service_client import ServiceClient, ServiceError


COMMANDS = (b"/community", b"/community state", b"/community result", b"/community reconnect",
            b"/community leave", b"/community off")
LIFETIME = 20.0


def display(text):
    # Native text supports formatting. Pass only a small plain ASCII alphabet.
    allowed = " .,:;!?'-_()/[]#=+"
    return "".join(c if c.isascii() and (c.isalnum() or c in allowed) else "?"
                   for c in text[:640]).encode("ascii")


@dataclass(frozen=True)
class Work:
    generation: int
    request_id: str
    deadline: float
    cancel: threading.Event
    operation: str


class Bridge:
    def __init__(self, config, emit, client=None, clock=time.monotonic,
                 automatic=False, delivery_delay=0.0):
        if (not isinstance(delivery_delay, (int, float)) or isinstance(delivery_delay, bool)
                or not 0 <= delivery_delay <= 10):
            raise ValueError("delivery_delay must be between 0 and 10 seconds")
        self.config = config
        self.emit = emit
        self.clock = clock
        self.automatic = automatic
        self.delivery_delay = float(delivery_delay)
        self._client = client if client is not None else ServiceClient(config)
        self._lock = threading.Lock()
        # CPython SimpleQueue.put/get_nowait are reentrant C operations. Queue's
        # put_nowait still waits on its internal mutex; keep capacity under our gate.
        self._jobs = queue.SimpleQueue()
        self._generation = 0
        self._pending = None
        self._ready = None
        self._disabled = False
        self._thread = threading.Thread(target=self._run, name="CommunityService", daemon=True)
        self._thread.start()

    def _invalidate(self):
        self._generation += 1
        if self._pending:
            self._pending.cancel.set()
        self._pending = self._ready = None
        try:
            self._jobs.get_nowait()
        except queue.Empty:
            pass

    def _enqueue(self, work):
        if self._jobs.qsize() >= 1:
            raise queue.Full
        self._jobs.put(work)

    @staticmethod
    def _expired_message(work):
        return ("Community result expired; outcome unknown. Use /community state to check saved progress."
                if work.operation == "probe" else
                "Community state result expired. Use /community state to read again.")

    def _expire_pending(self, now):
        if self._pending and now >= self._pending.deadline:
            expired = self._pending
            self._invalidate()
            self._ready = (expired, self._expired_message(expired), now)
            self.emit("request_expired", request_id=expired.request_id, generation=expired.generation)

    def _consume_ready(self, now):
        if self._ready is None:
            return None
        work, message, ready_at = self._ready
        if now < ready_at and now < work.deadline:
            return None
        self._ready = None
        if now >= work.deadline:
            message = self._expired_message(work)
        self.emit("server_presentation", request_id=work.request_id, generation=work.generation,
                  operation=work.operation)
        return display(message)

    def poll(self):
        """Consume one response on a permitted callback, without waiting or idle text."""
        if not self._lock.acquire(blocking=False):
            return None
        try:
            if self._disabled:
                return None
            now = self.clock()
            self._expire_pending(now)
            return self._consume_ready(now)
        finally:
            self._lock.release()

    def busy(self):
        """Conservatively reject a new action when work or its result is outstanding."""
        if not self._lock.acquire(blocking=False):
            return True
        try:
            return (self._disabled or self._pending is not None or self._ready is not None
                    or self._jobs.qsize() >= 1)
        finally:
            self._lock.release()

    def cancel_pending(self):
        """Invalidate this lifecycle's work; cancellation does not undo server commits."""
        if not self._lock.acquire(blocking=False):
            return False
        try:
            work = self._pending if self._pending else self._ready[0] if self._ready else None
            self._invalidate()
            self._enqueue(None)  # Close on the worker, never on an engine callback.
            if work:
                self.emit("request_cancelled", request_id=work.request_id, generation=work.generation,
                          operation=work.operation)
            self.emit("community_left", generation=self._generation, disabled=self._disabled,
                      reason="lifecycle")
            return True
        finally:
            self._lock.release()

    def handle(self, command):
        """Called only at a matched native system reply, with no native values."""
        if not self._lock.acquire(blocking=False):
            return b"Community busy; try the command again."
        try:
            if self._disabled:
                return b"Community adapter disabled until restart."
            if command in (b"/community off", b"/community leave", b"/community reconnect"):
                self._invalidate()
                self._disabled = command == b"/community off"
                self._enqueue(None)  # Worker closes the session; callback never joins it.
                self.emit("community_left", generation=self._generation, disabled=self._disabled)
                if self._disabled:
                    return b"Community adapter disabled until restart."
                return (b"Community disconnected. Use /community to reconnect." if command == b"/community leave"
                        else b"Community reconnect queued. Use /community to send a new request.")
            now = self.clock()
            self._expire_pending(now)
            if command == b"/community result":
                result = self._consume_ready(now)
                if result is not None:
                    return result
                if self._pending or self._ready:
                    return (b"Community connecting or waiting. Reply will appear automatically." if self.automatic
                            else b"Community connecting or waiting. Use /community result shortly.")
                return b"No community result pending. Use /community to send a request."
            if self._pending or self._ready:
                return (b"Community request already pending or ready. Reply will appear automatically." if self.automatic
                        else b"Community request already pending or ready. Use /community result.")
            operation = "state" if command == b"/community state" else "probe"
            work = Work(self._generation, str(uuid.uuid4()), self.clock() + LIFETIME, threading.Event(), operation)
            try:
                self._enqueue(work)
            except queue.Full:
                return b"Community reconnecting; try /community shortly."
            self._pending = work
            self.emit("server_request_queued", request_id=work.request_id, generation=work.generation,
                      community=self.config.community, operation=work.operation)
            action = "connecting/reading saved progress" if operation == "state" else "connecting/sending"
            hint = "Reply will appear automatically." if self.automatic else "Use /community result."
            return display(f"Community {self.config.community}: {action}. {hint}")
        finally:
            self._lock.release()

    def _run(self):
        while True:
            work = self._jobs.get()
            if work is None:
                self._client.close()
                if self._disabled:
                    return
                continue
            cancelled = lambda: work.cancel.is_set() or self.clock() >= work.deadline
            try:
                state = (self._client.state(cancelled) if work.operation == "state" else
                         self._client.probe(work.request_id, cancelled))
                text = (f"[{self.config.community} #{state['revision']} progress {state['progress']}] "
                        f"{state['message']}")
                self.emit("server_response", request_id=work.request_id, generation=work.generation,
                          operation=work.operation, member_id=state["memberId"],
                          interaction_id=state["interactionId"], revision=state["revision"],
                          progress=state["progress"])
            except ServiceError as error:
                code = str(error)
                if code == "unavailable":
                    text = ("Community server unavailable or timed out; outcome unknown. Check server, then /community state."
                            if work.operation == "probe" else
                            "Community server unavailable or timed out. Check server, then /community state.")
                else:
                    text = f"Community rejected or disconnected ({code}). Check setup, then /community reconnect."
                self.emit("server_failure", request_id=work.request_id, generation=work.generation,
                          operation=work.operation, code=code)
            except Exception:
                # Never let exception text (which could include credentials) reach chat or logs.
                text = "Community client error. Use /community reconnect."
                self.emit("server_failure", request_id=work.request_id, generation=work.generation,
                          code="client_error")
            with self._lock:
                active = self._pending is work and work.generation == self._generation and not cancelled()
                if active:
                    self._ready = (work, text, self.clock() + self.delivery_delay)
                    self._pending = None
            if not active:
                self.emit("late_response_discarded", request_id=work.request_id, generation=work.generation)
                self._client.close()
