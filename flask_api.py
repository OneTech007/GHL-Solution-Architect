import os
import ssl
import uuid
import whisper
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from moviepy import VideoFileClip
import re
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from flask import Flask, request, jsonify, send_file, url_for

ssl._create_default_https_context = ssl._create_unverified_context
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv')
AUDIO_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.flac')

app = Flask(__name__)


# ─── Core Functions (same as app.py) ────────────────────────────────

def extract_audio(video_path: str) -> str:
    audio_path = str(UPLOAD_DIR / f"{uuid.uuid4().hex}.wav")
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path, codec='pcm_s16le', fps=16000, logger=None)
    video.close()
    return audio_path


def transcribe_audio(file_path: str, model_name: str = "base") -> str:
    model = whisper.load_model(model_name)
    result = model.transcribe(file_path)
    return result.get("text", "")


def analyze_with_groq(text: str, instructions: str = "") -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    safe_text = text[:15000]

    system_message = """You are a senior GHL (GoHighLevel) Technical Architect with deep expertise in CRM automation, funnel building, workflow design, and AI-powered client engagement systems.

Your role is to produce professional, implementation-ready Technical Approach Documents that a development team can directly follow. Write with precision, use proper markdown formatting, and ensure every recommendation is actionable and specific to the client's needs."""

    if safe_text.strip():
        source_context = "meeting transcription"
        source_rule = "- Base the document STRICTLY on what is discussed or implied in the transcription. Do NOT fabricate details."
    else:
        source_context = "instructions/notes provided"
        source_rule = "- Base the document STRICTLY on the instructions/notes provided. Use them as the project brief and build a complete technical approach around them."

    prompt = f"""Analyze the following {source_context} and generate a comprehensive **TECHNICAL APPROACH DOCUMENT**.

**RULES:**
{source_rule}
- OMIT any section that is NOT relevant to the {source_context} (e.g., skip Chatbots if never mentioned).
- Use professional markdown formatting with headers, tables, and bullet points.
- Be specific with field names, pipeline stage names, workflow triggers, and automation logic.
- Where the transcription is vague or details are missing, DO NOT ask the client for information. Instead, suggest the most appropriate values, configurations, or approaches based on industry best practices and context clues from the transcription. Clearly mark these as "Suggested:" so the team knows they are recommendations rather than confirmed requirements.
- Provide FULL DETAILED step-by-step breakdowns for every workflow, pipeline, funnel, and website section. Do not summarize — list every individual step, trigger, action, condition, and outcome.
- For any website or landing page, specify whether it should be built using GHL native builder or custom HTML, and detail every section/block of the page.
- Each module must include a numbered step-by-step implementation guide.
- Include a table of all third-party tools/integrations required with their purpose, cost (if known), and integration method.
- Include a Prerequisites section listing everything needed before implementation can begin.

---

**DOCUMENT STRUCTURE** (include only relevant sections):

# Technical Approach : [Client Name or Company Name]
(Extract client/company name from the transcription or suggest based on context. This is the document title — do NOT include a separate project header table.)

# 1. PROJECT OBJECTIVES
- Summarize the business problem the client wants to solve.
- List 3-5 specific, measurable objectives discussed in the meeting.
- Identify the target audience or customer segment if mentioned.

# 2. FEATURE LISTING
Provide a summary table of ALL features/modules that will be implemented:
| # | Feature/Module | Description | Build Method |
|---|---|---|---|
| 1 | (e.g., Lead Capture Funnel) | (brief description) | (GHL Native / Custom HTML / API) |
| 2 | ... | ... | ... |
(List every feature discussed — this gives a quick overview before the detailed breakdown.)

# 3. FEATURE DETAILING
For EACH feature listed in the table above, provide a full detailed breakdown with numbered implementation steps:

## 3.1 Lead Qualification & Custom Forms
- List each form needed with specific field names, field types, and validation rules.
- Define qualification logic (e.g., conditional fields, scoring criteria).
- Specify where forms will be embedded or triggered.
- **Steps:** Number each implementation step (Step 1: Create form in GHL > Sites > Forms, Step 2: Add fields..., etc.).

## 3.2 Funnels & Landing Pages
- Describe each funnel step (landing page -> thank you page -> upsell, etc.).
- For each page, specify: **Build Method** (GHL Native Builder or Custom HTML).
- Detail every section/block of each page: hero section, features, testimonials, CTA, form placement, footer, etc.
- Note headline focus, CTA text, color scheme, and form placement per page.
- Mention any A/B testing or tracking requirements.
- **Steps:** Number each implementation step.

## 3.3 Website (if applicable)
- Specify **Build Method:** GHL Native Builder or Custom HTML.
- Detail every page needed (Home, About, Services, Contact, etc.).
- For each page, list every section/block with content guidance.
- Specify navigation structure, header, and footer layout.
- **Steps:** Number each implementation step.

## 3.4 Calendar & Scheduling
- Define calendar type (Round Robin, Collective, Class Booking, etc.).
- Specify booking rules: availability windows, buffer times, meeting duration.
- Note any pre-booking qualification steps.
- **Steps:** Number each implementation step.

## 3.5 Pipeline & Deal Tracking
- Define each pipeline with ALL its stages listed in order (e.g., New Lead -> Contacted -> Qualified -> Proposal Sent -> Won/Lost).
- For EACH stage, specify: stage name, stage actions, automation triggers, manual actions required, and transition criteria to next stage.
- Specify stage-transition triggers (manual vs. automated).
- Note any monetary values or probability percentages per stage.
- **Steps:** Number each implementation step.

## 3.6 Proposals, Contracts & Payments
- Define the proposal/estimate template structure.
- Specify e-signature requirements.
- Detail payment integration (Stripe, etc.), pricing tiers, and invoicing logic.
- **Steps:** Number each implementation step.

## 3.7 Automation Workflows
For EACH workflow, provide a FULL detailed breakdown:
- **Workflow Name:** Descriptive name
- **Trigger:** What starts it (e.g., form submission, tag added, pipeline stage change).
- **Detailed Step-by-Step Actions:** List EVERY action in sequence with wait times, conditions, and content:
  - Step 1: [Action type] - [Details]
  - Step 2: Wait [duration]
  - Step 3: If/Else [condition] - Yes branch: [actions] / No branch: [actions]
  - (continue for ALL steps)
- **Goal/Exit Condition:** What ends the workflow early (e.g., appointment booked).

Common workflows to consider (include only if relevant):
- New Lead Nurture Sequence
- Appointment Confirmation & Reminders
- No-Show / Cancellation Follow-Up
- Post-Meeting Follow-Up
- Re-engagement Campaign
- Internal Team Notifications
- Pipeline Stage Automation

## 3.8 AI & Chatbot Configuration
- Define the chat widget placement and trigger rules.
- Specify the AI bot's role, tone, and conversation boundaries.
- List the intents/scenarios the bot should handle.
- Define handoff rules to a live agent.
- **Steps:** Number each implementation step.

# 4. THIRD-PARTY INTEGRATIONS & TOOLS
Provide a table with ALL third-party tools required:
| Tool/Service | Purpose | Integration Method | Required Plan/Cost | Priority |
|---|---|---|---|---|
| (list each tool) | | (API/Zapier/Webhook/Native) | | (Must-have/Nice-to-have) |

- Note any custom webhook or API requirements.
- Specify domain, DNS, or hosting considerations.

# 5. DASHBOARD & REPORTING
- Define 3-5 key KPIs to track based on project goals.
- Suggest a reporting dashboard layout with specific widgets.
- Note any automated report delivery (email summaries, Slack alerts).

# 6. AGENT / TEAM MANUAL RESPONSIBILITIES
- List specific manual actions the team must perform daily/weekly.
- Define SOPs for pipeline management and lead follow-up.
- Specify any data hygiene tasks (e.g., updating contact statuses, clearing stale leads).

# 7. SUGGESTIONS & ASSUMPTIONS
- For any ambiguous or missing details, provide your best-practice recommendations with clear reasoning.
- Mark each suggestion with "Suggested:" prefix so the team can review and confirm.
- Do NOT frame these as questions to the client — instead, propose a concrete solution or configuration for each gap.

# 8. PREREQUISITES
List everything required before implementation can begin:
- GHL sub-account setup requirements
- Domain and DNS configurations needed
- Third-party account credentials required
- Content/assets the client must provide (logos, copy, images, etc.)
- Access permissions needed
- Any existing systems that need to be audited or migrated

# 9. NEXT STEPS
- If based on the call the client seems interested to move further, include this note: "Please provide GHL sub-account access to dev.patel@theonetechnologies.co.in to begin implementation."
- List immediate action items for both the client and the development team.

---

{f"**ADDITIONAL INSTRUCTIONS FROM THE TEAM:**" + chr(10) + instructions + chr(10) + "---" + chr(10) if instructions.strip() else ""}
{f"**TRANSCRIPTION:**" + chr(10) + safe_text if safe_text.strip() else "**NOTE:** No transcription provided. Generate the document based entirely on the additional instructions above."}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=8000,
        top_p=0.9,
    )
    return response.choices[0].message.content


def add_formatted_runs(paragraph, text):
    """Parse markdown inline formatting (**bold**, *italic*) and add runs to paragraph."""
    # Split by ** for bold
    parts = re.split(r'(\*\*.*?\*\*)', text)
    for part in parts:
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            inner = part[2:-2]
            run = paragraph.add_run(inner)
            run.bold = True
        elif '*' in part:
            # Handle single * italic within remaining text
            sub_parts = re.split(r'(\*[^*]+?\*)', part)
            for sp in sub_parts:
                if not sp:
                    continue
                if sp.startswith('*') and sp.endswith('*') and len(sp) > 2:
                    run = paragraph.add_run(sp[1:-1])
                    run.italic = True
                else:
                    paragraph.add_run(sp)
        else:
            paragraph.add_run(part)

    # Apply font to all runs
    for run in paragraph.runs:
        run.font.name = 'Calibri'
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)


def flush_table(doc, table_rows):
    """Render collected table rows into a properly formatted DOCX table."""
    if not table_rows:
        return
    num_cols = max(len(r) for r in table_rows)
    table = doc.add_table(rows=len(table_rows), cols=num_cols)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Set table to auto-fit
    table.autofit = True

    for ri, row_data in enumerate(table_rows):
        for ci in range(num_cols):
            cell = table.rows[ri].cells[ci]
            cell_text = row_data[ci] if ci < len(row_data) else ""
            # Clear default paragraph and write formatted text
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_formatted_runs(p, cell_text)

            # Style header row
            if ri == 0:
                for run in p.runs:
                    run.bold = True
                    run.font.size = Pt(10)
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                # Dark header background
                shading = cell._element.get_or_add_tcPr()
                shading_elm = shading.makeelement(qn('w:shd'), {
                    qn('w:fill'): 'B92328',
                    qn('w:val'): 'clear'
                })
                shading.append(shading_elm)
            else:
                for run in p.runs:
                    run.font.size = Pt(10)
                # Alternate row shading
                if ri % 2 == 0:
                    shading = cell._element.get_or_add_tcPr()
                    shading_elm = shading.makeelement(qn('w:shd'), {
                        qn('w:fill'): 'F5F5F5',
                        qn('w:val'): 'clear'
                    })
                    shading.append(shading_elm)

    doc.add_paragraph()  # spacing after table


def markdown_to_docx(markdown_text: str, output_path: str) -> str:
    doc = Document()

    # ── Page margins
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # ── Base styles
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    style.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.15

    for level, size in [('Heading 1', 18), ('Heading 2', 14), ('Heading 3', 12)]:
        s = doc.styles[level]
        s.font.color.rgb = RGBColor(0xB9, 0x23, 0x28)
        s.font.name = 'Calibri'
        s.font.size = Pt(size)
        s.font.bold = True
        s.paragraph_format.space_before = Pt(18 if level == 'Heading 1' else 12)
        s.paragraph_format.space_after = Pt(6)

    lines = markdown_text.split('\n')
    i = 0
    table_rows = []
    in_table = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── Table rows
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            # Skip separator rows like |---|---|
            if all(set(c) <= set('-: ') for c in cells):
                i += 1
                continue
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            flush_table(doc, table_rows)
            table_rows = []
            in_table = False
            # Don't increment — process current line

        # ── Empty lines
        if not stripped:
            i += 1
            continue

        # ── Headings
        if stripped.startswith('### '):
            heading_text = stripped[4:].strip().strip('*#').strip()
            doc.add_heading(heading_text, level=3)
        elif stripped.startswith('## '):
            heading_text = stripped[3:].strip().strip('*#').strip()
            doc.add_heading(heading_text, level=2)
        elif stripped.startswith('# '):
            heading_text = stripped[2:].strip().strip('*#').strip()
            doc.add_heading(heading_text, level=1)

        # ── Horizontal rule
        elif stripped.startswith('---'):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run('_' * 60)
            run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
            run.font.size = Pt(8)

        # ── Sub-bullet (indented: "  - " or "    - ")
        elif re.match(r'^(\s{2,})([-*])\s', line):
            text = re.sub(r'^\s+[-*]\s', '', line)
            p = doc.add_paragraph(style='List Bullet 2')
            p.paragraph_format.left_indent = Cm(2)
            add_formatted_runs(p, text)

        # ── Top-level bullet
        elif stripped.startswith('- ') or stripped.startswith('* '):
            text = stripped[2:]
            p = doc.add_paragraph(style='List Bullet')
            add_formatted_runs(p, text)

        # ── Numbered list (e.g., "1. ", "12. ", "Step 1:")
        elif re.match(r'^\d+[\.\)]\s', stripped):
            match = re.match(r'^(\d+)[\.\)]\s*(.*)', stripped)
            if match:
                num = match.group(1)
                text = match.group(2)
                p = doc.add_paragraph(style='List Number')
                add_formatted_runs(p, text)

        # ── Regular paragraph
        else:
            p = doc.add_paragraph()
            add_formatted_runs(p, stripped)

        i += 1

    # Flush any remaining table
    if in_table and table_rows:
        flush_table(doc, table_rows)

    doc.save(output_path)
    return output_path


# ─── Flask API Routes ───────────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def generate():
    """
    Generate a GHL Technical Approach Document.

    Accepts multipart/form-data:
      - file (optional): video or audio file
      - instructions (optional): text notes/instructions

    At least one of file or instructions must be provided.

    Returns the DOCX file directly as a download.
    """
    file = request.files.get("file")
    instructions = request.form.get("instructions", "").strip()

    has_file = file is not None and file.filename
    if not has_file and not instructions:
        return jsonify({"error": "Please provide either a file or instructions."}), 400

    file_id = uuid.uuid4().hex
    upload_path = None
    temp_audio = None

    try:
        transcription = ""

        if has_file:
            file_ext = os.path.splitext(file.filename)[1].lower()

            if file_ext not in VIDEO_EXTENSIONS + AUDIO_EXTENSIONS:
                return jsonify({
                    "error": f"Unsupported file type: {file_ext}",
                    "supported_video": list(VIDEO_EXTENSIONS),
                    "supported_audio": list(AUDIO_EXTENSIONS)
                }), 400

            upload_path = str(UPLOAD_DIR / f"{file_id}{file_ext}")
            file.save(upload_path)

            if file_ext in VIDEO_EXTENSIONS:
                audio_path = extract_audio(upload_path)
                temp_audio = audio_path
            else:
                audio_path = upload_path

            transcription = transcribe_audio(audio_path)

        analysis = analyze_with_groq(transcription, instructions)

        docx_filename = f"GHL_Solution_Architect_{file_id}.docx"
        docx_path = str(UPLOAD_DIR / docx_filename)
        markdown_to_docx(analysis, docx_path)

        return send_file(
            docx_path,
            as_attachment=True,
            download_name="GHL_Solution_Architect.docx",
            mimetype="application/octet-stream"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if upload_path and os.path.exists(upload_path):
            os.remove(upload_path)
        if temp_audio and os.path.exists(temp_audio):
            os.remove(temp_audio)


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "GHL Solution Architect API"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
