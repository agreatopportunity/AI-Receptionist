# AI-Receptionist
Walk Through for AI Receptionist 

# AI Receptionist System with FreeSWITCH Integration

A professional AI-powered virtual receptionist that handles web-based interactions and real phone calls through FreeSWITCH integration. The system screens calls, takes messages, manages contacts, and provides 24/7 availability.

## Features

### Core Functionality
- **AI-Powered Conversations** - Natural language processing for realistic interactions
- **Multi-Channel Support** - Web interface and phone system integration
- **Smart Call Screening** - Automatic spam detection and VIP recognition
- **Message Taking** - Detailed message capture with sentiment analysis
- **Contact Management** - Prioritized contact database with relationship tracking
- **Call History** - Complete conversation transcripts and analytics

### Phone System Features (FreeSWITCH)
- **Real Phone Call Support** - Accept calls from any phone number
- **Business Hours** - Automatic after-hours handling with voicemail
- **Call Recording** - Optional recording of all conversations
- **WebRTC Support** - Browser-based calling capability
- **Speech-to-Text** - Real-time transcription of phone conversations
- **Text-to-Speech** - Natural voice responses from AI

## System Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Phone      │────▶│  FreeSWITCH  │────▶│    Flask     │
│   Network    │     │    Server    │     │   Backend    │
└──────────────┘     └──────────────┘     └──────────────┘
                             │                     │
                             ▼                     ▼
                     ┌──────────────┐     ┌──────────────┐
                     │   WebRTC     │     │     LLM      │
                     │   Browser    │     │   Service    │
                     └──────────────┘     └──────────────┘
```

## Prerequisites

- Ubuntu 20.04+ or Debian 11+
- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- 2GB RAM minimum (4GB recommended)
- Public IP address (for phone system)
- Domain name with SSL certificate (for production)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/agreatopportunity/ai-receptionist.git
cd ai-receptionist
```

### 2. Database Setup

```sql
CREATE DATABASE ai_receptionist;
CREATE USER 'ai_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ai_receptionist.* TO 'ai_user'@'localhost';
FLUSH PRIVILEGES;

-- Run the schema
mysql -u ai_user -p ai_receptionist < schema.sql
```

### 3. Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Environment Configuration

Create `.env` file:

```bash
# Database
DB_HOST=localhost
DB_USER=ai_user
DB_PASSWORD=your_password
DB_NAME=ai_receptionist

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET=your_jwt_secret_here

# LLM Service
API_KEY=your_llm_api_key

# FreeSWITCH (if using phone system)
FREESWITCH_HOST=localhost
FREESWITCH_PORT=8021
FREESWITCH_PASSWORD=ClueCon
FREESWITCH_WS_PORT=5066
```

### 5. FreeSWITCH Installation (Optional - for phone support)

```bash
# Run the setup script
sudo bash setup_freeswitch.sh

# Verify installation
fs_cli -x "status"
```

## File Structure

```
ai-receptionist/
├── app.py                      # Main Flask application
├── yourfrontend.html           # Frontend interface
├── requirements.txt            # Python dependencies
├── schema.sql                  # Database schema
├── setup_freeswitch.sh         # FreeSWITCH installation script
├── freeswitch/
│   ├── dialplan/              # Call routing rules
│   ├── sip_profiles/          # SIP configurations
│   └── autoload_configs/      # Module configurations
├── static/
│   └── css/                   # Stylesheets
└── README.md                  # This file
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(32) UNIQUE,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    phone VARCHAR(20),
    company VARCHAR(255),
    password_hash VARCHAR(255),
    preferences JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Key Tables
- `users` - User accounts and preferences
- `user_contacts` - Contact database with priorities
- `call_rules` - Screening and routing rules
- `receptionist_calls` - Call history and transcripts
- `phone_settings` - Phone system configuration
- `phone_calls` - Phone call records

## Configuration

### Basic Setup

1. **Start the Flask server:**
```bash
python app.py
# Or for production:
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. **Access the web interface:**
```
http://localhost:5000/recai.html
```

3. **Create an account:**
- Click "Sign In"
- Register with email and password
- Configure your receptionist settings

### Phone System Setup

1. **Enable phone system in dashboard:**
- Toggle "Phone System" switch
- Enter your phone number
- Set business hours
- Save settings

2. **Configure SIP provider:**

For Twilio:
```xml
<gateway name="twilio">
  <param name="username" value="your_account_sid"/>
  <param name="password" value="your_auth_token"/>
  <param name="proxy" value="your-domain.pstn.twilio.com"/>
  <param name="register" value="false"/>
</gateway>
```

For generic SIP:
```xml
<gateway name="voip_provider">
  <param name="username" value="your_sip_username"/>
  <param name="password" value="your_sip_password"/>
  <param name="proxy" value="sip.provider.com"/>
  <param name="register" value="true"/>
</gateway>
```

3. **Test the connection:**
```bash
fs_cli -x "sofia status"
fs_cli -x "sofia status gateway your_gateway"
```

## Usage

### For Users (Owners)

1. **Share your link:**
   - Copy your unique receptionist link
   - Share with contacts/clients
   - Link format: `https://your-domain.com/recai.html?call=your-slug`

2. **Manage contacts:**
   - Add VIP contacts for priority handling
   - Set relationship types (family, colleague, client)
   - Priority 9-10 gets immediate attention

3. **Configure call rules:**
   - Blacklist spam numbers
   - Set screening levels
   - Configure business hours

