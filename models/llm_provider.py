"""
LLM provider abstraction — Groq, OpenAI, Anthropic.

Key resilience feature: when Groq returns 400 "Failed to parse tool call
arguments as JSON" (caused by the model emitting single-quoted Python dicts
inside a JSON string), we extract the failed_generation from the error,
repair the JSON, and return it as if the call succeeded.
"""
import json
import re
from typing import Any

from loguru import logger

from models.schemas import get_settings

settings = get_settings()


# ── JSON repair ───────────────────────────────────────────────────────────────

def _repair_json_args(raw: str) -> dict:
    """
    Try multiple strategies to parse a broken JSON tool-call argument string.

    Common failure: model writes Python dict literals with single quotes inside
    a JSON string, e.g.:
        {"code": "import x\nheaders = {'Accept': 'application/json'}\n..."}

    Strategy:
    1. Direct json.loads — works if valid
    2. Replace unescaped single quotes that are INSIDE a JSON string value
    3. ast.literal_eval — handles Python dict/str literals
    4. Extract just the code string with a regex and reconstruct
    5. Return empty dict so the harness can feed the error back to the LLM
    """
    # 1. Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Try to fix single-quoted strings by converting them carefully.
    #    Only replace single quotes that appear to be Python string delimiters,
    #    not apostrophes inside words.
    try:
        # Replace Python-style {'key': 'value'} with {"key": "value"}
        # This is intentionally conservative — only handle the outer dict structure
        fixed = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", lambda m: '"' + m.group(1).replace('"', '\\"') + '"', raw)
        return json.loads(fixed)
    except (json.JSONDecodeError, re.error):
        pass

    # 3. ast.literal_eval — handles Python dict/str literals directly
    try:
        import ast
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    # 4. For run_python: extract code with a forgiving regex
    try:
        # Look for "code": "..." or 'code': '...' spanning multiple lines
        code_match = re.search(
            r'["\']code["\']\s*:\s*["\'](.+?)["\'](?:\s*,|\s*\})',
            raw,
            re.DOTALL,
        )
        if code_match:
            code = code_match.group(1)
            # Unescape common escape sequences
            code = code.replace('\\n', '\n').replace('\\t', '\t').replace("\\'", "'")
            logger.info("Recovered 'code' argument via regex from malformed JSON")
            return {"code": code}
    except Exception:
        pass

    # 5. Give up — return empty so harness feeds error back to LLM
    logger.error(f"Could not repair JSON args: {raw[:300]}")
    return {}


def _extract_failed_generation(error_body: str) -> str | None:
    """Pull failed_generation out of a Groq 400 error body."""
    try:
        data = json.loads(error_body) if isinstance(error_body, str) else error_body
        return data.get("error", {}).get("failed_generation")
    except Exception:
        return None


def _parse_failed_generation(failed_gen: str) -> list[dict] | None:
    """
    Parse a Groq failed_generation string into a list of tool calls.
    The string looks like:
      {"name": "run_python", "arguments": {"code": "..."}}
    """
    if not failed_gen:
        return None

    # Try to extract name + arguments with a forgiving approach
    try:
        # First try direct JSON parse
        obj = json.loads(failed_gen)
        if isinstance(obj, dict) and "name" in obj:
            args = obj.get("arguments", {})
            if isinstance(args, str):
                args = _repair_json_args(args)
            return [{"id": "recovered_0", "name": obj["name"], "arguments": args}]
    except json.JSONDecodeError:
        pass

    # Try repairing the whole outer structure
    try:
        repaired = _repair_json_args(failed_gen)
        if isinstance(repaired, dict) and "name" in repaired:
            args = repaired.get("arguments", {})
            if isinstance(args, str):
                args = _repair_json_args(args)
            elif not isinstance(args, dict):
                args = {}
            return [{"id": "recovered_0", "name": repaired["name"], "arguments": args}]
    except Exception:
        pass

    # Extract name and code separately via regex — most reliable for run_python
    try:
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', failed_gen)
        if name_match:
            tool_name = name_match.group(1)

            # Extract code block — everything between "code": " and the closing "
            # Handle both escaped and unescaped newlines
            code_match = re.search(
                r'"code"\s*:\s*"(.*?)(?<!\\)"\s*(?:,|\})',
                failed_gen,
                re.DOTALL,
            )
            if code_match:
                code = code_match.group(1)
                code = code.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
            else:
                # Try single-quoted code value
                code_match2 = re.search(r"['\"]code['\"]\s*:\s*['\"](.+)", failed_gen, re.DOTALL)
                code = code_match2.group(1).rstrip('}\'"') if code_match2 else ""

            # Extract timeout
            timeout_match = re.search(r'"timeout"\s*:\s*(\d+)', failed_gen)
            timeout = int(timeout_match.group(1)) if timeout_match else 30

            args = {"code": code, "timeout": timeout} if code else {}
            logger.info(f"Recovered tool call via regex: {tool_name}")
            return [{"id": "recovered_0", "name": tool_name, "arguments": args}]
    except Exception as ex:
        logger.warning(f"Regex recovery failed: {ex}")

    return None


