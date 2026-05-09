# Provider API Contract

## Router Endpoint

The RelayLM router exposes an OpenAI-compatible API at `http://<host>:<port>/v1`.

### Chat Completions

```
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "Qwen/Qwen3-0.6B",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}
```

**Response** (standard OpenAI chat completion format):

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "Qwen/Qwen3-0.6B",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hi!"},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

### Models List

```
GET /v1/models
```

Returns list of available models (local + configured provider models).

## Routing Behavior

| Scenario | Behavior |
|----------|----------|
| Requested model is deployed locally | Route to local vLLM instance |
| Requested model not local, provider configured | Route to provider in fallback order |
| No provider configured for model | Return 404 with available model list |
| All providers fail | Return last provider error with 502 |
| Streaming request | Stream responses, buffering on fallback |

## Provider Adapter Interface

Each external provider MUST expose an adapter that:
1. Translates the OpenAI-compatible request to the provider's native format
2. Translates the provider's response back to OpenAI-compatible format
3. Handles authentication (API key from keychain)
4. Reports errors consistently
