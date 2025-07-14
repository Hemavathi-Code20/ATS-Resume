from flask import Flask, request, render_template
import docx
import PyPDF2
import spacy
from skills_list import SKILLS
from job_roles import ROLE_KEYWORDS, ROLE_SKILLS

nlp = spacy.load("en_core_web_sm")
app = Flask(__name__)

COURSE_RECOMMENDATIONS = {
    "php": "https://www.udemy.com/course/php-for-beginners/",
    "mysql": "https://www.udemy.com/course/the-ultimate-mysql-bootcamp-go-from-sql-beginner-to-expert/",
    "git": "https://www.udemy.com/course/git-and-github-bootcamp/",
    "javascript": "https://www.udemy.com/course/the-complete-javascript-course/",
    "html": "https://www.codecademy.com/learn/learn-html",
    "css": "https://www.codecademy.com/learn/learn-css",
    "apache": "https://www.udemy.com/course/apache-web-server-complete-admin-guide/",
    "nginx": "https://www.udemy.com/course/nginx-fundamentals/",
    "postgresql": "https://www.udemy.com/course/sql-and-postgresql/",
}

def extract_text(file):
    text = ""
    if file.filename.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    elif file.filename.endswith(".docx"):
        doc = docx.Document(file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text

def clean_token(token):
    return token.text.lower().strip()

def predict_role(job_desc):
    desc = job_desc.lower()
    if "php" in desc and "intern" in desc:
        return "PHP Intern"

    lines = desc.splitlines()
    for line in lines[:5]:
        for role in ROLE_KEYWORDS:
            if role.lower() in line:
                return role
    for role in ROLE_KEYWORDS:
        patterns = [
            f"{role.lower()} intern", f"{role.lower()} role", f"we are hiring a {role.lower()}",
            f"we are looking for a {role.lower()}", f"job title: {role.lower()}",
            f"position: {role.lower()}", f"as a {role.lower()}"
        ]
        if any(pattern in desc for pattern in patterns):
            return role
    scores = {role: sum(kw in desc for kw in keywords) for role, keywords in ROLE_KEYWORDS.items()}
    best_match = max(scores, key=scores.get)
    return best_match if scores[best_match] > 0 else "Unknown"

def analyze_resume(resume_text, job_desc):
    resume_tokens = set(clean_token(token) for token in nlp(resume_text) if token.is_alpha)
    resume_skills = set(skill for skill in resume_tokens if skill in SKILLS)
    predicted_role = predict_role(job_desc)
    required_skills = set(ROLE_SKILLS.get(predicted_role, []))
    matched = resume_skills & required_skills
    missing = required_skills - resume_skills
    score = round((len(matched) / len(required_skills)) * 100, 2) if required_skills else 0
    return score, sorted(resume_skills), sorted(missing), predicted_role

def get_course_recommendations(missing_skills, limit=2):
    recommendations = []
    for skill in missing_skills:
        link = COURSE_RECOMMENDATIONS.get(skill.lower())
        if link and link not in [r[1] for r in recommendations]:
            recommendations.append((skill.title(), link))
        if len(recommendations) >= limit:
            break
    return recommendations

@app.route("/", methods=["GET", "POST"])
def index():
    score = None
    current_skills = []
    recommended_skills = []
    predicted_role = ""
    show_prediction = False
    course_links = []

    if request.method == "POST":
        resume = request.files["resume"]
        job_desc = request.form["jobdesc"]
        resume_text = extract_text(resume)
        score, current_skills, recommended_skills, predicted_role = analyze_resume(resume_text, job_desc)
        course_links = get_course_recommendations(recommended_skills, limit=2)
        show_prediction = True

    return render_template("index.html",
                           score=score,
                           current_skills=current_skills,
                           recommended_skills=recommended_skills,
                           predicted_role=predicted_role,
                           show_prediction=show_prediction,
                           course_links=course_links)

if __name__ == "__main__":
    app.run(debug=True)