4. **Review conversations:**
   - Click any call in history to see full transcript
   - View sentiment analysis
   - Check message details

### For Callers

1. **Web interface:**
   - Visit the shared link
   - Enter contact information
   - Chat with Emma (AI receptionist)

2. **Phone calls (if enabled):**
   - Call the configured phone number
   - Speak naturally with the AI
   - Leave messages if needed

## API Endpoints

### Authentication
```
POST /v1/auth/register     - Create account
POST /v1/auth/login        - Sign in
GET  /v1/auth/me          - Get profile
```

### Receptionist
```
GET  /v1/receptionist/link              - Get share link
POST /v1/receptionist/personalized_chat - Owner chat session
GET  /v1/receptionist/analytics         - Call statistics
GET  /v1/receptionist/history           - Call history
POST /v1/receptionist/contacts          - Manage contacts
GET  /v1/receptionist/call_rules        - Screening rules
```

### Public (No Auth)
```
GET  /v1/receptionist/public/target     - Get receptionist info
POST /v1/receptionist/public/start      - Start conversation
POST /v1/receptionist/public/message    - Send message
POST /v1/receptionist/public/end        - End conversation
```

### Phone System
```
GET  /v1/phone/settings    - Get phone configuration
POST /v1/phone/settings    - Update phone settings
POST /v1/phone/incoming    - FreeSWITCH webhook
POST /v1/phone/test        - Test call
```

## Security Considerations

### Production Deployment

1. **Use HTTPS:**
```bash
certbot certonly --standalone -d your-domain.com
```

2. **Secure FreeSWITCH:**
```bash
# Change default passwords
fs_cli -x "fsctl send_sighup"

# Update firewall
ufw allow 5060/udp  # SIP
ufw allow 10000:20000/udp  # RTP
ufw deny 8021  # Block ESL from external
```

3. **Environment variables:**
- Never commit `.env` file
- Use strong JWT secrets
- Rotate API keys regularly

4. **Database security:**
- Use prepared statements (already implemented)
- Regular backups
- Encrypted connections for remote DB

## Troubleshooting

### Common Issues

**FreeSWITCH won't start:**
```bash
# Check logs
tail -f /var/log/freeswitch/freeswitch.log

# Verify permissions
chown -R freeswitch:freeswitch /etc/freeswitch
```

**No audio on calls:**
```bash
# Check codec support
fs_cli -x "show codecs"

# Verify RTP ports
netstat -udpn | grep freeswitch
```

**Database connection errors:**
```bash
# Test connection
mysql -u ai_user -p ai_receptionist -e "SELECT 1"

# Check Flask logs
tail -f app.log
```

**WebRTC not working:**
- Ensure SSL certificates are valid
- Check STUN/TURN server is running
- Verify firewall allows ports 3478, 7443

### Debug Commands

```bash
# FreeSWITCH console
fs_cli

# Watch SIP traffic
fs_cli -x "sofia global siptrace on"

# Monitor calls
fs_cli -x "show calls"

# Python ESL test
python3 -c "import ESL; con = ESL.ESLconnection('localhost', '8021', 'ClueCon'); print(con.connected())"
```

## Performance Optimization

### Database
```sql
-- Add indexes for common queries
CREATE INDEX idx_user_calls ON receptionist_calls(user_id, created_at);
CREATE INDEX idx_caller_info ON receptionist_calls(caller_info(255));
CREATE INDEX idx_session ON receptionist_calls(session_id);
```

### FreeSWITCH
```xml
<!-- Optimize RTP handling -->
<param name="rtp-timeout-sec" value="300"/>
<param name="rtp-hold-timeout-sec" value="1800"/>
<param name="disable-transcoding" value="true"/>
```

### Flask
```python
# Use connection pooling
from sqlalchemy import create_engine
engine = create_engine('mysql://...', pool_size=20, max_overflow=0)
```

## Monitoring

### Metrics to Track
- Call volume per hour/day
- Average call duration
- Sentiment scores
- Response times
- Failed calls
- Spam detection rate

### Log Files
```bash
/var/log/freeswitch/freeswitch.log    # FreeSWITCH main log
/var/log/ai-receptionist/app.log      # Application log
/var/log/mysql/error.log              # Database errors
/var/log/nginx/access.log             # Web server access
```

## Backup and Recovery

### Database Backup
```bash
# Daily backup script
#!/bin/bash
mysqldump -u ai_user -p ai_receptionist > backup_$(date +%Y%m%d).sql
```

### FreeSWITCH Backup
```bash
tar -czf freeswitch_backup.tar.gz /etc/freeswitch
```

## Cost Analysis

### Self-Hosted
- **Server**: $10-40/month (DigitalOcean/AWS/Linode)
- **Phone Number**: $1-15/month (Twilio/Telnyx)
- **Minutes**: $0.007-0.02/minute
- **Total**: ~$15-60/month + usage

### Managed Services Alternative
- **Twilio Flex**: $150/user/month
- **Five9**: $149/user/month
- **Dialpad AI**: $95/user/month


### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- FreeSWITCH community for telephony platform
- OpenAI/Anthropic for LLM capabilities
- Flask community for web framework
- Contributors and testers

## Version History

- **v1.0.0** - Initial release with web interface
- **v1.1.0** - Added FreeSWITCH phone integration
- **v1.2.0** - WebRTC support and real-time transcription
- **v1.3.0** - Enhanced spam detection and analytics

---

**Note**: This is an active project. Check for updates regularly and always test in a development environment before deploying to production.
