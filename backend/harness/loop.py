"""
AutoAgent Harness — the core ReAct loop.

Token management strategy (for models with tight TPM limits like gpt-oss-120b):
- Tool results are TRUNCATED in the message history sent to the LLM.
  The full result is still saved to DB and shown in the UI.
- A sliding window drops old middle turns when the estimated context
  gets too large, always keeping: system prompt + original task + last 4 turns.
- Token usage is estimated cheaply (chars / 4) before each LLM call so we
  can trim proactively rather than hitting a 413 error.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.harness.prompts import build_system_prompt
from backend.harness.tools import file_io, memory  # noqa: side-effect imports
from backend.harness.tools.base import get_tool, get_tool_schemas
from memory.session_store import publish_event
from models.database import AgentTurn, Task
from models.llm_provider import call_llm
from models.schemas import AgentEvent, HarnessConfig

# ── Token budget constants ────────────────────────────────────────────────────
# gpt-oss-120b on Groq free tier: 8,000 TPM
# We target staying under 6,000 tokens per request to leave headroom for the
# model's response (max_tokens_per_turn).
MAX_CONTEXT_CHARS = 18_000   # ~4,500 tokens (chars/4 ≈ tokens)
TOOL_RESULT_MAX_CHARS = 1_500  # truncate each tool result in message history
KEEP_RECENT_TURNS = 4         # always keep the last N assistant+tool pairs


def _estimate_tokens(messages: list[dict]) -> int:
    """Cheap token estimate: total chars / 4."""
    total = sum(len(json.dumps(m)) for m in messages)
    return total // 4


def _truncate_for_history(text: str, max_chars: int = TOOL_RESULT_MAX_CHARS) -> str:
    """Truncate a tool result that will be stored in message history."""
    if len(text) <= max_chars:
        return text
    keep = max_chars - 80
    return text[:keep] + f"\n\n[... {len(text) - keep:,} chars truncated for context window ...]"


def _trim_messages(messages: list[dict], max_chars: int = MAX_CONTEXT_CHARS) -> list[dict]:
    """
    Sliding window: if the message list is too large, drop old middle turns.

    Always preserves:
    - messages[0]  — system prompt
    - messages[1]  — original user task
    - last KEEP_RECENT_TURNS*2 messages — recent assistant+tool pairs

    Everything in between is summarised as a placeholder.
    """
    total_chars = sum(len(json.dumps(m)) for m in messages)
    if total_chars <= max_chars:
        return messages

    # Fixed anchors
    head = messages[:2]           # system + user task
    tail = messages[-(KEEP_RECENT_TURNS * 2):]  # last N turns

    # If head+tail already fits, we're done
    if sum(len(json.dumps(m)) for m in head + tail) <= max_chars:
        dropped = len(messages) - len(head) - len(tail)
        if dropped > 0:
            placeholder = {
                "role": "user",
                "content": (
                    f"[{dropped} earlier messages were summarised to save context. "
                    "Key findings so far are reflected in the recent tool results above.]"
                ),
            }
            return head + [placeholder] + tail
        return head + tail

    # Even head+tail is too long — truncate tool results in tail further
    trimmed_tail = []
    for m in tail:
        if m.get("role") == "tool":
            content = m["content"]
            if len(content) > 800:
                m = {**m, "content": content[:800] + " [truncated]"}
        trimmed_tail.append(m)

    return head + trimmed_tail


class AgentHarness:
    def __init__(
        self,
        task: Task,
        config: HarnessConfig,
        db: AsyncSession,
        session_id: Optional[str] = None,
    ):
        self.task = task
        self.config = config
        self.db = db
        self.task_id = str(task.id)
        self.session_id = session_id or str(uuid.uuid4())

        self.messages: list[dict] = []
        self.total_tokens = 0
        self.turn_number = 0

        file_io.set_task_context(self.task_id, self.session_id)
        memory.set_session(self.session_id)

    # ── Main entrypoint ───────────────────────────────────────────────────────

    async def run(self) -> str:
        await self._update_task_status("running")

        system_prompt = build_system_prompt(self.config.enabled_tools)
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self.task.description},
        ]

        tool_schemas = get_tool_schemas(self.config.enabled_tools)
        final_answer = ""

        try:
            while self.turn_number < self.config.max_turns:
                self.turn_number += 1
                logger.info(f"[{self.task_id}] Turn {self.turn_number} | "
                            f"msgs={len(self.messages)} | "
                            f"est_tokens={_estimate_tokens(self.messages)}")

                # Check total token budget
                if self.total_tokens >= self.config.total_token_budget:
                    msg = f"Token budget of {self.config.total_token_budget:,} exhausted."
                    await self._emit(AgentEvent(event_type="error", turn=self.turn_number, content=msg))
                    final_answer = f"Task stopped: {msg}"
                    break

                # ── Trim history to fit context window ────────────────────────
                trimmed = _trim_messages(self.messages)
                est_tokens = _estimate_tokens(trimmed)
                logger.debug(f"[{self.task_id}] Context: {est_tokens} est tokens, "
                             f"{len(trimmed)} msgs (was {len(self.messages)})")

                t0 = time.monotonic()

                # ── LLM call ──────────────────────────────────────────────────
                try:
                    response = await call_llm(
                        provider=self.config.llm_provider,
                        model=self.config.model,
                        messages=trimmed,          # send trimmed, not full history
                        tools=tool_schemas,
                        max_tokens=self.config.max_tokens_per_turn,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"[{self.task_id}] LLM error: {e}")
                    await self._emit(AgentEvent(
                        event_type="error", turn=self.turn_number, content=f"LLM error: {e}",
                    ))
                    final_answer = f"Task failed due to LLM error: {e}"
                    break

                elapsed_ms = (time.monotonic() - t0) * 1000
                usage = response["usage"]
                self.total_tokens += usage.get("total_tokens", 0)

                content = response["content"]
                tool_calls = response["tool_calls"]

                # ── Emit thought ──────────────────────────────────────────────
                if content:
                    await self._emit(AgentEvent(
                        event_type="thought",
                        turn=self.turn_number,
                        content=content,
                        duration_ms=elapsed_ms,
                        token_usage=usage,
                    ))

                # ── No tool calls → done ──────────────────────────────────────
                if not tool_calls:
                    final_answer = content
                    await self._persist_turn(thought=content, duration_ms=elapsed_ms,
                                             tokens_used=usage.get("total_tokens", 0))
                    break

                # ── Execute tools ─────────────────────────────────────────────
                # Append assistant message to FULL history
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                self.messages.append(assistant_msg)

                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]
                    tool_call_id = tc["id"]

                    await self._emit(AgentEvent(
                        event_type="tool_call",
                        turn=self.turn_number,
                        content=f"Calling {tool_name}",
                        tool_name=tool_name,
                        tool_args=tool_args,
                        duration_ms=elapsed_ms,
                        token_usage=usage,
                    ))

                    t_tool = time.monotonic()
                    # full_result → saved to DB and shown in UI
                    full_result = await self._execute_tool(tool_name, tool_args)
                    tool_elapsed = (time.monotonic() - t_tool) * 1000

                    await self._emit(AgentEvent(
                        event_type="tool_result",
                        turn=self.turn_number,
                        content="",
                        tool_name=tool_name,
                        tool_result=full_result,   # full in UI
                        duration_ms=tool_elapsed,
                    ))

                    # history_result → truncated version for LLM context
                    history_result = _truncate_for_history(full_result)

                    # Append TRUNCATED result to message history
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": history_result,
                    })

                    await self._persist_turn(
                        thought=content,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        tool_result=full_result,   # full in DB
                        duration_ms=elapsed_ms + tool_elapsed,
                        tokens_used=usage.get("total_tokens", 0),
                    )

            else:
                final_answer = (
                    f"Task reached maximum of {self.config.max_turns} turns."
                )
                await self._emit(AgentEvent(
                    event_type="error", turn=self.turn_number, content=final_answer,
                ))

        except asyncio.CancelledError:
            logger.info(f"[{self.task_id}] Task cancelled")
            await self._update_task_status("cancelled")
            await self._emit(AgentEvent(
                event_type="error", turn=self.turn_number, content="Task was cancelled by user.",
            ))
            raise

        except Exception as e:
            logger.exception(f"[{self.task_id}] Unhandled harness error: {e}")
            await self._update_task_status("failed", error=str(e))
            await self._emit(AgentEvent(
                event_type="error", turn=self.turn_number, content=f"Unexpected error: {e}",
            ))
            return f"Task failed: {e}"

        await self._update_task_status("completed", final_answer=final_answer)
        await self._emit(AgentEvent(
            event_type="done", turn=self.turn_number, content=final_answer,
        ))
        logger.info(f"[{self.task_id}] Done in {self.turn_number} turns, {self.total_tokens:,} tokens")
        return final_answer

    # ── Tool execution ────────────────────────────────────────────────────────

    async def _execute_tool(self, tool_name: str, tool_args: dict, attempt: int = 1) -> str:
        tool = get_tool(tool_name)
        if not tool:
            return f"Error: Unknown tool '{tool_name}'."
        try:
            result = await asyncio.wait_for(
                tool.run(**tool_args),
                timeout=self.config.tool_timeout_seconds,
            )
            return str(result)
        except asyncio.TimeoutError:
            return f"Error: Tool '{tool_name}' timed out after {self.config.tool_timeout_seconds}s."
        except asyncio.CancelledError:
            raise
        except Exception as e:
            error_msg = f"Tool '{tool_name}' error: {type(e).__name__}: {e}"
            logger.warning(f"[{self.task_id}] {error_msg}")
            if self.config.retry_on_tool_error and attempt < self.config.max_tool_retries:
                await asyncio.sleep(1)
                return await self._execute_tool(tool_name, tool_args, attempt + 1)
            return error_msg

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _emit(self, event: AgentEvent):
        try:
            await publish_event(self.task_id, event.model_dump())
        except Exception as e:
            logger.warning(f"[{self.task_id}] Publish failed: {e}")

    async def _persist_turn(
        self,
        thought: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[dict] = None,
        tool_result: Optional[str] = None,
        duration_ms: float = 0.0,
        tokens_used: int = 0,
    ):
        turn = AgentTurn(
            task_id=uuid.UUID(self.task_id),
            turn_number=self.turn_number,
            thought=thought,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result[:10_000] if tool_result else None,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
        )
        self.db.add(turn)
        try:
            await self.db.commit()
        except Exception as e:
            logger.warning(f"[{self.task_id}] DB persist failed: {e}")
            await self.db.rollback()

    async def _update_task_status(
        self,
        status: str,
        error: Optional[str] = None,
        final_answer: Optional[str] = None,
    ):
        self.task.status = status
        if status in ("completed", "failed", "cancelled"):
            self.task.completed_at = datetime.now(timezone.utc)
        if error:
            self.task.error_message = error
        if final_answer:
            self.task.final_answer = final_answer
        try:
            await self.db.commit()
        except Exception as e:
            logger.warning(f"[{self.task_id}] Status update failed: {e}")
            await self.db.rollback()