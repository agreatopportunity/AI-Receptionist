# AI Receptionist System

A professional AI-powered virtual receptionist that handles web-based interactions and optional phone system integration. The system screens calls, takes messages, manages contacts, and provides 24/7 availability.

## Features

- 🤖 AI-powered conversation handling
- 📞 Optional phone system integration (FreeSWITCH)
- 🛡️ Smart spam detection and VIP recognition
- 📝 Detailed message taking with sentiment analysis
- 👥 Contact management with priority levels
- 📊 Analytics and call history
- 🔒 JWT-based authentication
- 🌐 Web-based interface (responsive design)

## Prerequisites

- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- Node.js (optional, for frontend development)
- 2GB RAM minimum (4GB recommended for production)

## Quick Start Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Database

```bash
mysql -u root -p < schema.sql
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_USER=ai_user
DB_PASSWORD=your_password
DB_NAME=ai_receptionist
JWT_SECRET=your-secret-key-here
LLM_API_URL=your-llm-endpoint
LLM_API_KEY=your-api-key
```

### 4. Run the Application

```bash
python app.py
```

### 5. Access the Interface

Open your browser and navigate to:

```
http://localhost:5000/recai.html
```

## Default Credentials

- **Email:** admin@example.com
- **Password:** admin123

⚠️ **Important:** Change these credentials immediately after first login!

## Configuration

### Security Configuration

Before deploying to production, ensure you:

- ✅ Generate a new JWT_SECRET: `openssl rand -hex 32`
- ✅ Change the default admin password
- ✅ Update database credentials
- ✅ Enable HTTPS with valid SSL certificates
- ✅ Configure firewall rules
- ✅ Set `DEBUG=False` in production

### Application Configuration

Update these settings for your deployment:

- **API Base URL** in `recai.html` (line 399)
- **LLM Service Endpoint** in `app.py` 
- **Company Branding** in HTML templates
- **Time Zone** in user preferences
- **Port Number** if needed (default: 5000)

### Optional Features

- **FreeSWITCH Phone Integration** - Requires additional setup (see `/docs/freeswitch-setup.md`)
- **Redis Session Storage** - Recommended for production scalability
- **SSL Certificates** - Required for HTTPS in production
- **Email Notifications** - Configure SMTP settings
- **Webhook Integrations** - Connect to external services

## Project Structure

```
ai-receptionist/
├── app.py                 # Main Flask application
├── recai.html            # Frontend interface
├── requirements.txt      # Python dependencies
├── schema.sql           # Database schema
├── .env                 # Environment variables (create this)
├── README.md           # This file
└── docs/               # Additional documentation
    └── freeswitch-setup.md
```

## API Endpoints

### Authentication
- `POST /v1/auth/register` - Create new account
- `POST /v1/auth/login` - User login
- `GET /v1/auth/me` - Get current user profile

### Receptionist (Protected)
- `GET /v1/receptionist/link` - Get share link
- `GET /v1/receptionist/analytics` - Get statistics
- `GET /v1/receptionist/history` - Call history

### Public (No Auth)
- `GET /v1/receptionist/public/target` - Get receptionist info
- `POST /v1/receptionist/public/start` - Start conversation
- `POST /v1/receptionist/public/message` - Send message
- `POST /v1/receptionist/public/end` - End conversation

## Development

### Running in Development Mode

```bash
# Set debug mode
export DEBUG=True

# Run with auto-reload
python app.py
```

### Running Tests

```bash
pytest tests/
```

## Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker

```bash
docker build -t ai-receptionist .
docker run -p 5000:5000 --env-file .env ai-receptionist
```

### Systemd Service

Create `/etc/systemd/system/ai-receptionist.service`:

```ini
[Unit]
Description=AI Receptionist Service
After=network.target mysql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-receptionist
Environment="PATH=/opt/ai-receptionist/venv/bin"
ExecStart=/opt/ai-receptionist/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Common Issues

**Database Connection Error:**
- Verify MySQL is running: `systemctl status mysql`
- Check credentials in `.env` file
- Ensure database exists: `mysql -u root -p -e "SHOW DATABASES;"`

**LLM Not Responding:**
- Verify LLM_API_URL is correct
- Check API key is valid
- Test endpoint directly with curl

**Port Already in Use:**
- Change port in app.py: `APP_PORT=5001`
- Or kill existing process: `lsof -i :5000`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask framework for the backend
- MySQL for database management
- FreeSWITCH for optional phone integration
- Contributors and testers

---

**Version:** 1.0.0  
**Last Updated:** 2024  
**Status:** Active Development
