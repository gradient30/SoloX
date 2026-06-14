"""Versioned control protocol for the Android weak-network agent."""

from __future__ import annotations

import json
import uuid
from typing import Any

SCHEMA_VERSION = 1
MAX_MESSAGE_BYTES = 1024 * 1024


class AgentProtocolError(RuntimeError):
    """Raised when an Agent message violates the control protocol."""


def build_request(
    command: str,
    payload: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not command:
        raise AgentProtocolError('command is required')
    return {
        'schema_version': SCHEMA_VERSION,
        'request_id': request_id or str(uuid.uuid4()),
        'command': command,
        'payload': payload or {},
    }


def encode_message(message: dict[str, Any]) -> bytes:
    encoded = json.dumps(
        message,
        ensure_ascii=True,
        separators=(',', ':'),
        sort_keys=True,
    ).encode('utf-8')
    if len(encoded) > MAX_MESSAGE_BYTES:
        raise AgentProtocolError('message exceeds size limit')
    return encoded + b'\n'


def decode_response(
    raw: str | bytes,
    *,
    expected_request_id: str,
) -> dict[str, Any]:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise AgentProtocolError(f'Agent response is not valid UTF-8: {exc}') from exc
    try:
        message = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AgentProtocolError(f'invalid JSON response: {exc}') from exc
    if not isinstance(message, dict):
        raise AgentProtocolError('response must be a JSON object')
    if message.get('schema_version') != SCHEMA_VERSION:
        raise AgentProtocolError(
            f'unsupported schema version: {message.get("schema_version")}'
        )
    if message.get('request_id') != expected_request_id:
        raise AgentProtocolError('response request_id does not match request')
    if not isinstance(message.get('ok'), bool):
        raise AgentProtocolError('response ok field must be boolean')
    payload = message.get('payload')
    if payload is None:
        payload = {}
        message['payload'] = payload
    if not isinstance(payload, dict):
        raise AgentProtocolError('response payload must be an object')
    error = message.get('error')
    if error is not None and not isinstance(error, str):
        raise AgentProtocolError('response error must be a string or null')
    return message
