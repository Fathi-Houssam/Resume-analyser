import csv
import os
import fitz
import sqlite3
import spacy
import threading
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from spacy.matcher import PhraseMatcher
from flask_login import LoginManager, login_required, current_user
from models import get_user_by_id  # Import the necessary functions and classes from models
from auth import auth_bp  # Import auth_bp from auth

app = Flask(__name__)
nlp = spacy.load('C:/Users/ryzen/OneDrive/Desktop/pfe/model-bestv2')
person_nlp = spacy.load('en_core_web_md')

app.config['SECRET_KEY'] = 'your_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

app.register_blueprint(auth_bp, url_prefix='/auth')



DATABASE = 'dbpfe5.db'
lock = threading.Lock()



def get_db_connection():
    return sqlite3.connect(DATABASE, timeout=30)

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT UNIQUE,
            Password TEXT,
            IsAdmin INTEGER DEFAULT 0,
            CanUploadMultiple INTEGER DEFAULT 0

        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Resumes (c
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID INTEGER,
            Name TEXT,
            "Graduation Year" INTEGER,
            "Years of experience" INTEGER,
            Designation TEXT,
            Location TEXT,
            "Email Address" TEXT,
            "Resume PDF" TEXT,
            FOREIGN KEY (UserID) REFERENCES Users(ID)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Degrees (
            DegreeID INTEGER PRIMARY KEY AUTOINCREMENT,
            ResumeID INTEGER,
            Degree TEXT,
            FOREIGN KEY (ResumeID) REFERENCES Resumes(ID)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Colleges (
            CollegeID INTEGER PRIMARY KEY AUTOINCREMENT,
            ResumeID INTEGER,
            CollegeName TEXT,
            FOREIGN KEY (ResumeID) REFERENCES Resumes(ID)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Companies (
            CompanyID INTEGER PRIMARY KEY AUTOINCREMENT,
            ResumeID INTEGER,
            "Company Name" TEXT,
            FOREIGN KEY (ResumeID) REFERENCES Resumes(ID)
        )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Skills (
            SkillID INTEGER PRIMARY KEY AUTOINCREMENT,
            ResumeID INTEGER,
            Skill TEXT,
            FOREIGN KEY (ResumeID) REFERENCES Skills(ID)
        )
        ''')

init_db()



email_pattern = [{"TEXT": {"REGEX": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"}}]
matcher = spacy.matcher.Matcher(nlp.vocab)
matcher.add("EMAIL", [email_pattern])

def normalize_text(text):
    text = text.lower()
    text = text.replace("the ", "").strip()
    return text


def load_city_names(csv_filepath):
    cities = []
    with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) > 0 and row[0].strip():  
                cities.append(row[0].strip())       
    return cities

cities = load_city_names('C:/Users/ryzen/OneDrive/Desktop/pfe/city2.csv')

def load_college_names(csv_filepath):
    colleges = []
    with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) > 0 and row[0].strip():
                colleges.append(row[0].strip())
    return colleges

colleges = load_college_names('C:/Users/ryzen/OneDrive/Desktop/pfe/colleges.csv')

def create_college_phrase_matcher(nlp, colleges):
    matcher = PhraseMatcher(nlp.vocab)
    patterns = [nlp.make_doc(college) for college in colleges]
    matcher.add("COLLEGE", patterns)
    return matcher

college_phrase_matcher = create_college_phrase_matcher(nlp, colleges)

def load_skill_names(csv_filepath):
    skills = []
    with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) > 0 and row[0].strip():
                skills.append(row[0].strip())
    return skills

skills = load_skill_names('C:/Users/ryzen/OneDrive/Desktop/pfe/skills1.csv')

def create_skill_phrase_matcher(nlp, skills):
    matcher = PhraseMatcher(nlp.vocab)
    patterns = [nlp.make_doc(skill) for skill in skills]
    matcher.add("SKILL", patterns)
    return matcher

skill_phrase_matcher = create_skill_phrase_matcher(nlp, skills)


def create_phrase_matcher(nlp, cities):
    matcher = PhraseMatcher(nlp.vocab)
    patterns = [nlp.make_doc(city) for city in cities]
    matcher.add("CITY", patterns)
    return matcher

phrase_matcher = create_phrase_matcher(nlp, cities)

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    text = ' '.join(text.split())
    return text

def nlpfeeding(pdf_text):
    custom_doc = nlp(pdf_text)
    person_doc = person_nlp(pdf_text)
    entities = []
    seen_entities = set()
    name_found = False
    email_found = False

    # Extract college names first using college_phrase_matcher
    college_matches = college_phrase_matcher(custom_doc)
    for match_id, start, end in college_matches:
        entity_text = custom_doc[start:end].text
        entity_label = "College Name"
        normalized_entity = (normalize_text(entity_text), entity_label)
        if normalized_entity not in seen_entities:
            entities.append({'text': entity_text, 'label': entity_label})
            seen_entities.add(normalized_entity)

    # Extract email addresses using regex-based matcher
    matches = matcher(custom_doc)
    for match_id, start, end in matches:
        entity_text = custom_doc[start:end].text
        entity_label = "Email Address"
        normalized_entity = (normalize_text(entity_text), entity_label)
        if normalized_entity not in seen_entities:
            entities.append({'text': entity_text, 'label': entity_label})
            seen_entities.add(normalized_entity)
            email_found = True

    # Extract skills using skill_phrase_matcher
    skill_matches = skill_phrase_matcher(custom_doc)
    for match_id, start, end in skill_matches:
        entity_text = custom_doc[start:end].text
        entity_label = "Skills"
        normalized_entity = (normalize_text(entity_text), entity_label)
        if normalized_entity not in seen_entities:
            entities.append({'text': entity_text, 'label': entity_label})
            seen_entities.add(normalized_entity)

    # Extract other entities from custom_doc
    for ent in custom_doc.ents:
        entity_text = ent.text
        entity_label = ent.label_
        normalized_entity = (normalize_text(entity_text), entity_label)
        if entity_label == 'Email Address' and not email_found:
            if normalized_entity not in seen_entities:
                entities.append({'text': entity_text, 'label': entity_label})
                seen_entities.add(normalized_entity)
                email_found = True
        elif entity_label == 'College Name':
            if normalized_entity not in seen_entities:
                entities.append({'text': entity_text, 'label': entity_label})
                seen_entities.add(normalized_entity)
        elif entity_label == 'Name' and not name_found:
            if normalized_entity not in seen_entities:
                entities.append({'text': entity_text, 'label': 'Name'})
                seen_entities.add(normalized_entity)
                name_found = True
        elif entity_label not in ['Email Address', 'Name', 'College Name', 'Location', 'Skill']:
            if normalized_entity not in seen_entities:
                entities.append({'text': entity_text, 'label': entity_label})
                seen_entities.add(normalized_entity)

    # If no Name entity was found by the custom model, use the spaCy model to extract the name
    if not name_found:
        for ent in person_doc.ents:
            if ent.label_ == 'PERSON':
                entity_text = ent.text
                entity_label = "Name"
                if normalize_text(entity_text) not in seen_entities:
                    entities.append({'text': entity_text, 'label': entity_label})
                    seen_entities.add(normalize_text(entity_text))
                    break

    # Extract location entities using the matcher first
    location_found = False
    matches = phrase_matcher(custom_doc)
    for match_id, start, end in matches:
        entity_text = custom_doc[start:end].text
        entity_label = "Location"
        normalized_entity = (normalize_text(entity_text), entity_label)
        if normalized_entity not in seen_entities:
            entities.append({'text': entity_text, 'label': entity_label})
            seen_entities.add(normalized_entity)
            location_found = True

    # If no location entity was found using the matcher, use the custom NLP model
    if not location_found:
        for ent in custom_doc.ents:
            if ent.label_ == 'GPE':  
                entity_text = ent.text
                entity_label = "Location"
                normalized_entity = (normalize_text(entity_text), entity_label)
                if normalized_entity not in seen_entities:
                    entities.append({'text': entity_text, 'label': entity_label})
                    seen_entities.add(normalized_entity)

    return entities



def insert_entities_to_db(entities, resume_pdf, user_id):
    with lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Check if the resume already exists for the current user
            cursor.execute('''
            SELECT ID FROM Resumes WHERE UserID = ? AND "Resume PDF" = ?
            ''', (user_id, resume_pdf))
            existing_resume = cursor.fetchone()

            if existing_resume:
                # Resume already exists, skip insertion
                return

            name = next((e['text'] for e in entities if e['label'] == 'Name'), None)
            grad_year = next((e['text'] for e in entities if e['label'] == 'Graduation Year'), None)
            years_exp = next((e['text'] for e in entities if e['label'] == 'Years of experience'), None)
            designation = next((e['text'] for e in entities if e['label'] == 'Designation'), None)
            location = next((e['text'] for e in entities if e['label'] == 'Location'), None)
            email = next((e['text'] for e in entities if e['label'] == 'Email Address'), None)

            cursor.execute('''
            INSERT INTO Resumes (UserID, Name, "Graduation Year", "Years of experience", Designation, Location, "Email Address", "Resume PDF")
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, name, grad_year, years_exp, designation, location, email, resume_pdf))

            resume_id = cursor.lastrowid

            for e in entities:
                if e['label'] == 'Degree':
                    cursor.execute('''
                    INSERT INTO Degrees (ResumeID, Degree)
                    VALUES (?, ?)
                    ''', (resume_id, e['text']))

            for e in entities:
                if e['label'] == 'College Name':
                    cursor.execute('''
                    INSERT INTO Colleges (ResumeID, CollegeName)
                    VALUES (?, ?)
                    ''', (resume_id, e['text']))

            for e in entities:
                if e['label'] == 'Companies worked at':
                    cursor.execute('''
                    INSERT INTO Companies (ResumeID, "Company Name")
                    VALUES (?, ?)
                    ''', (resume_id, e['text']))

            for e in entities:
                if e['label'] == 'Skills':
                    cursor.execute('''
                    INSERT INTO Skills (ResumeID, Skill)
                    VALUES (?, ?)
                    ''', (resume_id, e['text']))

            conn.commit()
        finally:
            conn.close()


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('auth.login'))



