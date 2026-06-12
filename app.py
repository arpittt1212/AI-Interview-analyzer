import os
import json
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify, stream_with_context
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import database
import ai_analyzer

app = Flask(__name__)
app.secret_key = 'ai_interview_analyzer_secret_key_192837465'

# Configure Upload Folder inside the workspace
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB Max upload limit

# Create upload directory if it does not exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize Database on startup
database.init_db()

# Custom Filter to clean timestamp prefixes from filenames in templates
@app.template_filter('clean_filename')
def clean_filename_filter(s):
    if '_' in s:
        return s.split('_', 1)[-1]
    return s

# 1. Landing Page
@app.route('/')
def index():
    return render_template('index.html')

# 2. User Authentication: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('upload'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        user = database.get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            
    return render_template('login.html')

# 3. User Authentication: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('upload'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # Check if email is already registered
        existing_user = database.get_user_by_email(email)
        if existing_user:
            flash('Email address is already registered.', 'error')
            return render_template('register.html')
            
        # Hash password and create user
        password_hash = generate_password_hash(password)
        user_id = database.create_user(name, email, password_hash)
        
        if user_id:
            session['user_id'] = user_id
            session['user_name'] = name
            session['user_email'] = email
            flash('Registration successful! Welcome to your workspace.', 'success')
            return redirect(url_for('upload'))
        else:
            flash('An error occurred during account creation. Please try again.', 'error')
            
    return render_template('register.html')

# 4. Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

# 5. Upload Interview Route
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('user_id'):
        flash('Please log in to access your workspace.', 'error')
        return redirect(url_for('login'))
        
    gpu_status = ai_analyzer.get_gpu_status()
    
    if request.method == 'POST':
        # Check if file part is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part selected.'})
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file chosen.'})
            
        # Validate file extensions (audio/video formats supported)
        allowed_extensions = {'.mp3', '.wav', '.mp4'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Unsupported file format. Please upload MP3, WAV, or MP4.'})
            
        filename = secure_filename(file.filename)
        # Prepend user ID and timestamp to make file names unique on disk
        unique_filename = f"{session['user_id']}_{int(time.time())}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file to uploads folder
        file.save(file_path)
        
        # Save placeholder record to database to fetch unique interview ID
        interview_id = database.create_interview(
            user_id=session['user_id'],
            file_name=unique_filename,
            transcript="Analysis in progress. Generating speech transcript...",
            comm_score=0,
            conf_score=0,
            gram_score=0,
            speed_score=0,
            quality_score=0,
            overall_score=0,
            speed_wpm=0,
            filler_words_json=json.dumps({"um": 0, "uh": 0, "like": 0, "actually": 0, "basically": 0, "total": 0}),
            feedback_json=json.dumps([]),
            recs_json=json.dumps([])
        )
        
        # Return success with redirection path to the analysis loading page
        return jsonify({
            'success': True,
            'redirect': url_for('analyze', interview_id=interview_id)
        })
        
    return render_template('upload.html', gpu_status=gpu_status)

# 6. Loading/Processing View
@app.route('/analyze/<int:interview_id>')
def analyze(interview_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    # Security: Verify ownership of this interview record
    interview = database.get_interview_by_id(interview_id)
    if not interview or interview['user_id'] != session['user_id']:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('upload'))
        
    return render_template('processing.html', interview_id=interview_id)

# 7. Real-Time Processing SSE Event Stream
@app.route('/process_stream/<int:interview_id>')
def process_stream(interview_id):
    if not session.get('user_id'):
        return Response('Unauthorized', status=401)
        
    interview = database.get_interview_by_id(interview_id)
    if not interview or interview['user_id'] != session['user_id']:
        return Response('Unauthorized', status=401)
        
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], interview['file_name'])

    @stream_with_context
    def generate_progress():
        # Step 0: Upload Complete
        yield f"data: {json.dumps({'stage': '0'})}\n\n"
        time.sleep(1.2)
        
        # Step 1: Speech-to-Text Conversion
        yield f"data: {json.dumps({'stage': '1'})}\n\n"
        time.sleep(1.2)
        
        # Step 2: Transcript Generation
        yield f"data: {json.dumps({'stage': '2'})}\n\n"
        time.sleep(1.2)
        
        # Step 3: Communication Analysis
        yield f"data: {json.dumps({'stage': '3'})}\n\n"
        time.sleep(1.2)
        
        # Step 4: Confidence Analysis
        yield f"data: {json.dumps({'stage': '4'})}\n\n"
        time.sleep(1.2)
        
        # Step 5: Grammar Analysis
        yield f"data: {json.dumps({'stage': '5'})}\n\n"
        time.sleep(1.2)
        
        # Step 6: Performance Scoring
        yield f"data: {json.dumps({'stage': '6'})}\n\n"
        time.sleep(1.2)
        
        # Step 7: AI Feedback Generation
        yield f"data: {json.dumps({'stage': '7'})}\n\n"
        
        try:
            # Run the core AI engine (transcription & NLP score audits)
            results = ai_analyzer.analyze_interview_file(file_path)
            
            # Step 8: Report Ready
            yield f"data: {json.dumps({'stage': '8'})}\n\n"
            time.sleep(1.2)
            
            # Update the SQLite placeholder record with final metrics
            database.update_interview_results(
                interview_id,
                results["transcript"],
                results["communication_score"],
                results["confidence_score"],
                results["grammar_score"],
                results["speaking_speed_score"],
                results["answer_quality_score"],
                results["overall_score"],
                results["speaking_speed"],
                json.dumps(results["filler_words"]),
                json.dumps(results["feedback"]),
                json.dumps(results["recommendations"])
            )
            
            # Stage 'ready' triggers redirect in main.js
            yield f"data: {json.dumps({'stage': 'ready'})}\n\n"
            
        except Exception as e:
            # Yield error logs to client
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return Response(generate_progress(), mimetype='text/event-stream')

