#!/usr/bin/env python3
"""
AI Receptionist - Flask Application
Default template for AI-powered virtual receptionist system
"""

import os
import json
import uuid
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import jwt
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
class Config:
    """Application configuration"""
    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'ai_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    DB_NAME = os.getenv('DB_NAME', 'ai_receptionist')
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
    
    # JWT
    JWT_SECRET = os.getenv('JWT_SECRET', 'change-this-secret-key')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_DAYS = 30
    
    # LLM Service (configure your LLM endpoint here)
    LLM_API_URL = os.getenv('LLM_API_URL', 'http://localhost:3002/v1/chat/completions')
    LLM_API_KEY = os.getenv('LLM_API_KEY', 'your-api-key')
    
    # Application
    APP_PORT = int(os.getenv('APP_PORT', '5000'))
    APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Setup logging
logging.basicConfig(
    level=logging.INFO if not Config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection pool
try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="ai_receptionist_pool",
        pool_size=Config.DB_POOL_SIZE,
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    logger.info("Database connection pool created successfully")
except Exception as e:
    logger.error(f"Failed to create database pool: {e}")
    db_pool = None

# In-memory session storage (use Redis in production)
sessions = {}
sessions_lock = threading.RLock()

# =============================================
# Database Helper Functions
# =============================================

def get_db_connection():
    """Get database connection from pool"""
    if not db_pool:
        logger.error("Database pool not initialized")
        return None
    try:
        return db_pool.get_connection()
    except Exception as e:
        logger.error(f"Failed to get DB connection: {e}")
        return None

def safe_json(data):
    """Safely parse JSON data"""
    if data is None:
        return None
    if isinstance(data, (dict, list)):
        return data
    try:
        return json.loads(data)
    except:
        return None

# =============================================
# Authentication
# =============================================

def generate_token(user_id):
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=Config.JWT_EXPIRATION_DAYS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None

def require_auth(f):
    """Decorator for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header[7:].strip()
        user_id = verify_token(token)
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        g.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated_function

# =============================================
# User Management Routes
# =============================================

@app.route('/v1/auth/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.get_json() or {}
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        if not all([email, password, name]):
            return jsonify({'error': 'All fields required'}), 400
        
        # Hash password (use bcrypt in production)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database error'}), 500
        
        try:
            cursor = conn.cursor()
            
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email already registered'}), 409
            
            # Generate username
            username = email.split('@')[0][:32]
            base_username = username
            counter = 1
            while True:
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if not cursor.fetchone():
                    break
                username = f"{base_username}{counter}"
                counter += 1
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (username, email, name, password_hash, preferences)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                username, email, name, password_hash,
                json.dumps({'greeting_style': 'professional', 'timezone': 'America/Chicago'})
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            # Generate token
            token = generate_token(user_id)
            
            return jsonify({
                'status': 'success',
                'token': token,
                'user': {
                    'id': user_id,
                    'username': username,
                    'name': name,
                    'email': email
                }
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/v1/auth/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json() or {}
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not all([email, password]):
            return jsonify({'error': 'Email and password required'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database error'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, username, name, email, preferences
                FROM users
                WHERE email = %s AND password_hash = %s AND is_active = 1
            """, (email, password_hash))
            
            user = cursor.fetchone()
            
            if user:
                # Update last login
                cursor.execute(
                    "UPDATE users SET last_login = NOW() WHERE id = %s",
                    (user['id'],)
                )
                conn.commit()
                
                token = generate_token(user['id'])
                
                # Parse preferences
                if user['preferences']:
                    user['preferences'] = safe_json(user['preferences'])
                
                return jsonify({
                    'status': 'success',
                    'token': token,
                    'user': user
                })
            else:
                return jsonify({'error': 'Invalid credentials'}), 401
                
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/v1/auth/me', methods=['GET'])
@require_auth
def get_profile():
    """Get current user profile"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database error'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, username, name, email, phone, company, preferences
                FROM users
                WHERE id = %s AND is_active = 1
            """, (g.user_id,))
            
            user = cursor.fetchone()
            
            if user:
                if user['preferences']:
                    user['preferences'] = safe_json(user['preferences'])
                return jsonify({'status': 'success', 'user': user})
            else:
                return jsonify({'error': 'User not found'}), 404
                
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500

