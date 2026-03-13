import os
import whisper
import argparse
import ssl
from groq import Groq
from dotenv import load_dotenv
from moviepy import VideoFileClip

# FIX: SSL Certificate issue on Mac
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov', '.avi', '.flv', '.wmv')
AUDIO_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.flac')

def handle_input_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext in VIDEO_EXTENSIONS:
        print(f"Video detected. Extracting audio...")
        video = VideoFileClip(file_path)
        audio_path = "temp_extracted_audio.wav"
        video.audio.write_audiofile(audio_path, codec='pcm_s16le', fps=16000, logger=None)
        video.close()
        return audio_path, True
    return file_path, False

def transcribe_audio(file_path, model_name="base"):
    print(f"Loading Whisper...")
    model = whisper.load_model(model_name)
    result = model.transcribe(file_path)
    return result.get("text", "")

def analyze_with_groq(text, api_key):
    client = Groq(api_key=api_key)
    safe_text = text[:15000]

    system_message = """You are a senior GHL (GoHighLevel) Technical Architect with deep expertise in CRM automation, funnel building, workflow design, and AI-powered client engagement systems.

Your role is to produce professional, implementation-ready Technical Approach Documents that a development team can directly follow. Write with precision, use proper markdown formatting, and ensure every recommendation is actionable and specific to the client's needs as discussed in the transcription."""

    prompt = f"""Analyze the following meeting transcription and generate a comprehensive **TECHNICAL APPROACH DOCUMENT**.

**RULES:**
- Base the document STRICTLY on what is discussed or implied in the transcription. Do NOT fabricate details.
- OMIT any section that is NOT relevant to the transcription (e.g., skip Chatbots if never mentioned).
- Use professional markdown formatting with headers, tables, and bullet points.
- Be specific with field names, pipeline stage names, workflow triggers, and automation logic.
- Where the transcription is vague, note it as a "Clarification Needed" item.

---

**DOCUMENT STRUCTURE** (include only relevant sections):

# 1. PROJECT HEADER
| Field | Details |
|-------|---------|
| Client Name | (extract from transcription) |
| Company | (extract from transcription) |
| Industry | (extract or infer from context) |
| Date | (today's date or meeting date if mentioned) |
| Document Type | GHL Technical Approach |

# 2. PROJECT OVERVIEW & OBJECTIVES
- Summarize the business problem the client wants to solve.
- List 3-5 specific, measurable objectives discussed in the meeting.
- Identify the target audience or customer segment if mentioned.

# 3. PROPOSED SOLUTION
Include ONLY the sub-sections that apply:

## 3.1 Lead Qualification & Custom Forms
- List each form needed with specific field names and field types.
- Define qualification logic (e.g., conditional fields, scoring criteria).
- Specify where forms will be embedded or triggered.

## 3.2 Funnels & Landing Pages
- Describe each funnel step (landing page → thank you page → upsell, etc.).
- Note key elements per page: headline focus, CTA text, form placement.
- Mention any A/B testing or tracking requirements.

## 3.3 Calendar & Scheduling
- Define calendar type (Round Robin, Collective, Class Booking, etc.).
- Specify booking rules: availability windows, buffer times, meeting duration.
- Note any pre-booking qualification steps.

## 3.4 Pipeline & Deal Tracking
- Define each pipeline with its stages (e.g., New Lead → Contacted → Qualified → Proposal Sent → Won/Lost).
- Specify stage-transition triggers (manual vs. automated).
- Note any monetary values or probability percentages per stage.

## 3.5 Proposals, Contracts & Payments
- Define the proposal/estimate template structure.
- Specify e-signature requirements.
- Detail payment integration (Stripe, etc.), pricing tiers, and invoicing logic.

## 3.6 Automation Workflows
For each workflow, specify:
- **Trigger:** What starts it (e.g., form submission, tag added, pipeline stage change).
- **Actions:** Step-by-step sequence (emails, SMS, wait steps, internal notifications).
- **Conditions:** Any If/Else branching logic.
- **Goal:** What ends the workflow early (e.g., appointment booked).

Common workflows to consider (include only if relevant):
- New Lead Nurture Sequence
- Appointment Confirmation & Reminders
- No-Show / Cancellation Follow-Up
- Post-Meeting Follow-Up
- Re-engagement Campaign
- Internal Team Notifications

## 3.7 AI & Chatbot Configuration
- Define the chat widget placement and trigger rules.
- Specify the AI bot's role, tone, and conversation boundaries.
- List the intents/scenarios the bot should handle.
- Define handoff rules to a live agent.

# 4. INTEGRATIONS & TECHNICAL REQUIREMENTS
- List any third-party integrations mentioned (Zapier, Google Sheets, Stripe, Calendly, etc.).
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

# 7. IMPLEMENTATION TIMELINE
- Break the project into logical phases (Phase 1: Setup, Phase 2: Automation, Phase 3: Launch, etc.).
- List key deliverables per phase.

# 8. CLARIFICATIONS NEEDED
- List any ambiguous points from the transcription that require client confirmation before implementation.

---

**TRANSCRIPTION:**
{safe_text}
"""

    print("Generating Tailored GHL Technical Approach...")
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="/Users/theonetech/Documents/Project/Technical approach/Impromptu Google Meet Meeting - Feb 20 2026.mp4")
    args = parser.parse_args()

    temp_audio_used = False
    try:
        process_path, temp_audio_used = handle_input_file(args.file)
        transcription = transcribe_audio(process_path)

        analysis = analyze_with_groq(transcription, os.getenv("GROQ_API_KEY"))

        output_file = "GHL_Technical_Approach.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(analysis)

        print(f"\n✅ Custom document generated: {output_file}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if temp_audio_used and os.path.exists(process_path):
            os.remove(process_path)

if __name__ == "__main__":
    main()