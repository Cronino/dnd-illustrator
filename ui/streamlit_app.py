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
    if "style" not in st.session_state:
        st.session_state.style = ""
    if "validated_api" not in st.session_state:
        st.session_state.validated_api = False


def _ensure_openai() -> OpenAIService | None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error("OPENAI_API_KEY not set. Add it to your .env and restart.")
        return None
    try:
        client = OpenAIService()
        if not st.session_state.validated_api:
            try:
                client.validate_api_key()
                st.session_state.validated_api = True
            except Exception as e:
                # Summarize before halting use
                try:
                    summary = client.summarize_error(str(e), context="Startup API key validation")
                    st.error(summary)
                except Exception:
                    pass
                st.exception(e)
                return None
        return client
    except Exception as e:
        st.error(f"OpenAI initialization failed: {e}")
        return None


def sidebar() -> None:
    st.sidebar.header("Settings")
    st.sidebar.selectbox(
        "Illustration Style (optional)",
        ["", "realistic", "comic", "watercolor", "pixel-art"],
        key="style",
    )


def characters_tab() -> None:
    storage: StorageService = st.session_state.storage
    st.subheader("Create Character")
    with st.form("create_character"):
        name = st.text_input("Name", key="char_name")
        role = st.text_input("Role/Class", key="char_role")
        desc = st.text_area("Description (full)", key="char_desc")
        summary = st.text_area("Brief Summary (1-2 sentences)", key="char_summary")
        uploaded = st.file_uploader("Reference Image (optional)", type=["png", "jpg", "jpeg"], key="char_upload")
        expand = st.checkbox("Use AI to expand description into illustration prompt", key="char_expand")
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
                with st.status("Submitting prompt…", expanded=False) as s:
                    s.update(label="Generating long prompt…", state="running")
                    long_prompt = client.expand_character_prompt(name, role, desc, style=st.session_state.style or None)
                    s.update(label="Prompt ready", state="complete")
            else:
                long_prompt = desc
        else:
            long_prompt = desc
        portrait_path = image_paths[0] if image_paths else None
        char = storage.create_character(name, role, desc, summary=summary, long_prompt=long_prompt, portrait_path=portrait_path, image_paths=image_paths)
        # Auto-generate portrait if none was uploaded
        if not portrait_path:
            client = _ensure_openai()
            if client:
                try:
                    with st.status("Generating portrait…", expanded=False) as s:
                        s.update(label="Contacting image API…", state="running")
                        prompt_text = (long_prompt or desc) + (f". Render in {st.session_state.style} style." if st.session_state.style else "")
                        img_bytes = client.generate_image(prompt_text)
                        img_path = storage.save_image_bytes(img_bytes, f"char-{name}.png")
                        char.portrait_path = img_path
                        char.image_paths.append(img_path)
                        storage.update_character(char)
                        s.update(label="Portrait saved", state="complete")
                except Exception as e:
                    try:
                        summary_msg = _ensure_openai().summarize_error(str(e), context=f"Generating portrait for {name}")  # type: ignore
                        st.error(summary_msg)
                    except Exception:
                        pass
                    st.exception(e)
        st.success(f"Character created: {char.name}")
        # Clear form inputs
        st.session_state.char_name = ""
        st.session_state.char_role = ""
        st.session_state.char_desc = ""
        st.session_state.char_summary = ""
        st.session_state.char_upload = None
        st.session_state.char_expand = False
        st.rerun()

    st.subheader("Characters")
    chars = storage.list_characters()
    if not chars:
        st.info("No characters yet.")
    else:
        tabs = st.tabs([f"{c.name}" for c in chars])
        for idx, c in enumerate(chars):
            with tabs[idx]:
                cols = st.columns([1, 2])
                with cols[0]:
                    if c.portrait_path and os.path.exists(c.portrait_path):
                        st.image(c.portrait_path, caption=f"{c.name} ({c.role})", width="stretch")
                    elif c.image_paths:
                        try:
                            st.image(c.image_paths[0], caption=f"{c.name} ({c.role})", width="stretch")
                        except Exception:
                            pass
                with cols[1]:
                    if c.summary:
                        st.write(c.summary)
                    else:
                        st.write(c.description[:300] + ("..." if len(c.description) > 300 else ""))
                    with st.expander("Details & Actions"):
                        st.write("Full Description")
                        desc_edit = st.text_area(f"Description — {c.name}", value=c.description, key=f"desc_{c.id}")
                        st.write("Brief Summary")
                        summary_edit = st.text_area(f"Summary — {c.name}", value=c.summary or "", key=f"summary_{c.id}")
                        if getattr(c, "long_prompt", ""):
                            st.write("Illustration Prompt (long)")
                            st.code(c.long_prompt)

                        action_cols = st.columns(4)
                        with action_cols[0]:
                            if st.button("Save Changes", key=f"save_{c.id}"):
                                c.description = desc_edit
                                c.summary = summary_edit
                                storage.update_character(c)
                                st.success("Saved.")
                                st.rerun()
                        with action_cols[1]:
                            if st.button("Regen Prompt", key=f"regen_prompt_{c.id}"):
                                client = _ensure_openai()
                                if client:
                                    try:
                                        st.toast("Submitted: regenerating prompt…")
                                        with st.spinner("Working…"):
                                            new_lp = client.expand_character_prompt(c.name, c.role, desc_edit, style=st.session_state.style or None)
                                        c.long_prompt = new_lp
                                        c.description = desc_edit
                                        c.summary = summary_edit
                                        storage.update_character(c)
                                        st.success("Prompt regenerated.")
                                        st.rerun()
                                    except Exception as e:
                                        try:
                                            summary = client.summarize_error(str(e), context=f"Regenerating prompt for {c.name}")
                                            st.error(summary)
                                        except Exception:
                                            pass
                                        st.exception(e)
                        with action_cols[2]:
                            if st.button("Regen Portrait", key=f"regen_img_{c.id}"):
                                client = _ensure_openai()
                                if client:
                                    try:
                                        st.toast("Submitted: regenerating portrait…")
                                        with st.spinner("Working…"):
                                            prompt_text = c.long_prompt or c.description
                                            img_bytes = client.generate_image(prompt_text + (f". Render in {st.session_state.style} style." if st.session_state.style else ""))
                                        img_path = storage.save_image_bytes(img_bytes, f"char-{c.name}.png")
                                        # maintain version history
                                        if c.portrait_path:
                                            if c.image_versions is None:
                                                c.image_versions = []
                                            c.image_versions.append(c.portrait_path)
                                        c.portrait_path = img_path
                                        if img_path not in (c.image_paths or []):
                                            c.image_paths.append(img_path)
                                        storage.update_character(c)
                                        st.success("Portrait regenerated.")
                                        st.rerun()
                                    except Exception as e:
                                        try:
                                            summary = client.summarize_error(str(e), context=f"Regenerating portrait for {c.name}")
                                            st.error(summary)
                                        except Exception:
                                            pass
                                        st.exception(e)
                        # Hidden history & revert
                        with st.expander("Portrait history"):
                            versions = list(reversed(getattr(c, "image_versions", []) or []))
                            if not versions:
                                st.caption("No previous versions.")
                            else:
                                for vi, vp in enumerate(versions):
                                    cols_v = st.columns([3, 1])
                                    with cols_v[0]:
                                        if os.path.exists(vp):
                                            st.image(vp, width="stretch")
                                    with cols_v[1]:
                                        if st.button("Revert", key=f"revert_{c.id}_{vi}"):
                                            # swap current with selected version
                                            current = c.portrait_path
                                            selected = vp
                                            remaining = [p for p in getattr(c, "image_versions", []) if p != selected]
                                            if current:
                                                remaining.append(current)
                                            c.portrait_path = selected
                                            c.image_versions = remaining
                                            storage.update_character(c)
                                            st.success("Reverted portrait.")
                                            st.rerun()
                        with action_cols[3]:
                            if st.button("Delete", key=f"delete_{c.id}"):
                                storage.delete_character(c.id)
                                st.warning("Character deleted.")
                                st.rerun()


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

    # Show which characters are in the campaign vs not
    st.markdown("---")
    all_chars = storage.list_characters()
    in_chars = [c for c in all_chars if c.id in camp.character_ids]
    out_chars = [c for c in all_chars if c.id not in camp.character_ids]

    cols_c = st.columns(2)
    with cols_c[0]:
        st.subheader("In Campaign")
        if not in_chars:
            st.caption("None yet.")
        else:
            for c in in_chars:
                st.markdown(f"- **{c.name}** ({c.role})")
    with cols_c[1]:
        st.subheader("Not Added")
        if not out_chars:
            st.caption("All characters are added.")
        else:
            selected = st.multiselect("Choose characters to add", out_chars, format_func=lambda c: c.name, key="add_chars_ms")
            if st.button("Add to Campaign") and selected:
                for ch in selected:
                    storage.add_character_to_campaign(camp.id, ch.id)
                st.success("Characters added.")
                st.rerun()


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
        title = st.text_input("Scene Title", key="scene_title")
        prompt = st.text_area("Scene Prompt", key="scene_prompt")
        involved = st.multiselect("Characters Involved", camp_chars, format_func=lambda c: c.name, key="scene_involved")
        chapter = st.text_input("Chapter/Session (optional)", key="scene_chapter")
        uploaded_scene = st.file_uploader("Upload Scene Image (optional)", type=["png", "jpg", "jpeg"], key="scene_upload")
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
        if uploaded_scene:
            image_bytes = uploaded_scene.read()
            image_path = storage.save_image_bytes(image_bytes, f"scene-{scene.id}.png", campaign_id=camp.id, scene_id=scene.id)
        elif client:
            st.toast("Submitted: creating scene…")
            with st.status("Preparing prompt…", expanded=False) as s:
                # Combine character long prompts/description to enrich prompt
                char_prompts = []
                for ch in involved:
                    longp = getattr(ch, "long_prompt", None) or ch.description
                    char_prompts.append(f"{ch.name} ({ch.role}): {longp}")
                combined_prompt = (
                    f"Illustrate the scene: {prompt}. Characters: "
                    + "; ".join(char_prompts)
                    + (f". Render in {st.session_state.style} style." if st.session_state.style else "")
                )
                s.update(label="Generating image…", state="running")
                try:
                    img_bytes = client.generate_image(combined_prompt)
                    s.update(label="Saving image…", state="running")
                    image_path = storage.save_image_bytes(img_bytes, f"scene-{scene.id}.png", campaign_id=camp.id, scene_id=scene.id)
                    # maintain scene image versions
                    if scene.image_path:
                        if scene.image_versions is None:
                            scene.image_versions = []
                        scene.image_versions.append(scene.image_path)
                except Exception as e:
                    try:
                        summary = client.summarize_error(str(e), context="Generating scene image")
                        st.error(summary)
                    except Exception:
                        pass
                    st.exception(e)
                s.update(label="Generating caption…", state="running")
                try:
                    caption = client.caption_scene(prompt, [c.name for c in involved])
                except Exception as e:
                    try:
                        summary = client.summarize_error(str(e), context="Generating scene caption")
                        st.error(summary)
                    except Exception:
                        pass
                    st.exception(e)
                s.update(label="Done", state="complete")

        # Save results
        if image_path:
            scene.image_path = image_path
        if caption:
            scene.caption = caption
        storage.update_scene(scene)
        st.success("Scene created.")
        # Clear scene form fields
        st.session_state.scene_title = ""
        st.session_state.scene_prompt = ""
        st.session_state.scene_involved = []
        st.session_state.scene_chapter = ""
        st.rerun()
        if scene.image_path and os.path.exists(scene.image_path):
            cols_img = st.columns(2)
            with cols_img[0]:
                st.image(scene.image_path, caption=scene.caption or "", width="stretch")

    st.markdown("---")
    st.subheader("Campaign Scenes")
    if camp:
        scenes = storage.list_scenes(campaign_id=camp.id)
        for idx, sc in enumerate(scenes):
            with st.expander(f"{idx+1}. {sc.title} ({sc.chapter or 'No chapter'})"):
                if sc.image_path and os.path.exists(sc.image_path):
                    # Reduced size display in half-width column
                    st.image(sc.image_path, width="stretch")
                if sc.caption:
                    st.caption(sc.caption)
                # Reordering controls
                cols_o = st.columns(3)
                with cols_o[0]:
                    if st.button("Move Up", disabled=(idx == 0), key=f"scene_up_{sc.id}"):
                        # swap IDs in campaign ordering
                        ids = list(camp.scene_ids)
                        j = ids.index(sc.id)
                        ids[j-1], ids[j] = ids[j], ids[j-1]
                        # persist order
                        data = storage._read_json(storage.campaigns_path)
                        data[camp.id]["scene_ids"] = ids
                        storage._write_json(storage.campaigns_path, data)
                        st.rerun()
                with cols_o[1]:
                    if st.button("Move Down", disabled=(idx == len(scenes)-1), key=f"scene_down_{sc.id}"):
                        ids = list(camp.scene_ids)
                        j = ids.index(sc.id)
                        ids[j+1], ids[j] = ids[j], ids[j+1]
                        data = storage._read_json(storage.campaigns_path)
                        data[camp.id]["scene_ids"] = ids
                        storage._write_json(storage.campaigns_path, data)
                        st.rerun()
                with cols_o[2]:
                    if st.button("Edit Scene", key=f"edit_scene_{sc.id}"):
                        st.session_state[f"editing_scene_{sc.id}"] = True
                        st.rerun()
                
                # Scene editing form
                if st.session_state.get(f"editing_scene_{sc.id}", False):
                    with st.form(f"edit_scene_form_{sc.id}"):
                        new_title = st.text_input("Title", value=sc.title, key=f"edit_title_{sc.id}")
                        new_prompt = st.text_area("Prompt", value=sc.prompt, key=f"edit_prompt_{sc.id}")
                        new_caption = st.text_area("Caption", value=sc.caption or "", key=f"edit_caption_{sc.id}")
                        new_upload = st.file_uploader("New Image", type=["png", "jpg", "jpeg"], key=f"edit_upload_{sc.id}")
                        regen_img = st.checkbox("Regenerate image with AI", key=f"regen_img_{sc.id}")
                        cols_edit = st.columns(3)
                        with cols_edit[0]:
                            if st.form_submit_button("Save Changes"):
                                sc.title = new_title
                                sc.prompt = new_prompt
                                sc.caption = new_caption
                                if new_upload:
                                    # Save new uploaded image
                                    img_bytes = new_upload.read()
                                    if sc.image_path:
                                        # Archive old image
                                        if sc.image_versions is None:
                                            sc.image_versions = []
                                        sc.image_versions.append(sc.image_path)
                                    sc.image_path = storage.save_image_bytes(img_bytes, f"scene-{sc.id}.png", campaign_id=camp.id, scene_id=sc.id)
                                elif regen_img and client:
                                    try:
                                        # Archive old image
                                        if sc.image_path:
                                            if sc.image_versions is None:
                                                sc.image_versions = []
                                            sc.image_versions.append(sc.image_path)
                                        # Generate new image
                                        combined = new_prompt
                                        if camp_chars:
                                            char_prompts = []
                                            for ch in camp_chars:
                                                longp = getattr(ch, "long_prompt", None) or ch.description
                                                char_prompts.append(f"{ch.name} ({ch.role}): {longp}")
                                            combined += ". Characters: " + "; ".join(char_prompts)
                                        if st.session_state.style:
                                            combined += f". Render in {st.session_state.style} style."
                                        img_bytes = client.generate_image(combined)
                                        sc.image_path = storage.save_image_bytes(img_bytes, f"scene-{sc.id}.png", campaign_id=camp.id, scene_id=sc.id)
                                        # Generate new caption
                                        try:
                                            sc.caption = client.caption_scene(new_prompt, [c.name for c in camp_chars])
                                        except Exception:
                                            pass
                                    except Exception as e:
                                        st.error(f"Image generation failed: {e}")
                                storage.update_scene(sc)
                                st.session_state[f"editing_scene_{sc.id}"] = False
                                st.success("Scene updated.")
                                st.rerun()
                        with cols_edit[1]:
                            if st.form_submit_button("Cancel"):
                                st.session_state[f"editing_scene_{sc.id}"] = False
                                st.rerun()
                        with cols_edit[2]:
                            if st.form_submit_button("Delete Scene"):
                                storage.delete_scene(sc.id)
                                st.session_state[f"editing_scene_{sc.id}"] = False
                                st.warning("Scene deleted.")
                                st.rerun()
                
                # Quick delete button (outside edit form)
                if st.button("Delete Scene", key=f"quick_delete_{sc.id}"):
                    storage.delete_scene(sc.id)
                    st.warning("Scene deleted.")
                    st.rerun()
                
                with st.expander("Image history"):
                    versions = list(reversed(getattr(sc, "image_versions", []) or []))
                    if not versions:
                        st.caption("No previous versions.")
                    else:
                        for vi, vp in enumerate(versions):
                            cols_v = st.columns([3, 1])
                            with cols_v[0]:
                                if os.path.exists(vp):
                                    st.image(vp, width="stretch")
                            with cols_v[1]:
                                if st.button("Revert", key=f"revert_scene_{sc.id}_{vi}"):
                                    current = sc.image_path
                                    selected = vp
                                    remaining = [p for p in getattr(sc, "image_versions", []) if p != selected]
                                    if current:
                                        remaining.append(current)
                                    sc.image_path = selected
                                    sc.image_versions = remaining
                                    storage.update_scene(sc)
                                    st.success("Reverted scene image.")
                                    st.rerun()


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

    # MP4 montage with gentle zoom
    secs = st.number_input("Seconds per scene (MP4)", min_value=2.0, max_value=15.0, value=4.0, step=0.5)
    if st.button("Generate MP4 Montage"):
        try:
            with st.status("Rendering video…", expanded=False) as s:
                s.update(label="Compositing scenes…", state="running")
                path = montage.export_mp4(camp.name, scenes, seconds_per_scene=float(secs))
                s.update(label="Video ready", state="complete")
            with open(path, "rb") as f:
                st.download_button("Download MP4", f, file_name=os.path.basename(path))
        except Exception as e:
            client = _ensure_openai()
            if client:
                try:
                    st.error(client.summarize_error(str(e), context="Generating MP4 montage"))
                except Exception:
                    pass
            st.exception(e)

    if client and st.button("Generate Text Recap"):
        pairs = [(s.title, s.caption or "") for s in scenes]
        try:
            recap = client.recap_text(pairs)
            st.text_area("Session Recap", recap, height=200)
        except Exception as e:
            st.error(f"Recap failed: {e}")

    # Extend montage: propose and generate N future scenes
    st.markdown("---")
    st.subheader("Extend Montage")
    steps = st.slider("How many future steps?", min_value=1, max_value=6, value=3)
    if client and st.button("Propose and Generate Future Scenes"):
        try:
            base_context = "\n".join([f"{s.title}: {s.caption or s.prompt}" for s in scenes])
            with st.status("Proposing future scenes…", expanded=True) as sbox:
                sbox.update(label="Querying model…", state="running")
                proposals = client.propose_future_scenes_with_titles(base_context, steps=int(steps))
                st.write("Proposals (title and prompt):")
                for j, (ttl, pp) in enumerate(proposals, start=1):
                    st.write(f"{j}. {ttl} — {pp}")
                sbox.update(label="Generating images…", state="running")
                prog = st.progress(0)
                total = max(1, len(proposals))
                # Gather characters used so far in this campaign
                involved_char_ids = []
                for s in scenes:
                    for cid in (s.character_ids or []):
                        if cid not in involved_char_ids:
                            involved_char_ids.append(cid)
                all_chars = st.session_state.storage.list_characters()
                involved_chars = [c for c in all_chars if c.id in involved_char_ids]
                char_prompts = []
                for ch in involved_chars:
                    longp = getattr(ch, "long_prompt", None) or ch.description
                    char_prompts.append(f"{ch.name} ({ch.role}): {longp}")
                for i, (ttl, p) in enumerate(proposals, start=1):
                    st.write(f"Rendering step {i}/{total}…")
                    combined = p
                    if char_prompts:
                        combined += ". Characters: " + "; ".join(char_prompts)
                    if st.session_state.style:
                        combined += f". Render in {st.session_state.style} style."
                    img_bytes = client.generate_image(combined)
                    scene = storage.create_scene(
                        campaign_id=camp.id,
                        title=ttl or f"Future {i}",
                        prompt=p,
                        character_ids=involved_char_ids,
                        style=st.session_state.style or None,
                        chapter=None,
                    )
                    img_path = storage.save_image_bytes(img_bytes, f"scene-{scene.id}.png", campaign_id=camp.id, scene_id=scene.id)
                    scene.image_path = img_path
                    # Generate a caption to ensure narrative continuity
                    try:
                        cap = client.caption_scene(p, [c.name for c in involved_chars])
                        scene.caption = cap
                    except Exception:
                        pass
                    storage.update_scene(scene)
                    prog.progress(int(i * 100 / total))
                sbox.update(label="Done", state="complete")
            st.success("Extended montage with future scenes.")
            st.rerun()
        except Exception as e:
            try:
                st.error(client.summarize_error(str(e), context="Extending montage"))
            except Exception:
                pass
            st.exception(e)


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


