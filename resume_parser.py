"""Resume parsing: text extraction (PDF/DOCX/TXT) + spaCy NLP + rule-based heuristics."""
import io, re, datetime
from collections import defaultdict, Counter
import spacy
from spacy.matcher import PhraseMatcher

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = spacy.blank("en")
HAS_NER = nlp.has_pipe("ner")

# ---------- Skill taxonomy: "Name:alias:alias"; leading "!" = ambiguous, matched only inside Skills section
SKILLS = {
 "Languages": "Python:py:Python3|JavaScript:js:ECMAScript|TypeScript:ts|Java|C++|C#|!C|!Go:Golang|!R|Rust|!Swift|Kotlin|PHP|Ruby|SQL|HTML:HTML5|CSS:CSS3|Sass:SCSS|Shell:Bash:sh|PowerShell|Dart|Scala|MATLAB|Perl",
 "Web & APIs": "React:React.js:ReactJS|Next.js:NextJS:Next|Vue.js:Vue:VueJS|Nuxt.js:Nuxt|Angular:AngularJS|Svelte:SvelteKit|Node.js:NodeJS:Node|Express.js:Express:ExpressJS|Django|Flask|FastAPI|Spring Boot:SpringBoot|.NET:ASP.NET|Ruby on Rails:Rails|NestJS:Nest.js|GraphQL|REST:REST API:RESTful APIs:RESTful|gRPC|Microservices|WebSocket:WebSockets|Tailwind CSS:Tailwind:TailwindCSS|Bootstrap|Redux:Redux Toolkit|jQuery",
 "AI & Data Science": "Machine Learning:ML|Deep Learning:DL|NLP:Natural Language Processing|Computer Vision:CV|Large Language Models:LLM:LLMs|Generative AI:GenAI|LangChain|RAG|Hugging Face:HuggingFace|OpenAI|spaCy|NLTK|scikit-learn:sklearn|TensorFlow:TF|PyTorch|Keras|OpenCV|Pandas|NumPy|SciPy|Matplotlib|Seaborn|Tableau|Power BI:PowerBI|Apache Spark:PySpark:!Spark|Hadoop|Apache Airflow:Airflow|ETL|Data Engineering|Data Analysis|Statistics|Prompt Engineering",
 "Databases & Storage": "PostgreSQL:Postgres|MySQL|MongoDB:Mongo|Redis|SQLite|Oracle|Elasticsearch|Cassandra|DynamoDB|Snowflake|BigQuery|Supabase|Firebase:Firestore|MariaDB|Neo4j",
 "Cloud & DevOps": "AWS:Amazon Web Services|Azure:Microsoft Azure|GCP:Google Cloud:Google Cloud Platform|Docker|Kubernetes:k8s|Terraform|Jenkins|Git|GitHub Actions|GitLab CI:GitLab|CI/CD:Continuous Integration|Linux|Unix|Ansible|Nginx|Apache|Prometheus|Grafana|Serverless|Cloudflare",
 "Tools & Methodologies": "Jira|Agile|Scrum|Figma|Postman|Swagger|!Excel|Pytest|Jest|Cypress|Selenium|Unit Testing|System Design|Design Patterns|Object-Oriented Programming:OOP|Data Structures:DSA|Algorithms|SDLC|CI/CD",
 "Soft Skills": "Leadership|Communication|Problem Solving|Teamwork|Project Management|Mentoring|Stakeholder Management|Critical Thinking|Time Management|Collaboration|Adaptability",
}

CANON, CAT, STRICT, ALIAS = {}, {}, {}, {}
for cat, spec in SKILLS.items():
    for item in spec.split("|"):
        strict = item.startswith("!")
        name, *aliases = item.lstrip("!").split(":")
        CAT[name] = cat
        for t in [name, *aliases]:
            (STRICT if strict else ALIAS)[t if strict else t.lower()] = name

matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
for term, name in ALIAS.items():
    matcher.add(name, [nlp.make_doc(term)])

# ---------- Regexes & Constants
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?:(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5})")
LINKEDIN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w%-]+/?", re.I)
GITHUB = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+/?", re.I)
PORTFOLIO = re.compile(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.(?:dev|me|io|app|tech|design|page|info|site|in|co|org|net|com))(?:/[^\s,;]*)?", re.I)
LEETCODE = re.compile(r"(?:https?://)?(?:www\.)?leetcode\.com/(?:u/)?[\w-]+/?", re.I)

