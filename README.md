# ResumeLens AI — Advanced ATS Resume Parser & Intelligence Platform
**AIL Mini Project**  
_By Shreeya S Tapaswi (31474)_

An AI-powered resume parser and applicant tracking system (ATS) analytics platform. Extracts candidate names, contact details, social/portfolio links, categorized skills, work experience with non-overlapping duration calculations, projects, education with GPA/CGPA, and certifications from PDF, DOCX, and TXT resumes.

---

## 🚀 Quick Start
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## ✨ Features & Architecture

### 1. High-Accuracy NLP & Heuristic Extraction Engine
- **Text Layer**: Multi-format extraction using `pdfplumber` (with multi-column coordinate tolerance for PDFs), `python-docx` (including table parsing for DOCX), and UTF-8 plain text decoder.
- **Header & Name Detection**: Filters out resume noise (`Curriculum Vitae`, `Resume`, honorifics, etc.), identifies candidate name via header heuristics + spaCy NER `PERSON` tag, with smart email handle fallback.
- **Contact & Web Footprint**: Robust regex extraction for international phone numbers, email, LinkedIn, GitHub, LeetCode, and personal portfolio links.
- **Expanded Skill Taxonomy**: Multi-category taxonomy (Languages, Web & APIs, AI & Data Science, Databases, Cloud & DevOps, Tools, Soft Skills) using spaCy `PhraseMatcher` with aliases (`k8s`, `js`, `ts`, `sklearn`, `genai`, `llm`, etc.) and strict ambiguity matching. Delimiter handling prevents breaking compound technical terms like `CI/CD` and `PL/SQL`.
- **Work History Timeline**: Anchored by date-range parsing (`MMM YYYY - Present`, `MM/YYYY - MM/YYYY`, etc.), non-overlapping duration merger, job title extraction, company entity detection via spaCy `ORG`, and bullet-point parsing with metric detection.
- **Projects & Academic Credentials**: Parses degrees (`B.Tech`, `M.S.`, `B.S.`, `Ph.D.`, `MBA`), institutions, graduation year, and GPA/CGPA scores. Extracts independent technical projects with tech stack badges.

### 2. Cool & Modern Interactive UI
- **Cyber Obsidian Glassmorphism**: Tailored dark theme with ambient glowing meshes, electric cyan and violet accents, and modern typography (`Plus Jakarta Sans`, `Space Grotesk`, `JetBrains Mono`, `Source Serif 4`).
- **Interactive Document Inspector**:
  - Live animated laser beam sweep while parsing.
  - Realistic digital paper rendering.
  - Category highlight toggles (Skills, Dates, Organizations, Contact).
  - Real-time in-document search with match count indicator.
  - Bi-directional sync: clicking any skill tag or job title flashes and scrolls to its location in the document.
- **ATS Readiness Diagnostics**:
  - SVG animated circular score gauge with dynamic color indicators.
  - 9-point ATS check breakdown (Contact, Headings, Skills Depth, History, Quantified Impact, Action Verbs, Length, Readability, Health).
  - Actionable recommendations panel highlighting exact improvements needed.
- **Job Description Matcher**:
  - Match percentage score with compatibility level.
  - Matched skills cloud (emerald glow) vs. Missing skills cloud (rose glow).
  - 1-click **"Copy Missing Skills"** to easily tailor resumes to JDs.
- **Multi-Resume Comparison Matrix**:
  - Upload multiple candidate files or load pre-built diverse samples (Full Stack, AI/ML, Fresher).
  - Side-by-side comparison modal with gold crown award for highest ATS score.
- **Export & Sharing**:
  - Download structured JSON.
  - 1-click copy formatted candidate summary.
  - Print-ready ATS report.
