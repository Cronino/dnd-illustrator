from __future__ import annotations

import base64
import io
import os
from typing import List, Optional, Tuple

from openai import OpenAI


class OpenAIService:
    def __init__(self, api_key: Optional[str] = None) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY or pass api_key.")
        self.client = OpenAI(api_key=key)

    def expand_character_prompt(self, name: str, role: str, description: str, style: Optional[str] = None) -> str:
        style_text = f" in a {style} style" if style else ""
        system = (
            "You are a prompt engineer for an illustration model. Generate a clear, consistent,"
            " visual description that can be used to render a DnD character consistently across scenes."
        )
        user = (
            f"Character name: {name}. Role/class: {role}. Description: {description}."
            f" Return a detailed visual prompt{style_text} focusing on stable features, color palette,"
            " clothing, notable gear, and mood."
        )
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    def caption_scene(self, scene_prompt: str, involved_characters: List[str]) -> str:
        people = ", ".join(involved_characters)
        system = "You write brief, evocative one-sentence captions for fantasy scene illustrations."
        user = f"Write a caption for this scene: '{scene_prompt}'. Characters involved: {people}."
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.8,
            max_tokens=80,
        )
        return resp.choices[0].message.content.strip()

    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes:
        # Use Images API (DALL·E-style) returning base64
        result = self.client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size=size,
        )
        b64 = result.data[0].b64_json
        return base64.b64decode(b64)

    def recap_text(self, scenes: List[Tuple[str, str]]) -> str:
        # scenes: list of (title, caption)
        bullet_list = "\n".join([f"- {title}: {caption}" for title, caption in scenes])
        system = "You summarize DnD sessions concisely with a heroic tone."
        user = f"Summarize this session as a short recap (120-180 words):\n{bullet_list}"
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()