# 8. Fallback Polling Route for Stage Status check
@app.route('/analyze_status/<int:interview_id>')
def analyze_status(interview_id):
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    interview = database.get_interview_by_id(interview_id)
    if not interview or interview['user_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 401
        
    # If overall score is non-zero, it means the update SQL has completed
    if interview['overall_score'] > 0:
        return jsonify({'stage': 'ready'})
    return jsonify({'stage': 'processing'})

# 9. Results Dashboard View
@app.route('/results/<int:interview_id>')
def results(interview_id):
    if not session.get('user_id'):
        flash('Please login to access reports.', 'error')
        return redirect(url_for('login'))
        
    # Fetch interview record and verify ownership
    interview_row = database.get_interview_by_id(interview_id)
    if not interview_row or interview_row['user_id'] != session['user_id']:
        flash('Record not found or unauthorized access.', 'error')
        return redirect(url_for('upload'))
        
    interview = dict(interview_row)
    
    # Strip disk timestamp prefixes for neat display in dashboards
    interview['file_name'] = clean_filename_filter(interview['file_name'])
    
    # Deserialize JSON fields
    try:
        filler_counts = json.loads(interview['filler_words'])
    except Exception:
        filler_counts = {"um": 0, "uh": 0, "like": 0, "actually": 0, "basically": 0, "total": 0}
        
    try:
        feedback = json.loads(interview['feedback'])
    except Exception:
        feedback = []
        
    try:
        recommendations = json.loads(interview['recommendations'])
    except Exception:
        recommendations = []
        
    return render_template(
        'results.html',
        interview=interview,
        filler_counts=filler_counts,
        filler_counts_json=json.dumps(filler_counts),
        feedback=feedback,
        recommendations=recommendations
    )

# 10. Reports Archive View
@app.route('/reports')
def reports():
    if not session.get('user_id'):
        flash('Please log in to view reports history.', 'error')
        return redirect(url_for('login'))
        
    db_interviews = database.get_interviews_by_user(session['user_id'])
    interviews = []
    
    for row in db_interviews:
        item = dict(row)
        # Clean file names
        item['file_name'] = clean_filename_filter(item['file_name'])
        
        # Deserialize filler counts for displays
        try:
            item['filler_counts'] = json.loads(item['filler_words'])
        except Exception:
            item['filler_counts'] = {"total": 0}
            
        interviews.append(item)
        
    return render_template('reports.html', interviews=interviews)

# 11. Delete Interview Route
@app.route('/delete/<int:interview_id>')
def delete_report(interview_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
        
    # Fetch record to find disk file
    interview = database.get_interview_by_id(interview_id)
    if interview and interview['user_id'] == session['user_id']:
        # Attempt to delete file from disk
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], interview['file_name'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to remove file from disk: {str(e)}")
                
        # Delete record from database
        database.delete_interview(interview_id, session['user_id'])
        flash('Interview report deleted successfully.', 'success')
    else:
        flash('Unauthorized or record not found.', 'error')
        
    return redirect(url_for('reports'))

# 12. Dashboard View
@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('login'))
        
    db_interviews = database.get_interviews_by_user(session['user_id'])
    
    if not db_interviews:
        return render_template(
            'dashboard.html', 
            interviews_count=0,
            avg_overall_score=0,
            avg_speed=0,
            total_fillers=0,
            history_json='[]',
            fillers_json='{}'
        )
        
    interviews = [dict(row) for row in db_interviews]
    interviews_count = len(interviews)
    
    # Calculate average metrics
    avg_overall_score = int(sum(item['overall_score'] for item in interviews) / interviews_count)
    avg_speed = int(sum(item['speaking_speed'] for item in interviews) / interviews_count)
    
    # Calculate aggregate filler counts
    filler_totals = {"um": 0, "uh": 0, "like": 0, "actually": 0, "basically": 0, "total": 0}
    for item in interviews:
        try:
            fc = json.loads(item['filler_words'])
            for k in filler_totals.keys():
                filler_totals[k] += fc.get(k, 0)
        except Exception:
            pass
            
    # Compile chronological progression data
    chrono_interviews = sorted(interviews, key=lambda x: x['created_at'])
    history_data = []
    for item in chrono_interviews:
        date_str = item['created_at'].split()[0]
        history_data.append({
            "date": date_str,
            "score": item['overall_score']
        })
        
    return render_template(
        'dashboard.html',
        interviews_count=interviews_count,
        avg_overall_score=avg_overall_score,
        avg_speed=avg_speed,
        total_fillers=filler_totals['total'],
        history_json=json.dumps(history_data),
        fillers_json=json.dumps(filler_totals)
    )

# 13. Practice View
@app.route('/practice')
def practice():
    if not session.get('user_id'):
        flash('Please log in to access the practice arena.', 'error')
        return redirect(url_for('login'))
    return render_template('practice.html')

# 14. Settings View
@app.route('/settings')
def settings():
    if not session.get('user_id'):
        flash('Please log in to access settings.', 'error')
        return redirect(url_for('login'))
    return render_template('settings.html')

# 15. Help View
@app.route('/help')
def help_support():
    if not session.get('user_id'):
        flash('Please log in to access support.', 'error')
        return redirect(url_for('login'))
    return render_template('help.html')

if __name__ == '__main__':
    # Run server locally on default port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
