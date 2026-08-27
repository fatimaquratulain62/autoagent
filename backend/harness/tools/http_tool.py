"""Generic HTTP request tool."""
import json
from typing import ClassVar, Optional

import httpx
from pydantic import BaseModel, Field

from backend.harness.tools.base import BaseTool, register_tool


class HttpRequestInput(BaseModel):
    url: str = Field(..., description="URL to make the request to")
    method: str = Field("GET", description="HTTP method: GET, POST, PUT, DELETE, PATCH")
    headers: Optional[dict] = Field(None, description="Request headers as a dict")
    body: Optional[str] = Field(None, description="Request body as a JSON string or plain text")
    timeout: int = Field(30, description="Request timeout in seconds")


class HttpRequestTool(BaseTool):
    name: ClassVar[str] = "http_request"
    description: ClassVar[str] = (
        "Make arbitrary HTTP requests to APIs or endpoints. Use for calling REST APIs, "
        "checking URL health, submitting data, or fetching JSON responses. "
        "Returns status code, headers, and response body."
    )
    input_schema: ClassVar[type[BaseModel]] = HttpRequestInput

    async def run(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        body: Optional[str] = None,
        timeout: int = 30,
    ) -> str:
        method = method.upper()
        req_headers = {
            "User-Agent": "AutoAgent/1.0",
            "Accept": "application/json, text/plain, */*",
        }
        if headers:
            req_headers.update(headers)

        # Parse body
        content = None
        json_data = None
        if body:
            try:
                json_data = json.loads(body)
                req_headers.setdefault("Content-Type", "application/json")
            except (json.JSONDecodeError, TypeError):
                content = body.encode() if isinstance(body, str) else body

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.request(
                method,
                url,
                headers=req_headers,
                json=json_data,
                content=content,
            )

        response_headers = dict(resp.headers)
        content_type = response_headers.get("content-type", "")
        text = resp.text

        if len(text) > 3000:
            text = text[:3000] + "\n[... response truncated ...]"

        result = (
            f"Status: {resp.status_code} {resp.reason_phrase}\n"
            f"Content-Type: {content_type}\n\n"
            f"Response Body:\n{text}"
        )
        return result


register_tool(HttpRequestTool())