# ── Client factory ────────────────────────────────────────────────────────────

def get_llm_client(provider: str = None):
    provider = provider or settings.DEFAULT_LLM_PROVIDER

    if provider == "groq":
        from groq import AsyncGroq
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in .env — get a free key at console.groq.com")
        return AsyncGroq(api_key=settings.GROQ_API_KEY)

    elif provider == "openai":
        from openai import AsyncOpenAI
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in .env")
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    elif provider == "anthropic":
        from anthropic import AsyncAnthropic
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set in .env")
        return AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    raise ValueError(f"Unknown provider: '{provider}'. Valid: groq, openai, anthropic")


# ── Main call ─────────────────────────────────────────────────────────────────

async def call_llm(
    provider: str,
    model: str,
    messages: list[dict],
    tools: list[dict],
    max_tokens: int = 1024,
) -> dict:
    """
    Unified LLM call. Returns:
    {
        "content": str,
        "tool_calls": [{"id": str, "name": str, "arguments": dict}],
        "finish_reason": "stop" | "tool_calls" | "length",
        "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
    }

    Groq 400 "Failed to parse tool call" errors are automatically recovered
    by extracting failed_generation from the error and repairing the JSON.
    """
    client = get_llm_client(provider)
    logger.info(f"LLM → {provider}/{model} | {len(messages)} msgs | {len(tools)} tools")

    if provider in ("groq", "openai"):
        kwargs: dict[str, Any] = dict(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await client.chat.completions.create(**kwargs)

        except Exception as e:
            err_str = str(e)

            # ── Groq 400: try to recover from failed_generation ───────────────
            if "400" in err_str and "failed_generation" in err_str:
                logger.warning("Groq returned 400 with failed_generation — attempting JSON repair")

                # Extract the error body (Groq SDK wraps it differently)
                failed_gen = None
                try:
                    # The SDK puts the response body in e.body or e.response.text
                    body = getattr(e, "body", None) or getattr(getattr(e, "response", None), "text", None)
                    if body:
                        failed_gen = _extract_failed_generation(body)
                except Exception:
                    pass

                # Also try parsing from the string representation
                if not failed_gen:
                    match = re.search(r"'failed_generation':\s*'(.*?)'(?=,\s*'|\})", err_str, re.DOTALL)
                    if match:
                        failed_gen = match.group(1).replace("\\'", "'")

                if failed_gen:
                    recovered = _parse_failed_generation(failed_gen)
                    if recovered:
                        logger.info(f"Recovered {len(recovered)} tool call(s) from failed_generation")
                        return {
                            "content": "",
                            "tool_calls": recovered,
                            "finish_reason": "tool_calls",
                            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        }

                logger.error(f"Could not recover from 400 error: {err_str[:500]}")

            logger.error(f"LLM API error ({provider}/{model}): {err_str[:300]}")
            raise

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        logger.debug(f"finish={finish_reason} tool_calls={bool(msg.tool_calls)} content={len(msg.content or '')}ch")

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                raw_args = tc.function.arguments or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    logger.warning(f"Repairing malformed args for {tc.function.name}")
                    args = _repair_json_args(raw_args)
                tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})

        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        return {
            "content": msg.content or "",
            "tool_calls": tool_calls,
            "finish_reason": finish_reason or "stop",
            "usage": usage,
        }

    elif provider == "anthropic":
        anthropic_tools = []
        for t in tools:
            fn = t.get("function", {})
            anthropic_tools.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })

        system_msg = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_messages.append(m)

        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_msg,
            messages=user_messages,
            tools=anthropic_tools if anthropic_tools else None,
        )

        content_text = ""
        tool_calls = []
        finish_reason = "stop"

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "arguments": block.input})
                finish_reason = "tool_calls"

        if response.stop_reason == "end_turn" and not tool_calls:
            finish_reason = "stop"

        return {
            "content": content_text,
            "tool_calls": tool_calls,
            "finish_reason": finish_reason,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
        }

    raise ValueError(f"Unknown provider: {provider}")