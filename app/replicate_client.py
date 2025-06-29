import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
REPLICATE_MODEL_VERSION = "ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4"

async def generate_image(prompt: str) -> str:
    if not REPLICATE_API_TOKEN:
        raise Exception("REPLICATE_API_TOKEN not set")

    url = "https://api.replicate.com/v1/predictions"
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "version": REPLICATE_MODEL_VERSION,
        "input": {
            "prompt": prompt,
            "width": 768,
            "height": 768,
            "num_outputs": 1,
            "guidance_scale": 7.5,
            "num_inference_steps": 50
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        print("DEBUG POST REPLICATE:", response.status_code, response.text)
        response.raise_for_status()
        prediction = response.json()

        prediction_url = prediction["urls"]["get"]
        status = prediction["status"]

        while status not in ("succeeded", "failed"):
            await asyncio.sleep(1)
            poll_resp = await client.get(prediction_url, headers=headers)
            poll_resp.raise_for_status()
            prediction = poll_resp.json()
            status = prediction["status"]

        if status == "succeeded":
            return prediction["output"][0]
        else:
            raise Exception(f"Replicate generation failed: {prediction}")