MON = "jan feb mar apr may jun jul aug sep oct nov dec".split()
MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
YEAR4 = r"(?:19|20)\d{2}"
YEAR2 = r"(?:'?[0-9]{2})"
YEAR = rf"(?:{YEAR4}|{YEAR2})"

PART_DATE = rf"(?:(?:{MONTH}[a-z]*\.?,?\s+{YEAR})|(?:\d{{1,2}}[\/\.\-]{YEAR})|(?:{YEAR4}[\/\.\-]\d{{1,2}})|(?:{MONTH}\.?\s*{YEAR})|{YEAR4})"
END_WORDS = r"(?:Present|Current|Now|Ongoing|Till\s*Date|Till\s*now|Until\s*now|Date|Continuing|Active)"
SEP = r"(?:\s*(?:[-–—~]|to|until|till)\s*)"

# Robust date range regex: handles dates on the right of title with parentheses, spaces, dashes, or trailing dashes
RANGE = re.compile(rf"\(?\s*({PART_DATE})\s*{SEP}\s*({PART_DATE}|{END_WORDS})\s*\)?|\(?\s*({PART_DATE})\s*[-–—]\s*(?=\)|$|\n)", re.I)

TITLE_RE = re.compile(r"\b(engineer|developer|manager|analyst|intern|designer|scientist|consultant|lead|director|architect|"
                      r"specialist|administrator|associate|officer|executive|head|programmer|tester|trainee|founder|co-founder|"
                      r"coordinator|researcher|fellow|lecturer|professor|instructor|sde|mts|member of technical staff|"
                      r"software development engineer|frontend|backend|fullstack|full stack|devops|data scientist|data analyst)\b", re.I)

DEGREE = re.compile(r"\b(B\.?\s?Tech|M\.?\s?Tech|B\.?E\.?|M\.?E\.?|B\.?S\.?|M\.?S\.?|B\.?Sc|M\.?Sc|B\.?C\.?A|M\.?C\.?A|MBA|BBA|Ph\.?D|Doctorate|"
                    r"Bachelor[^,|\n]*|Master[^,|\n]*|Diploma[^,|\n]*|Associate[^,|\n]*|High\s+School|CBSE|ICSE)(?=\W|$)", re.I)

INST = re.compile(r"\b(university|college|institute|school|academy|iit|nit|bits|coep|polytechnic|stanford|mit|harvard|cambridge|oxford|"
                  r"carnegie|georgia|berkeley|campus|department)\b", re.I)

GPA_RE = re.compile(r"(?:cgpa|gpa|grade|score|percentage|marks|aggregate)[\s:]*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?%?)", re.I)

HEADINGS = {
 "summary": r"(executive |professional |career )?(summary|profile|objective|about( me)?|overview)",
 "experience": r"(work |professional |relevant |employment |technical |industry |career |internship )?experience(s)?|"
               r"employment( history| record)?|work history|career history|internships?|positions held|professional background",
 "education": r"education|academics?|academic background|qualifications|academic credentials",
 "skills": r"(technical |key |core |professional )?(skills|competencies|expertise|proficiencies)( (&|and) \w+)?|technologies|tech stack|tools & technologies",
 "projects": r"(personal |key |academic |major |notable )?projects?",
 "certifications": r"certifications?|licenses( (&|and) certifications)?|courses|training & certifications|accreditations",
 "awards": r"honors?|awards?|achievements?|accomplishments?",
 "languages": r"languages?( spoken)?",
}

IGNORE_NAME_WORDS = {
    "resume", "curriculum", "vitae", "cv", "profile", "summary", "contact", "information",
    "details", "portfolio", "biodata", "bio-data", "page", "personal", "professional",
    "address", "phone", "email", "education", "experience", "skills", "projects", "certifications",
    "objective", "work", "technical", "academic", "courses", "github", "linkedin"
}

ACTION = set("built developed led managed designed created implemented improved reduced increased launched optimized delivered automated analyzed engineered deployed mentored migrated architected streamlined collaborated owned drove cut scaled integrated established maintained tested resolved coordinated spearheaded founded programmed authored accelerated championed spearheaded standardized transformed audited".split())

