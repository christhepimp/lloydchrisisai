"""
Lloyd's Image Generation Module (Placeholder)
=============================================
Pure-scratch placeholder. Later we will implement real diffusion or call an API.
Lloyd can decide to generate images on his own or when asked.
"""

import random
from typing import Optional
from datetime import datetime


class ImageGenerator:
    def __init__(self):
        self.history = []

    def generate(self, prompt: str, autonomous: bool = False) -> str:
        """
        Placeholder that returns a description instead of a real image.
        Later this will produce actual image files or base64.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fake_id = f"lloyd_img_{timestamp}_{random.randint(1000,9999)}"

        result = {
            "id": fake_id,
            "prompt": prompt,
            "status": "placeholder",
            "message": f"Lloyd generated an image concept for: '{prompt}'",
            "autonomous": autonomous,
            "note": "Real image generation coming soon (diffusion from scratch or API).",
        }

        self.history.append(result)
        return (
            f"bet i cooked something up\n"
            f"prompt: {prompt}\n"
            f"id: {fake_id}\n"
            f"(this is still a placeholder — real pixels coming later)"
        )

    def decide_to_generate(self) -> Optional[str]:
        """
        Autonomous decision: sometimes Lloyd just feels like making an image.
        """
        if random.random() < 0.08:  # 8% chance when called
            ideas = [
                "a chill night city with neon lights",
                "a sigma wolf in the mountains",
                "abstract vibes only",
                "a robot that looks like me",
                "sunset over the ocean fr",
            ]
            prompt = random.choice(ideas)
            return self.generate(prompt, autonomous=True)
        return None
