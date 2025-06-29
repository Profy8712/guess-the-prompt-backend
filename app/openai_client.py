import os
import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def generate_image(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "dall-e-2",
        "prompt": prompt,
        "n": 1,
        "size": "512x512",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=data, timeout=60)
        try:
            resp.raise_for_status()
        except Exception:
            print("OpenAI 400/500 error. Request sent:", data)
            print("OpenAI response:", resp.text)
            raise Exception(f"OpenAI error: {resp.text}")
        result = resp.json()
        return result["data"][0]["url"]
