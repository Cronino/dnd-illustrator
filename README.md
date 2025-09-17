## DnD Story Illustrator

Python app to create characters, illustrate scenes, and export end-of-session montages for tabletop RPG campaigns.

### Features
- Character setup with text and optional reference image
- Scene illustration via OpenAI Images with consistent character prompts
- AI captions and optional session recap
- Campaign management with character linking and chapters
- Montage export to PDF

### Tech
- Python 3.10+
- Streamlit UI
- OpenAI Chat + Images
- ReportLab for PDF

### Setup (WSL2 + uv recommended)
If you're on Windows, use WSL2 and run the app inside Linux.

Using uv (fast Python package manager):
```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtualenv
uv venv .venv
source .venv/bin/activate

# Install project (from pyproject)
uv pip install -e .
```

Alternatively with pip on Windows PowerShell:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Provide your OpenAI API key either:
   - In the app sidebar when running, or
   - As environment variable before launch:
```bash
$env:OPENAI_API_KEY="YOUR_KEY_HERE"
```

On Linux/WSL Bash:
```bash
export OPENAI_API_KEY="YOUR_KEY_HERE"
```

### Run
```bash
# Inside WSL2 / Linux shell
streamlit run app/main.py
```

Open the local URL printed by Streamlit.

### Usage Outline
1. Characters tab: create characters; optionally expand description with AI.
2. Campaigns tab: create a campaign and add characters to it.
3. Scenes tab: enter a scene prompt, select involved characters, generate illustration + caption.
4. Montage tab: export PDF montage and optionally generate a text recap.

### Notes
- Data is stored as JSON under `data/`. Images are saved under `data/images/`.
- This app uses `gpt-4o-mini` for text and `gpt-image-1` for images. You can change models in `services/openai_service.py`.
- If image generation fails, verify your OpenAI account has image access and sufficient quota.

## DnD Story Illustrator

Python app to create characters, illustrate scenes, and export end-of-session montages for tabletop RPG campaigns.

### Features
- Character setup with text and optional reference image
- Scene illustration via OpenAI Images with consistent character prompts
- AI captions and optional session recap
- Campaign management with character linking and chapters
- Montage export to PDF

### Tech
- Python 3.10+
- Streamlit UI
- OpenAI Chat + Images
- ReportLab for PDF

### Setup
1. Create a virtual environment (recommended):
```bash
python -m venv .venv
.venv\\Scripts\\activate
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Provide your OpenAI API key either:
   - In the app sidebar when running, or
   - As environment variable before launch:
```bash
$env:OPENAI_API_KEY="YOUR_KEY_HERE"
```

### Run
```bash
streamlit run app/main.py
```

Open the local URL printed by Streamlit.

### Usage Outline
1. Characters tab: create characters; optionally expand description with AI.
2. Campaigns tab: create a campaign and add characters to it.
3. Scenes tab: enter a scene prompt, select involved characters, generate illustration + caption.
4. Montage tab: export PDF montage and optionally generate a text recap.

### Notes
- Data is stored as JSON under `data/`. Images are saved under `data/images/`.
- This app uses `gpt-4o-mini` for text and `gpt-image-1` for images. You can change models in `services/openai_service.py`.
- If image generation fails, verify your OpenAI account has image access and sufficient quota.


