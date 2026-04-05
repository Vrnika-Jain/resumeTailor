import streamlit as st
from groq import Groq
import os
import io
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from fpdf import FPDF

st.set_page_config(
    page_title="Resume Tailor",
    page_icon="📄",
    layout="centered"
)

st.markdown("""
    <style>
    .block-container { max-width: 720px; padding-top: 2rem; }
    .stTextArea textarea { font-size: 14px; }
    .stDownloadButton button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

def tailor_with_groq(resume: str, jd: str, api_key: str) -> str:
    # Priority: UI input → secrets.toml → environment variable
    key = (
        api_key.strip()
        or st.secrets.get("GROQ_API_KEY", "")
        or os.environ.get("GROQ_API_KEY", "")
    )
    if not key:
        raise ValueError("No API key provided.")

    client = Groq(api_key=key)

    prompt = f"""You are an expert resume writer and ATS optimization specialist.

TASK: Rewrite the candidate's resume to perfectly target the job description below.

FORMATTING RULES (follow exactly):
- Line 1: Candidate full name (name only)
- Line 2: Contact info separated by | (email | phone | LinkedIn | location)
- Then sections in this order: SUMMARY, EXPERIENCE, SKILLS, EDUCATION
- Each section header in ALL CAPS on its own line
- Under EXPERIENCE: each role starts with "ROLE: Job Title | Company | Start - End"
- Bullet points start with "- " (dash space)
- Skills listed as comma-separated values under SKILLS
- Education: "Degree | Institution | Year"
- Blank line between each section

INSTRUCTIONS:
1. Extract the most important keywords, skills, and phrases from the job description.
2. Naturally weave these into the summary, bullets, and skills section.
3. Rewrite bullets to emphasize accomplishments relevant to this role.
4. Write a targeted 3-4 line summary specifically for this role.
5. Do NOT invent experience the candidate does not have - only reframe existing experience.
6. Use strong action verbs. Be concise and impactful.

CANDIDATE RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Output ONLY the tailored resume. No commentary, no explanations, no markdown.
"""

    msg = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.7
    )
    return msg.choices[0].message.content.strip()

def parse_resume(text: str) -> dict:
    lines = [l.rstrip() for l in text.split("\n")]
    data = {"name": "", "contact": "", "sections": []}
    if lines:
        data["name"] = lines[0].strip()
    if len(lines) > 1:
        data["contact"] = lines[1].strip()
    current_section = None
    headers = {"SUMMARY", "EXPERIENCE", "SKILLS", "EDUCATION", "CERTIFICATIONS", "PROJECTS"}
    for line in lines[2:]:
        s = line.strip()
        if s.upper() in headers:
            current_section = {"title": s.upper(), "lines": []}
            data["sections"].append(current_section)
        elif current_section and s:
            current_section["lines"].append(s)
    return data

def sanitize(text: str) -> str:
    return (text
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2022", "-")
        .replace("\u00e9", "e")
        .replace("\u00e0", "a")
        .replace("\u00e1", "a")
        .replace("\u00e8", "e")
        .replace("\u00ea", "e")
        .replace("\u00eb", "e")
        .replace("\u00ef", "i")
        .replace("\u00ee", "i")
        .replace("\u00f4", "o")
        .replace("\u00f6", "o")
        .replace("\u00fa", "u")
        .replace("\u00fb", "u")
        .replace("\u00fc", "u")
        .replace("\u00f1", "n")
        .replace("\u00e7", "c")
        .replace("\u2026", "...")
        .replace("\u00b7", "-")
        .replace("\u00ae", "(R)")
        .replace("\u00a9", "(C)")
        .replace("\u2122", "(TM)")
    )


def build_pdf(data: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(auto=True, margin=16)

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(15, 15, 15)
    pdf.cell(0, 12, sanitize(data["name"]), ln=True, align="C")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 5, sanitize(data["contact"]), ln=True, align="C")

    pdf.ln(3)
    pdf.set_draw_color(15, 15, 15)
    pdf.set_line_width(0.8)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(5)

    for sec in data["sections"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 15, 15)
        pdf.cell(0, 6, sanitize(sec["title"]), ln=True)

        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.3)
        pdf.line(18, pdf.get_y(), 192, pdf.get_y())
        pdf.ln(3)

        for line in sec["lines"]:
            if line.startswith("ROLE:"):
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(15, 15, 15)
                pdf.multi_cell(0, 6, sanitize(line.replace("ROLE:", "").strip()))
            elif line.startswith("- "):
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(40, 40, 40)
                pdf.set_x(pdf.get_x() + 5)
                pdf.multi_cell(165, 5.2, "•  " + sanitize(line[2:]))
            else:
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(0, 5.2, sanitize(line))

        pdf.ln(5)

    return bytes(pdf.output())

def build_docx(data: dict) -> bytes:
    doc = Document()

    for section in doc.sections:
        section.top_margin    = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin   = Inches(0.85)
        section.right_margin  = Inches(0.85)

    name_p = doc.add_paragraph()
    name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_p.paragraph_format.space_after = Pt(2)
    nr = name_p.add_run(data["name"])
    nr.bold = True
    nr.font.size = Pt(22)
    nr.font.color.rgb = RGBColor(0x0f, 0x0f, 0x0f)

    contact_p = doc.add_paragraph()
    contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contact_p.paragraph_format.space_after = Pt(6)
    cr = contact_p.add_run(data["contact"])
    cr.font.size = Pt(9)
    cr.font.color.rgb = RGBColor(0x5a, 0x5a, 0x5a)

    div_p = doc.add_paragraph()
    div_p.paragraph_format.space_after = Pt(6)
    pPr = div_p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bot = OxmlElement('w:bottom')
    bot.set(qn('w:val'), 'single')
    bot.set(qn('w:sz'), '12')
    bot.set(qn('w:space'), '1')
    bot.set(qn('w:color'), '0f0f0f')
    pBdr.append(bot)
    pPr.append(pBdr)

    for sec in data["sections"]:
        head_p = doc.add_paragraph()
        head_p.paragraph_format.space_before = Pt(8)
        head_p.paragraph_format.space_after  = Pt(1)
        hr = head_p.add_run(sec["title"])
        hr.bold = True
        hr.font.size = Pt(10)
        hr.font.color.rgb = RGBColor(0x0f, 0x0f, 0x0f)
        hPr = head_p._p.get_or_add_pPr()
        hBdr = OxmlElement('w:pBdr')
        hBot = OxmlElement('w:bottom')
        hBot.set(qn('w:val'), 'single')
        hBot.set(qn('w:sz'), '4')
        hBot.set(qn('w:space'), '1')
        hBot.set(qn('w:color'), 'b4b4b4')
        hBdr.append(hBot)
        hPr.append(hBdr)

        for line in sec["lines"]:
            lp = doc.add_paragraph()
            lp.paragraph_format.space_before = Pt(0)
            lp.paragraph_format.space_after  = Pt(2)
            if line.startswith("ROLE:"):
                lp.paragraph_format.space_before = Pt(4)
                lr = lp.add_run(line.replace("ROLE:", "").strip())
                lr.bold = True
                lr.font.size = Pt(10)
                lr.font.color.rgb = RGBColor(0x0f, 0x0f, 0x0f)
            elif line.startswith("- "):
                lp.paragraph_format.left_indent = Inches(0.18)
                lp.paragraph_format.space_after = Pt(1)
                lr = lp.add_run("\u2022  " + line[2:])
                lr.font.size = Pt(9.5)
                lr.font.color.rgb = RGBColor(0x28, 0x28, 0x28)
            else:
                lr = lp.add_run(line)
                lr.font.size = Pt(9.5)
                lr.font.color.rgb = RGBColor(0x28, 0x28, 0x28)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

st.title("📄 Resume Tailor")
st.caption("Paste your resume and a job description — get a tailored, ATS-ready resume in seconds.")
st.divider()

has_key = bool(
    st.secrets.get("GROQ_API_KEY", "")
    or os.environ.get("GROQ_API_KEY", "")
)

if has_key:
    api_key = ""
    st.info("🔑 API key loaded — you're good to go.", icon="✅")
else:
    api_key = st.text_input(
        "Groq API key",
        type="password",
        placeholder="gsk_...",
        help="Free API key from console.groq.com — no credit card needed."
    )

col1, col2 = st.columns(2)
with col1:
    resume_input = st.text_area(
        "Your current resume",
        height=280,
        placeholder="Paste your resume here — work experience, skills, education, everything."
    )
with col2:
    jd_input = st.text_area(
        "Job description",
        height=280,
        placeholder="Paste the full job posting here — requirements, responsibilities, qualifications."
    )

if st.button("✨ Tailor my resume", type="primary", use_container_width=True):
    if not has_key and not api_key.strip():
        st.error("Please enter your Groq API key.")
    elif not resume_input.strip():
        st.error("Please paste your resume.")
    elif not jd_input.strip():
        st.error("Please paste the job description.")
    else:
        with st.spinner("Tailoring your resume with Llama 4 Scout..."):
            try:
                tailored_text = tailor_with_groq(resume_input, jd_input, api_key)
                data          = parse_resume(tailored_text)
                pdf_bytes     = build_pdf(data)
                docx_bytes    = build_docx(data)

                st.success("Your tailored resume is ready!")
                st.text_area("Preview", tailored_text, height=340)

                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button(
                        "⬇ Download PDF",
                        data=pdf_bytes,
                        file_name="tailored_resume.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with dl2:
                    st.download_button(
                        "⬇ Download Word (.docx)",
                        data=docx_bytes,
                        file_name="tailored_resume.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Something went wrong: {e}")