def clean(t):
    t = t.replace("\r", "\n").replace("\u00a0", " ")
    t = re.sub(r"[•▪●◦■◆►➢]", "-", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()

def extract_text(data: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            text = "\n".join((p.extract_text(x_tolerance=1.5) or "") for p in pdf.pages)
    elif ext == "docx":
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for tb in d.tables:
            parts += [" | ".join(c.text for c in r.cells) for r in tb.rows]
        text = "\n".join(parts)
    elif ext in ("txt", "md", ""):
        text = data.decode("utf-8", "ignore")
    else:
        raise ValueError("Unsupported file type. Upload a PDF, DOCX or TXT file.")
    return clean(text)

def split_sections(lines):
    secs, cur = defaultdict(list), "header"
    for l in lines:
        s = re.sub(r"^[\s#*\-•=~_\[\]()]+|[\s:;=\-_\[\]()]+$", "", l).strip().lower()
        if s and len(s) <= 45 and len(s.split()) <= 5:
            matched_sec = None
            for sec_name, pat in HEADINGS.items():
                if re.fullmatch(pat, s):
                    matched_sec = sec_name
                    break
            if matched_sec:
                cur = matched_sec
                continue
        secs[cur].append(l)
    return secs

# ---------- Field extractors
def find_name(lines, email):
    honorifics = re.compile(r"^(?:mr\.|ms\.|mrs\.|dr\.|prof\.)\s*", re.I)
    for l in lines[:10]:
        cleaned_line = honorifics.sub("", l.strip()).strip()
        w = cleaned_line.split()
        if not (2 <= len(w) <= 4):
            continue
        # Skip if contains digits, emails, URLs, or delimiters
        if re.search(r"[\d@:/|,~_=+*#]", cleaned_line):
            continue
        # Skip if matches known heading or ignore words
        lower_w = [x.lower().strip(".,()[]") for x in w]
        if any(x in IGNORE_NAME_WORDS for x in lower_w):
            continue
        if TITLE_RE.search(cleaned_line):
            continue
        if all(re.fullmatch(r"[A-Za-z][A-Za-z.'’-]*", x) for x in w):
            return cleaned_line.title() if cleaned_line.isupper() else cleaned_line

    if HAS_NER:
        for ent in nlp("\n".join(lines[:12])).ents:
            if ent.label_ == "PERSON":
                ent_text = honorifics.sub("", ent.text.strip()).strip()
                w = ent_text.split()
                if 2 <= len(w) <= 4:
                    lower_w = [x.lower() for x in w]
                    if not any(x in IGNORE_NAME_WORDS for x in lower_w) and not TITLE_RE.search(ent_text):
                        return ent_text.title() if ent_text.isupper() else ent_text

    if email:
        user_part = email.split("@")[0]
        parts = [p.capitalize() for p in re.split(r"[._\-\d]+", user_part) if p and len(p) > 1]
        if 1 <= len(parts) <= 3:
            return " ".join(parts)
    return ""

def find_phone(text):
    for m in PHONE.finditer(text):
        c = m.group().strip()
        digits = re.sub(r"\D", "", c)
        # Avoid year ranges like 2019-2023 or simple year numbers
        if re.search(r"(?:19|20)\d{2}\s*[-–—]\s*(?:19|20)\d{2}", c):
            continue
        if 10 <= len(digits) <= 14:
            return c
    return ""

def find_links(text):
    li = (LINKEDIN.search(text) or [""])[0]
    gh = (GITHUB.search(text) or [""])[0]
    lc = (LEETCODE.search(text) or [""])[0]
    
    # Portfolio extraction (excluding known non-portfolio domains)
    portfolio = ""
    for m in PORTFOLIO.finditer(text):
        url = m.group().strip()
        domain = m.group(1).lower()
        if any(d in domain for d in ["linkedin", "github", "gmail", "yahoo", "outlook", "hotmail", "example", "leetcode"]):
            continue
        portfolio = url
        break

    return {
        "linkedin": li,
        "github": gh,
        "portfolio": portfolio,
        "leetcode": lc
    }

def to_ym(s, end=False):
    if not s:
        return 0
    s = s.strip().lower()
    if re.search(r"(present|current|now|ongoing|till|date|continuing|active)", s):
        t = datetime.date.today()
        return t.year * 12 + t.month
    
    y = 0
    y4 = re.search(r"(?:19|20)\d{2}", s)
    if y4:
        y = int(y4.group())
    else:
        y2 = re.search(r"(?:'|\b)(\d{2})\b", s)
        if y2:
            val = int(y2.group(1))
            y = 2000 + val if val < 70 else 1900 + val
    if not y:
        return 0

    m_name = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", s)
    if m_name:
        mo = MON.index(m_name.group(1)) + 1
    else:
        m_slash = re.search(r"\b(\d{1,2})[\/\.\-](?:19|20)\d{2}", s)
        if m_slash:
            mo = int(m_slash.group(1))
        else:
            m_rev = re.search(r"(?:19|20)\d{2}[\/\.\-](\d{1,2})", s)
            if m_rev:
                mo = int(m_rev.group(1))
            else:
                mo = 12 if end else 1
    return y * 12 + min(max(mo, 1), 12)

def is_sec_heading(line):
    s = re.sub(r"^[\s#*\-•=~_\[\]()]+|[\s:;=\-_\[\]()]+$", "", line).strip().lower()
    return any(re.fullmatch(pat, s) for pat in HEADINGS.values())

def parse_experience(lines):
    entries, used = [], set()
    for i, l in enumerate(lines):
        m = RANGE.search(l)
        if not m:
            if entries and i not in used:
                stripped = l.lstrip("-*•▪ ").strip()
                if len(stripped) > 4:
                    entries[-1]["highlights"].append(stripped)
            continue
        
        start_raw = m.group(1) or m.group(3) or ""
        end_raw = m.group(2) or "Present"
        s, e = to_ym(start_raw), to_ym(end_raw, end=True)
        head = RANGE.sub("", l).strip(" |,-–—()[]")

        title, company = "", ""
        if head:
            parts = [p.strip() for p in re.split(r"\s+(?:at|@)\s+|\s*[|•·]\s*|\s+[-–—]\s+|,\s+", head) if p.strip()]
            title = next((p for p in parts if TITLE_RE.search(p)), parts[0] if parts else "")
            rest = [p for p in parts if p != title]
            company = rest[0] if rest else ""
            if HAS_NER and head:
                orgs = [e_ent.text for e_ent in nlp(head).ents if e_ent.label_ == "ORG"]
                if orgs and orgs[0] not in title:
                    company = orgs[0]

        # If company or title missing, check adjacent lines
        if not company:
            # Check previous line
            if i > 0 and i-1 not in used and not lines[i-1].startswith(("-", "*", "•")) and len(lines[i-1]) < 70 and not RANGE.search(lines[i-1]) and not is_sec_heading(lines[i-1]):
                company = lines[i-1].strip(" -•|")
                used.add(i-1)
                if not title and head:
                    title = head
            # Check next line
            elif i+1 < len(lines) and not lines[i+1].startswith(("-", "*", "•")) and len(lines[i+1]) < 70 and not RANGE.search(lines[i+1]) and not is_sec_heading(lines[i+1]):
                company = lines[i+1].strip(" -•|")
                used.add(i+1)

        if not title:
            if i > 0 and i-1 not in used and not lines[i-1].startswith(("-", "*", "•")) and len(lines[i-1]) < 70 and not RANGE.search(lines[i-1]) and not is_sec_heading(lines[i-1]):
                title = lines[i-1].strip(" -•|")
                used.add(i-1)
            elif head:
                title = head

        entries.append({
            "title": title or "Role",
            "company": company,
            "start": start_raw.strip(),
            "end": end_raw.strip().title(),
            "months": max(e - s, 0),
            "_iv": (s, e),
            "highlights": []
        })

    for en in entries:
        en["highlights"] = [h for h in en["highlights"] if len(h) > 5][:8]
    return entries

def total_years(entries):
    ivs = sorted([e["_iv"] for e in entries if e["_iv"][0] > 0 and e["_iv"][1] >= e["_iv"][0]])
    if not ivs:
        return 0.0
    total = 0
    cur_s, cur_e = None, None
    for s, e in ivs:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return round(total / 12, 1)

def parse_education(lines):
    out, seen = [], set()
    for i, l in enumerate(lines):
        d = DEGREE.search(l)
        if not d:
            continue
        ctx = " ".join(lines[max(0, i-1):min(len(lines), i+3)])
        # Find institution
        inst = ""
        for p in re.split(r"\s*[|,;–—]\s*|\s+-\s+|\n", ctx):
            p = p.strip()
            if INST.search(p) and not DEGREE.search(p):
                inst = p
                break
        if not inst and HAS_NER:
            orgs = [e.text for e in nlp(ctx).ents if e.label_ == "ORG"]
            if orgs:
                inst = orgs[0]

        years = re.findall(r"(?:19|20)\d{2}", ctx)
        if inst:
            inst = re.sub(r"\b(?:19|20)\d{2}\b.*$", "", inst).strip(" ,|-–—()")
            if inst.count("(") > inst.count(")"):
                inst += ")"
        gpa_match = GPA_RE.search(ctx)
        gpa = gpa_match.group(1) if gpa_match else ""
        
        degree = d.group(0).strip(" ,|-–—()")
        # Try to capture full degree title if extended, e.g. "B.Tech in Computer Science"
        full_deg = re.search(rf"{re.escape(degree)}[^\n|,–—;]+", l, re.I)
        if full_deg:
            degree = full_deg.group(0).strip(" ,|-–—()")

        key = degree.lower()
        if key not in seen:
            seen.add(key)
            out.append({
                "degree": degree,
                "institution": inst,
                "year": years[-1] if years else "",
                "grade": gpa
            })
    return out

def parse_projects(lines):
    projects, cur = [], None
    for l in lines:
        l = l.strip()
        if not l:
            continue
        # Check if line looks like a project header
        if not l.startswith(("-", "*", "•")) and (len(l) < 70 or "|" in l or "(" in l):
            # Parse project title and tech stack
            tech = []
            title = l
            if "(" in l and ")" in l:
                m = re.search(r"\(([^)]+)\)", l)
                if m:
                    tech = [t.strip() for t in re.split(r"[,;|]", m.group(1)) if t.strip()]
                    title = l.replace(f"({m.group(1)})", "").strip()
            elif "|" in l:
                parts = [p.strip() for p in l.split("|")]
                title = parts[0]
                if len(parts) > 1:
                    tech = [t.strip() for t in re.split(r"[,;]", parts[1]) if t.strip()]
            
            cur = {
                "name": title.strip(" -:"),
                "technologies": tech[:6],
                "highlights": []
            }
            projects.append(cur)
        elif cur and l.startswith(("-", "*", "•")):
            cur["highlights"].append(l.lstrip("-*•▪ ").strip())
        elif cur and len(cur["highlights"]) < 3 and len(l) > 10:
            cur["highlights"].append(l)

    return projects[:5]

def parse_skills(doc, skill_lines):
    found = defaultdict(int)
    for mid, s, e in matcher(doc):
        found[nlp.vocab.strings[mid]] += 1

    other = []
    for line in skill_lines:
        body = line.split(":", 1)[1] if ":" in line else line
        # Split on commas, semicolons, bullets, and slashes with spaces, protecting CI/CD
        tokens = [x.strip(" -*•▪.") for x in re.split(r"[,;|•▪●\n\t]|\s[/-]\s|^\s*[-*•▪]\s*", body) if x.strip()]
        for it in tokens:
            if not it:
                continue
            if it in STRICT:
                found[STRICT[it]] += 1
            elif it.lower() in ALIAS:
                found.setdefault(ALIAS[it.lower()], 1)
            elif 2 <= len(it) <= 30 and len(it.split()) <= 3 and re.search(r"[A-Za-z]", it) and not re.search(r"\d{4}|@|http", it):
                other.append(it)

    grouped = defaultdict(list)
    for n, c in sorted(found.items(), key=lambda x: -x[1]):
        cat = CAT.get(n, "Other")
        grouped[cat].append({"name": n, "count": c})

    known = {n.lower() for n in found}
    extra = [o for o in dict.fromkeys(other) if o.lower() not in known]
    if extra:
        grouped["Other Tools & Skills"] = [{"name": o, "count": 1} for o in extra[:15]]

    return dict(grouped)

def _parse_core(raw):
    text = clean(raw)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    secs = split_sections(lines)
    head = secs["header"]
    email = (EMAIL.search(text) or [""])[0] if EMAIL.search(text) else ""
    doc = nlp(text)
    
    skills = parse_skills(doc, secs["skills"])
    exp = parse_experience(secs["experience"])
    if not exp:
        candidate_lines = [l for s, ls in secs.items() if s not in ("education", "skills", "certifications") for l in ls]
        exp = parse_experience(candidate_lines)
    edu = parse_education(secs["education"])
    projects = parse_projects(secs["projects"])
    links = find_links(text)
    
    # Location detection
    loc = ""
    for piece in re.split(r"[|•·\n]", " | ".join(head[:8])):
        piece = piece.strip()
        if re.fullmatch(r"[A-Za-z .]+(?:,\s*[A-Za-z .]+){1,2}", piece) and not TITLE_RE.search(piece) and len(piece) <= 40:
            if not any(x in piece.lower() for x in ["curriculum", "resume", "developer", "engineer"]):
                loc = piece
                break

    summary = " ".join(secs["summary"])[:500]
    stated = re.search(r"(\d{1,2})\+?\s*(?:years|yrs)", " ".join(secs["summary"] + head), re.I)

    # Highlights for the UI
    cand = [(s.start_char, s.end_char, "skill", nlp.vocab.strings[mid]) for mid, a, b in matcher(doc) for s in [doc[a:b]]]
    cand += [(m.start(), m.end(), "contact", "") for rx in (EMAIL, LINKEDIN, GITHUB, PORTFOLIO) for m in rx.finditer(text)]
    cand += [(m.start(), m.end(), "date", "") for m in RANGE.finditer(text)]
    if HAS_NER:
        cand += [(e.start_char, e.end_char, "org", "") for e in doc.ents if e.label_ == "ORG" and e.text not in ALIAS]

    hl, last = [], 0
    for s, e, t, lab in sorted(cand, key=lambda c: (c[0], -(c[1] - c[0]))):
        if s >= last:
            hl.append({"start": s, "end": e, "type": t, "label": lab})
            last = e

    name = find_name(head or lines, email)
    total_skills = sum(len(v) for v in skills.values())
    score = sum([
        20 * bool(name),
        15 * bool(email),
        10 * bool(find_phone(text)),
        20 * bool(skills),
        15 * bool(exp or projects),
        10 * bool(edu),
        10 * bool(links["linkedin"] or links["github"] or links["portfolio"])
    ])

    return {
        "name": name,
        "email": email,
        "phone": find_phone(text),
        "location": loc,
        "links": links,
        "summary": summary,
        "total_experience_years": total_years(exp),
        "stated_years": int(stated.group(1)) if stated else None,
        "skills": skills,
        "total_skills_count": total_skills,
        "experience": [{k: v for k, v in e.items() if k != "_iv"} for e in exp],
        "education": edu,
        "projects": projects,
        "certifications": [c.strip(" -*•▪") for c in secs["certifications"][:8] if len(c.strip()) > 3],
        "completeness": min(score, 100),
        "ner_enabled": HAS_NER,
        "text": text,
        "highlights": hl,
    }

# ---------- ATS readiness score + job-description match ----------
STOP = set("the and for with that this from will you our are have has your able work team using use such into their they been more than also who can all any not but out per via etc "
           "experience ability strong years skills knowledge role working good required preferred candidate responsibilities requirements including well plus must should nice looking join company".split())

def ats_report(res, text):
    bullets = [h for e in res["experience"] for h in e["highlights"]] + [h for p in res.get("projects", []) for h in p["highlights"]]
    nb, words = len(bullets), len(text.split())
    quant = sum(bool(re.search(r"\d+\s*%|[$₹€£]\s?\d|\d[\d,.]*\s*[kKmMx+]|\b\d{2,}\b|\b\d+\s*(?:users|clients|nodes|queries|times|requests|ms|seconds|hours)\b", b)) for b in bullets)
    verbs = sum(1 for b in bullets if b.split() and (b.split()[0].lower() in ACTION or b.split()[0].lower().endswith("ed")))
    avg = sum(len(b.split()) for b in bullets) / nb if nb else 0
    nskills = res.get("total_skills_count", sum(len(v) for v in res["skills"].values()))
    nonascii = sum(ord(c) > 127 for c in text) / max(len(text), 1)
    
    L = lambda a, b: min(a / b, 1) if b else 0
    contact = 5 * bool(res["email"]) + 4 * bool(res["phone"]) + 3 * bool(res["links"]["linkedin"]) + 2 * bool(res["links"]["github"] or res["links"]["portfolio"])
    secs = 5 * bool(res["experience"] or res["projects"]) + 4 * bool(res["education"]) + 5 * bool(nskills >= 6) + 3 * bool(res["summary"]) + 2 * bool(res.get("projects"))
    length = 10 if 350 <= words <= 850 else 7 if 200 <= words <= 1100 else 3
    
    rows = [
     ("Contact details", min(contact, 14), 14, "Add an email, phone number, and LinkedIn/GitHub links at the top."),
     ("Standard sections", min(secs, 19), 19, "Use clear standard headings: Summary, Experience, Education, Skills, and Projects."),
     ("Skills depth", round(15 * L(nskills, 12)), 15, "List at least 12 relevant skills categorized under a clean Skills section."),
     ("Dated history", round(10 * L(len(res["experience"]) + (1 if res.get("projects") else 0), 3)), 10, "Include dated experience entries or substantial academic projects."),
     ("Quantified impact", round(16 * L(quant / nb if nb else 0, 0.35)), 16, "Add measurable numbers, percentages, or scale metrics to your achievement bullets."),
     ("Action verbs", round(11 * L(verbs / nb if nb else 0, 0.65)), 11, "Start bullets with decisive action verbs like Built, Engineered, Led, or Optimized."),
     ("Resume length", length, 10, "Aim for 400-800 words to keep your resume concise and high-impact."),
     ("Bullet readability", 5 if (6 <= avg <= 28) else 2 if nb else 0, 5, "Keep bullet points between 8 and 25 words for quick scannability."),
     ("ATS parse health", 4 * bool(res["name"]) + (0 if nonascii < 0.03 else -2) + 2 * bool(res["location"]), 6, "Put your full name and city on the top line; avoid decorative columns or non-standard characters.")
    ]
    
    checks = [{"label": l, "got": max(int(g), 0), "max": m, "tip": t} for l, g, m, t in rows]
    score = min(max(sum(c["got"] for c in checks), 0), 100)
    
    # Rating category
    if score >= 85:
        grade = "A+ (Excellent)"
    elif score >= 75:
        grade = "A (Strong Match)"
    elif score >= 60:
        grade = "B (Good)"
    elif score >= 45:
        grade = "C (Fair)"
    else:
        grade = "Needs Optimization"

    return {
        "score": score,
        "grade": grade,
        "checks": checks,
        "words": words,
        "quantified_bullets": quant,
        "action_verb_bullets": verbs,
        "total_bullets": nb,
        "tips": [c["tip"] for c in checks if c["got"] < c["max"] * 0.75][:5]
    }

def job_match(res, text, jd):
    req = defaultdict(int)
    for mid, a, b in matcher(nlp(jd)):
        req[nlp.vocab.strings[mid]] += 1
    
    have = {s["name"] for v in res["skills"].values() for s in v}
    matched = [k for k in req if k in have]
    missing = [k for k in req if k not in have]
    
    ws = [w for w in (x.rstrip(".-") for x in re.findall(r"[a-zA-Z][a-zA-Z+#.-]{3,}", jd.lower())) if len(w) > 3 and w not in STOP and w not in ALIAS]
    top = [w for w, _ in Counter(ws).most_common(25)]
    low = text.lower()
    hit = [w for w in top if w in low]
    kw_pct = len(hit) / max(len(top), 1)
    
    skill_pct = len(matched) / max(len(req), 1) if req else 1.0
    total_pct = round(100 * (0.75 * skill_pct + 0.25 * kw_pct)) if req else round(100 * kw_pct)
    
    if total_pct >= 80:
        match_level = "High Match"
    elif total_pct >= 55:
        match_level = "Moderate Match"
    else:
        match_level = "Low Match"

    return {
        "percent": min(total_pct, 100),
        "level": match_level,
        "matched": matched,
        "missing": missing,
        "matched_count": len(matched),
        "total_req_count": len(req),
        "matched_keywords": hit,
        "keywords_missing": [w for w in top if w not in low][:10]
    }

def parse_resume(raw, jd=""):
    res = _parse_core(raw)
    res["ats"] = ats_report(res, res["text"])
    if jd.strip():
        res["job_match"] = job_match(res, res["text"], jd)
    return res
