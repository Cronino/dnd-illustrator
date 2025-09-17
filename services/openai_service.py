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

    def summarize_error(self, error_text: str, context: Optional[str] = None) -> str:
        """Return a brief, plain-English summary of an error with suggested fixes."""
        preface = (
            "You are a senior developer explaining errors to end users. "
            "Summarize the error in plain English and list 2-4 concrete fixes."
        )
        details = f"Context: {context}\nError:\n{error_text}" if context else f"Error:\n{error_text}"
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": preface},
                {"role": "user", "content": details},
            ],
            temperature=0.4,
            max_tokens=220,
        )
        return resp.choices[0].message.content.strip()

    def validate_api_key(self) -> None:
        """Raise an error if the API key is missing/invalid/blocked.

        Uses a minimal chat completion to verify access. Any exception is propagated
        so callers can decide whether to halt startup.
        """
        _ = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0.0,
        )

    def propose_future_scenes(self, recap_or_context: str, steps: int = 3) -> List[str]:
        """Generate a list of future scene prompts to extend the montage."""
        system = "You propose concise future DnD scene prompts that continue the story."
        user = f"Given this session context, propose {steps} future scene prompts in 1 sentence each.\nContext:\n{recap_or_context}"
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        lines = [l.strip("- ").strip() for l in text.splitlines() if l.strip()]
        return [l for l in lines if l]

    def propose_future_scenes_with_titles(self, recap_or_context: str, steps: int = 3) -> List[Tuple[str, str]]:
        """Return a list of (title, prompt) pairs for future scenes following story structure.

        Uses Dan Harmon's Story Circle (Hero's Journey) to create a coherent narrative arc
        with distinct beginning, middle, and end phases.
        """
        system = (
            "You are a narrative designer following Dan Harmon's Story Circle structure. "
            "Analyze the existing story and propose future scenes that complete a coherent narrative arc. "
            "Consider: Order (comfort zone), Need (something missing), Unfamiliar situation, "
            "Adapt (struggle), Pay the price (change), Return (mastery), Change (growth). "
            "Return exactly the requested number of items as lines in the format: Title: Prompt"
        )
        user = (
            f"Existing story context:\n{recap_or_context}\n\n"
            f"Analyze where this story currently sits in the narrative arc and propose {steps} future scenes "
            f"that complete a satisfying story structure. Each line like: Title: one-sentence prompt. "
            f"Ensure progression through story phases (setup → conflict → resolution)."
        )
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        pairs: List[Tuple[str, str]] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            if ":" in line:
                title, prompt = line.split(":", 1)
                pairs.append((title.strip().strip("-"), prompt.strip()))
        return pairs