# =============================================
# Receptionist Core Routes
# =============================================

@app.route('/v1/receptionist/link', methods=['GET'])
@require_auth
def get_receptionist_link():
    """Get or create receptionist share link"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database error'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Check existing link
            cursor.execute("""
                SELECT slug FROM receptionist_links
                WHERE user_id = %s AND active = 1
            """, (g.user_id,))
            
            row = cursor.fetchone()
            
            if row:
                slug = row['slug']
            else:
                # Generate new slug
                import secrets
                slug = secrets.token_urlsafe(8).lower().replace('_', '-')
                
                cursor.execute("""
                    INSERT INTO receptionist_links (user_id, slug, active)
                    VALUES (%s, %s, 1)
                """, (g.user_id, slug))
                conn.commit()
            
            # Build full URL
            base_url = request.host_url.rstrip('/')
            url = f"{base_url}/recai.html?call={slug}"
            
            return jsonify({
                'status': 'success',
                'slug': slug,
                'url': url
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Get link error: {e}")
        return jsonify({'error': 'Failed to get link'}), 500

@app.route('/v1/receptionist/analytics', methods=['GET'])
@require_auth
def get_analytics():
    """Get call analytics"""
    try:
        timeframe = request.args.get('timeframe', '7d')
        days = int(timeframe.replace('d', '')) if 'd' in timeframe else 7
        start_date = datetime.utcnow() - timedelta(days=days)
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database error'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    AVG(duration) as avg_duration,
                    AVG(sentiment_score) as avg_sentiment,
                    SUM(CASE WHEN JSON_EXTRACT(summary, '$.message_taken') = true THEN 1 ELSE 0 END) as messages_taken
                FROM receptionist_calls
                WHERE user_id = %s AND created_at >= %s
            """, (g.user_id, start_date))
            
            stats = cursor.fetchone() or {}
            
            return jsonify({
                'call_statistics': {
                    'total_calls': int(stats.get('total_calls') or 0),
                    'avg_duration': float(stats.get('avg_duration') or 0),
                    'avg_sentiment': float(stats.get('avg_sentiment') or 0),
                    'messages_taken': int(stats.get('messages_taken') or 0)
                },
                'timeframe': timeframe
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({'error': 'Failed to get analytics'}), 500

# =============================================
# Public Receptionist Routes (No Auth Required)
# =============================================

@app.route('/v1/receptionist/public/target', methods=['GET'])
def get_public_target():
    """Get receptionist target info"""
    try:
        slug = request.args.get('slug', '').strip()
        if not slug:
            return jsonify({'error': 'Slug required'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database error'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.id, u.name, u.company
                FROM receptionist_links rl
                JOIN users u ON u.id = rl.user_id
                WHERE rl.slug = %s AND rl.active = 1 AND u.is_active = 1
            """, (slug,))
            
            user = cursor.fetchone()
            
            if user:
                return jsonify({
                    'status': 'success',
                    'user': user
                })
            else:
                return jsonify({'error': 'Invalid link'}), 404
                
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Get target error: {e}")
        return jsonify({'error': 'Failed to get target'}), 500

@app.route('/v1/receptionist/public/start', methods=['POST'])
def start_public_session():
    """Start public conversation session"""
    try:
        data = request.get_json() or {}
        slug = data.get('slug', '').strip()
        caller_info = data.get('caller_info', {})
        
        if not slug:
            return jsonify({'error': 'Slug required'}), 400
        
        # Get user from slug
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database error'}), 500
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.id, u.name, u.preferences
                FROM receptionist_links rl
                JOIN users u ON u.id = rl.user_id
                WHERE rl.slug = %s AND rl.active = 1
            """, (slug,))
            
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'error': 'Invalid link'}), 404
            
            # Parse preferences
            preferences = safe_json(user['preferences']) or {}
            
            # Generate greeting
            greeting = f"Hello! You've reached {user['name']}'s AI receptionist. How can I help you today?"
            
            # Create session
            session_id = str(uuid.uuid4())
            
            with sessions_lock:
                sessions[session_id] = {
                    'user_id': user['id'],
                    'slug': slug,
                    'caller_info': caller_info,
                    'history': [],
                    'start_time': datetime.utcnow(),
                    'last_activity': datetime.utcnow()
                }
            
            return jsonify({
                'status': 'success',
                'session_id': session_id,
                'greeting': greeting,
                'started_at': datetime.utcnow().isoformat() + 'Z'
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Start session error: {e}")
        return jsonify({'error': 'Failed to start session'}), 500

@app.route('/v1/receptionist/public/message', methods=['POST'])
def send_public_message():
    """Send message in public session"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id', '').strip()
        message = data.get('message', '').strip()
        
        if not all([session_id, message]):
            return jsonify({'error': 'Session ID and message required'}), 400
        
        with sessions_lock:
            session = sessions.get(session_id)
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Add user message to history
        session['history'].append({'role': 'user', 'content': message})
        
        # Generate AI response (simplified for template)
        # In production, call your LLM service here
        ai_response = generate_ai_response(session, message)
        
        # Add AI response to history
        session['history'].append({'role': 'assistant', 'content': ai_response})
        session['last_activity'] = datetime.utcnow()
        
        return jsonify({
            'status': 'success',
            'response': ai_response
        })
        
    except Exception as e:
        logger.error(f"Message error: {e}")
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/v1/receptionist/public/end', methods=['POST'])
def end_public_session():
    """End public conversation session"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id', '').strip()
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        with sessions_lock:
            session = sessions.pop(session_id, None)
        
        if not session:
            return jsonify({'status': 'success', 'message': 'Session not found'})
        
        # Calculate duration
        duration = int((datetime.utcnow() - session['start_time']).total_seconds())
        
        # Save to database
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO receptionist_calls
                    (user_id, session_id, caller_info, conversation, summary, duration, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    session['user_id'],
                    session_id,
                    json.dumps(session['caller_info']),
                    json.dumps(session['history']),
                    json.dumps({'message': 'Session ended'}),
                    duration,
                    session['start_time']
                ))
                conn.commit()
            finally:
                cursor.close()
                conn.close()
        
        return jsonify({
            'status': 'success',
            'duration': duration
        })
        
    except Exception as e:
        logger.error(f"End session error: {e}")
        return jsonify({'error': 'Failed to end session'}), 500

# =============================================
# AI Response Generation
# =============================================

def generate_ai_response(session, message):
    """Generate AI receptionist response"""
    try:
        # Get user preferences
        user_id = session.get('user_id')
        caller_name = session.get('caller_info', {}).get('name', 'Guest')
        
        # Build context for LLM
        system_prompt = f"""You are Emma, a professional AI receptionist. 
        You are polite, helpful, and efficient. Keep responses brief and to the point.
        You're speaking with {caller_name}."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            *session.get('history', [])
        ]
        
        # Call LLM service (configure your endpoint)
        if Config.LLM_API_URL and Config.LLM_API_KEY:
            response = requests.post(
                Config.LLM_API_URL,
                headers={
                    'Authorization': f'Bearer {Config.LLM_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'messages': messages,
                    'temperature': 0.7,
                    'max_tokens': 150
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', 
                       'I understand. Let me take a message for you.')
        
        # Fallback response if LLM unavailable
        return "Thank you for your message. I'll make sure it gets delivered."
        
    except Exception as e:
        logger.error(f"AI response error: {e}")
        return "I apologize for the inconvenience. Your message has been noted."

# =============================================
# Utility Routes
# =============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        'service': 'AI Receptionist API',
        'version': '1.0.0',
        'status': 'running'
    })

# =============================================
# Background Tasks
# =============================================

def cleanup_sessions():
    """Clean up expired sessions"""
    while True:
        try:
            time.sleep(300)  # Every 5 minutes
            
            with sessions_lock:
                now = datetime.utcnow()
                expired = []
                
                for session_id, data in sessions.items():
                    if (now - data['last_activity']).total_seconds() > 1800:  # 30 minutes
                        expired.append(session_id)
                
                for session_id in expired:
                    del sessions[session_id]
                    logger.info(f"Cleaned up session: {session_id}")
                    
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")

# Start cleanup thread
import time
cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
cleanup_thread.start()

# =============================================
# Main Entry Point
# =============================================

if __name__ == '__main__':
    logger.info(f"Starting AI Receptionist on {Config.APP_HOST}:{Config.APP_PORT}")
    app.run(
        host=Config.APP_HOST,
        port=Config.APP_PORT,
        debug=Config.DEBUG
    )
