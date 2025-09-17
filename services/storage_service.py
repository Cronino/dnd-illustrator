from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from models.entities import Character, Scene, Campaign


class StorageService:
    def __init__(self, base_dir: str | Path = "data") -> None:
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.characters_path = self.base_path / "characters.json"
        self.scenes_path = self.base_path / "scenes.json"
        self.campaigns_path = self.base_path / "campaigns.json"
        self.images_dir = self.base_path / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self) -> None:
        for path in [self.characters_path, self.scenes_path, self.campaigns_path]:
            if not path.exists():
                path.write_text(json.dumps({}), encoding="utf-8")

    # Generic helpers
    def _read_json(self, path: Path) -> Dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write_json(self, path: Path, data: Dict) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Characters
    def create_character(self, name: str, role: str, description: str, image_paths: Optional[List[str]] = None) -> Character:
        characters = self._read_json(self.characters_path)
        character_id = str(uuid.uuid4())
        character = Character(id=character_id, name=name, role=role, description=description, image_paths=image_paths or [])
        characters[character_id] = character.to_dict()
        self._write_json(self.characters_path, characters)
        return character

    def list_characters(self) -> List[Character]:
        characters = self._read_json(self.characters_path)
        return [Character(**c) for c in characters.values()]

    def get_character(self, character_id: str) -> Optional[Character]:
        characters = self._read_json(self.characters_path)
        data = characters.get(character_id)
        return Character(**data) if data else None

    # Campaigns
    def create_campaign(self, name: str, description: str = "") -> Campaign:
        campaigns = self._read_json(self.campaigns_path)
        campaign_id = str(uuid.uuid4())
        campaign = Campaign(id=campaign_id, name=name, description=description)
        campaigns[campaign_id] = campaign.to_dict()
        self._write_json(self.campaigns_path, campaigns)
        return campaign

    def list_campaigns(self) -> List[Campaign]:
        campaigns = self._read_json(self.campaigns_path)
        return [Campaign(**c) for c in campaigns.values()]

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        campaigns = self._read_json(self.campaigns_path)
        data = campaigns.get(campaign_id)
        return Campaign(**data) if data else None

    def add_character_to_campaign(self, campaign_id: str, character_id: str) -> None:
        campaigns = self._read_json(self.campaigns_path)
        campaign = campaigns.get(campaign_id)
        if not campaign:
            return
        if character_id not in campaign["character_ids"]:
            campaign["character_ids"].append(character_id)
        campaigns[campaign_id] = campaign
        self._write_json(self.campaigns_path, campaigns)

    def add_scene_to_campaign(self, campaign_id: str, scene_id: str) -> None:
        campaigns = self._read_json(self.campaigns_path)
        campaign = campaigns.get(campaign_id)
        if not campaign:
            return
        campaign["scene_ids"].append(scene_id)
        campaigns[campaign_id] = campaign
        self._write_json(self.campaigns_path, campaigns)

    # Scenes
    def create_scene(
        self,
        campaign_id: str,
        title: str,
        prompt: str,
        character_ids: List[str],
        style: Optional[str] = None,
        chapter: Optional[str] = None,
    ) -> Scene:
        scenes = self._read_json(self.scenes_path)
        scene_id = str(uuid.uuid4())
        scene = Scene(
            id=scene_id,
            campaign_id=campaign_id,
            title=title,
            prompt=prompt,
            character_ids=character_ids,
            style=style,
            chapter=chapter,
        )
        scenes[scene_id] = scene.to_dict()
        self._write_json(self.scenes_path, scenes)
        self.add_scene_to_campaign(campaign_id, scene_id)
        return scene

    def update_scene(self, scene: Scene) -> None:
        scenes = self._read_json(self.scenes_path)
        scenes[scene.id] = scene.to_dict()
        self._write_json(self.scenes_path, scenes)

    def list_scenes(self, campaign_id: Optional[str] = None) -> List[Scene]:
        scenes = self._read_json(self.scenes_path)
        scene_objs = [Scene(**s) for s in scenes.values()]
        if campaign_id:
            scene_objs = [s for s in scene_objs if s.campaign_id == campaign_id]
        scene_objs.sort(key=lambda s: s.created_at)
        return scene_objs

    # Images
    def save_image_bytes(self, image_bytes: bytes, filename_hint: str) -> str:
        file_path = self.images_dir / filename_hint
        # Ensure unique filename
        if file_path.exists():
            file_path = self.images_dir / f"{Path(filename_hint).stem}-{uuid.uuid4().hex[:8]}{Path(filename_hint).suffix}"
        file_path.write_bytes(image_bytes)
        return str(file_path)


