from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class Character:
    id: str
    name: str
    role: str
    description: str
    image_paths: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Scene:
    id: str
    campaign_id: str
    title: str
    prompt: str
    character_ids: List[str]
    image_path: Optional[str] = None
    caption: Optional[str] = None
    style: Optional[str] = None
    chapter: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Campaign:
    id: str
    name: str
    description: str = ""
    character_ids: List[str] = field(default_factory=list)
    scene_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