@app.route('/singlepage')
def singlepage():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part in the request'

    file = request.files['file']

    if file.filename == '':
        return 'No selected file'

    pdf_text = extract_text_from_pdf(file)
    entities = nlpfeeding(pdf_text)

    return render_template('results.html', entities=entities)


@app.route('/upload_multiple', methods=['GET', 'POST'])
@login_required
def upload_multiple_files():
    if not current_user.can_upload_multiple:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        if 'files[]' not in request.files:
            return 'No file part in the request', 400

        files = request.files.getlist('files[]')

        for file in files:
            if file.filename:
                filepath = os.path.join('static/resumes', file.filename)
                file.save(filepath)
                pdf_text = extract_text_from_pdf(open(filepath, "rb"))
                entities = nlpfeeding(pdf_text)
                insert_entities_to_db(entities, file.filename, current_user.id)  # Ensure user ID is stored
        
        return redirect(url_for('dashboard'))

    return render_template('dbuploads.html')

@app.route('/dbsearch')
def dbsearch():
    return render_template('dbsearch.html')

@app.route('/search_results', methods=['GET'])
@login_required
def search_results():
    degree = request.args.get('degree')
    skills = request.args.get('skills')
    years_of_experience = request.args.get('yearsofexperience')

    query = '''
    SELECT DISTINCT Resumes.Name, Resumes."Resume PDF"
    FROM Resumes
    LEFT JOIN Degrees ON Resumes.ID = Degrees.ResumeID
    LEFT JOIN Skills ON Resumes.ID = Skills.ResumeID
    WHERE Resumes.UserID = ?
    '''
    
    params = [current_user.id]

    if degree:
        query += ' AND Degrees.Degree LIKE ?'
        params.append(f'%{degree}%')
    
    if skills:
        query += ' AND Skills.Skill LIKE ?'
        params.append(f'%{skills}%')
    
    if years_of_experience:
        query += ' AND Resumes."Years of experience" = ?'
        params.append(years_of_experience)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()

    return render_template('search_results.html', results=results)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(directory='static/resumes', filename=filename)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('auth.admin'))

    user_id = current_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT Resumes.Name, 
           GROUP_CONCAT(DISTINCT Degrees.Degree) as Degrees, 
           GROUP_CONCAT(DISTINCT Colleges.CollegeName) as Colleges,
           Resumes.ID
    FROM Resumes
    LEFT JOIN Degrees ON Resumes.ID = Degrees.ResumeID
    LEFT JOIN Colleges ON Resumes.ID = Colleges.ResumeID
    WHERE Resumes.UserID = ?
    GROUP BY Resumes.ID
    '''
    
    cursor.execute(query, (user_id,))
    resumes = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', resumes=resumes)

@app.route('/delete_resume/<int:resume_id>', methods=['POST'])
@login_required
def delete_resume(resume_id):
    user_id = current_user.id
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Delete from Resumes table
        cursor.execute('''
        DELETE FROM Resumes WHERE ID = ? AND UserID = ?
        ''', (resume_id, user_id))

        # Delete from Degrees table
        cursor.execute('''
        DELETE FROM Degrees WHERE ResumeID = ?
        ''', (resume_id,))

        # Delete from Colleges table
        cursor.execute('''
        DELETE FROM Colleges WHERE ResumeID = ?
        ''', (resume_id,))

        # Delete from Companies table
        cursor.execute('''
        DELETE FROM Companies WHERE ResumeID = ?
        ''', (resume_id,))

        # Delete from Skills table
        cursor.execute('''
        DELETE FROM Skills WHERE ResumeID = ?
        ''', (resume_id,))

        conn.commit()

    flash('Resume deleted successfully!', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
