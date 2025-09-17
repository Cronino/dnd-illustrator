from __future__ import annotations

import io
import os
from typing import List

import streamlit as st
from PIL import Image

from models.entities import Scene
from services.openai_service import OpenAIService
from services.storage_service import StorageService
from services.montage_service import MontageService


def _init_state() -> None:
    if "storage" not in st.session_state:
        st.session_state.storage = StorageService()
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("OPENAI_API_KEY", "")
    if "style" not in st.session_state:
        st.session_state.style = ""


def _ensure_openai() -> OpenAIService | None:
    api_key = st.session_state.get("api_key") or ""
    if not api_key:
        st.info("Enter your OpenAI API key in the sidebar to enable AI features.")
        return None
    try:
        return OpenAIService(api_key)
    except Exception as e:
        st.error(f"OpenAI initialization failed: {e}")
        return None


def sidebar() -> None:
    st.sidebar.header("Settings")
    st.sidebar.text_input("OpenAI API Key", key="api_key", type="password")
    st.sidebar.selectbox(
        "Illustration Style (optional)",
        ["", "realistic", "comic", "watercolor", "pixel-art"],
        key="style",
    )


def characters_tab() -> None:
    storage: StorageService = st.session_state.storage
    st.subheader("Create Character")
    with st.form("create_character"):
        name = st.text_input("Name")
        role = st.text_input("Role/Class")
        desc = st.text_area("Description")
        uploaded = st.file_uploader("Reference Image (optional)", type=["png", "jpg", "jpeg"])
        expand = st.checkbox("Use AI to expand description into illustration prompt")
        submitted = st.form_submit_button("Create Character")
    image_paths: List[str] = []
    if submitted and name and role and desc:
        if uploaded:
            image_bytes = uploaded.read()
            path = storage.save_image_bytes(image_bytes, f"char-{name}.png")
            image_paths.append(path)
        if expand:
            client = _ensure_openai()
            if client:
                desc = client.expand_character_prompt(name, role, desc, style=st.session_state.style or None)
        char = storage.create_character(name, role, desc, image_paths=image_paths)
        st.success(f"Character created: {char.name}")

    st.subheader("Characters")
    for c in storage.list_characters():
        with st.expander(f"{c.name} ({c.role})"):
            st.write(c.description)
            if c.image_paths:
                cols = st.columns(3)
                for idx, p in enumerate(c.image_paths[:3]):
                    try:
                        cols[idx % 3].image(p, use_column_width=True)
                    except Exception:
                        pass


def campaign_tab() -> None:
    storage: StorageService = st.session_state.storage
    st.subheader("Campaigns")
    with st.form("create_campaign"):
        name = st.text_input("Campaign Name")
        desc = st.text_area("Campaign Description")
        submitted = st.form_submit_button("Create Campaign")
    if submitted and name:
        camp = storage.create_campaign(name, desc)
        st.success(f"Campaign created: {camp.name}")

    camps = storage.list_campaigns()
    if not camps:
        st.info("Create a campaign to begin.")
        return

    camp = st.selectbox("Select Campaign", camps, format_func=lambda c: c.name)
    st.write(camp.description)

    st.markdown("---")
    st.subheader("Add Characters to Campaign")
    chars = storage.list_characters()
    selected = st.multiselect("Choose characters", chars, format_func=lambda c: c.name)
    if st.button("Add to Campaign") and camp and selected:
        for ch in selected:
            storage.add_character_to_campaign(camp.id, ch.id)
        st.success("Characters added.")


def scenes_tab() -> None:
    storage: StorageService = st.session_state.storage
    client = _ensure_openai()
    st.subheader("Scenes")
    camps = storage.list_campaigns()
    if not camps:
        st.info("Create a campaign first.")
        return
    camp = st.selectbox("Campaign", camps, format_func=lambda c: c.name)
    camp_chars = [c for c in storage.list_characters() if c.id in camp.character_ids]
    with st.form("create_scene"):
        title = st.text_input("Scene Title")
        prompt = st.text_area("Scene Prompt")
        involved = st.multiselect("Characters Involved", camp_chars, format_func=lambda c: c.name)
        chapter = st.text_input("Chapter/Session (optional)")
        submitted = st.form_submit_button("Create Scene and Generate Illustration")

    if submitted and title and prompt and involved:
        scene = storage.create_scene(
            campaign_id=camp.id,
            title=title,
            prompt=prompt,
            character_ids=[c.id for c in involved],
            style=st.session_state.style or None,
            chapter=chapter or None,
        )
        caption = None
        image_path = None
        if client:
            # Combine character descriptions to enrich prompt
            char_prompts = []
            for ch in involved:
                char_prompts.append(f"{ch.name} ({ch.role}): {ch.description}")
            combined_prompt = (
                f"Illustrate the scene: {prompt}. Characters: "
                + "; ".join(char_prompts)
                + (f". Render in {st.session_state.style} style." if st.session_state.style else "")
            )
            try:
                img_bytes = client.generate_image(combined_prompt)
                image_path = storage.save_image_bytes(img_bytes, f"scene-{scene.id}.png")
            except Exception as e:
                st.error(f"Image generation failed: {e}")
            try:
                caption = client.caption_scene(prompt, [c.name for c in involved])
            except Exception as e:
                st.error(f"Caption generation failed: {e}")

        # Save results
        if image_path:
            scene.image_path = image_path
        if caption:
            scene.caption = caption
        storage.update_scene(scene)
        st.success("Scene created.")
        if scene.image_path and os.path.exists(scene.image_path):
            st.image(scene.image_path, caption=scene.caption or "", use_column_width=True)

    st.markdown("---")
    st.subheader("Campaign Scenes")
    if camp:
        scenes = storage.list_scenes(campaign_id=camp.id)
        for sc in scenes:
            with st.expander(f"{sc.title} ({sc.chapter or 'No chapter'})"):
                if sc.image_path and os.path.exists(sc.image_path):
                    st.image(sc.image_path, use_column_width=True)
                if sc.caption:
                    st.caption(sc.caption)


def montage_tab() -> None:
    storage: StorageService = st.session_state.storage
    client = _ensure_openai()
    st.subheader("Session Montage")
    camps = storage.list_campaigns()
    if not camps:
        st.info("Create a campaign first.")
        return
    camp = st.selectbox("Campaign", camps, format_func=lambda c: c.name, key="camp_montage")
    scenes = storage.list_scenes(campaign_id=camp.id)
    if not scenes:
        st.info("No scenes yet.")
        return

    montage = MontageService()
    if st.button("Generate PDF Montage"):
        path = montage.export_pdf(camp.name, scenes)
        st.success("Montage generated.")
        with open(path, "rb") as f:
            st.download_button("Download PDF", f, file_name=os.path.basename(path))

    if client and st.button("Generate Text Recap"):
        pairs = [(s.title, s.caption or "") for s in scenes]
        try:
            recap = client.recap_text(pairs)
            st.text_area("Session Recap", recap, height=200)
        except Exception as e:
            st.error(f"Recap failed: {e}")


def run() -> None:
    st.set_page_config(page_title="DnD Story Illustrator", layout="wide")
    _init_state()
    sidebar()
    st.title("DnD Story Illustrator")
    tabs = st.tabs(["Characters", "Campaigns", "Scenes", "Montage"]) 
    with tabs[0]:
        characters_tab()
    with tabs[1]:
        campaign_tab()
    with tabs[2]:
        scenes_tab()
    with tabs[3]:
        montage_tab()


