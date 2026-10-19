import httpx
from config import settings

async def chat_completion(messages: list, temperature: float = 0.7, max_tokens: int = 2048, timeout: int = 300) -> str:
    """调用 Ollama（OpenAI 兼容接口）。
    timeout 默认 300 秒：P40 上 7B Q4 模型生成 2048 token 需要 1-3 分钟，不能太短。
    未来切换 vLLM/其他模型，只需改 .env 里的 OLLAMA_BASE_URL 和 LLM_MODEL，本文件不动。
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/chat/completions",
            json={
                "model": settings.LLM_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
