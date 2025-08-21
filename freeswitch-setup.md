# FreeSWITCH Integration Guide

This guide covers the installation and configuration of FreeSWITCH to enable phone call support for the AI Receptionist system.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Flask Integration](#flask-integration)
6. [SIP Provider Setup](#sip-provider-setup)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Security Considerations](#security-considerations)

## Overview

FreeSWITCH is an open-source telephony platform that enables the AI Receptionist to:
- Accept incoming phone calls
- Convert speech to text for AI processing
- Play AI responses using text-to-speech
- Record voicemails
- Handle business hours routing

## Prerequisites

### System Requirements

- Ubuntu 20.04+ or Debian 11+
- 4GB RAM minimum (8GB recommended)
- 20GB free disk space
- Public IP address (for external calls)
- Domain name (for WebRTC/secure connections)

### Network Requirements

Open the following ports in your firewall:

```bash
# SIP Signaling
sudo ufw allow 5060/udp
sudo ufw allow 5061/tcp

# WebRTC
sudo ufw allow 5066/tcp
sudo ufw allow 7443/tcp

# STUN/TURN
sudo ufw allow 3478/udp
sudo ufw allow 3478/tcp

# RTP Media (audio)
sudo ufw allow 10000:20000/udp
```

## Installation

### Method 1: Package Manager (Recommended)

```bash
# Add FreeSWITCH repository
wget -O - https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc | sudo apt-key add -
echo "deb http://files.freeswitch.org/repo/deb/debian-release/ `lsb_release -sc` main" | sudo tee /etc/apt/sources.list.d/freeswitch.list
echo "deb-src http://files.freeswitch.org/repo/deb/debian-release/ `lsb_release -sc` main" | sudo tee -a /etc/apt/sources.list.d/freeswitch.list

# Update and install
sudo apt-get update
sudo apt-get install -y freeswitch-meta-all
```

### Method 2: Compile from Source

```bash
# Install dependencies
sudo apt-get install -y git build-essential automake autoconf libtool pkg-config \
    libssl-dev libcurl4-openssl-dev libspeex-dev libopus-dev libedit-dev

# Clone and compile
cd /usr/local/src
sudo git clone https://github.com/signalwire/freeswitch.git
cd freeswitch
sudo ./bootstrap.sh -j
sudo ./configure
sudo make
sudo make install
```

### Install Python ESL Library

```bash
pip install python-ESL
```

## Configuration

### 1. Basic FreeSWITCH Setup

Create the AI Receptionist dialplan:

```bash
sudo nano /etc/freeswitch/dialplan/ai_receptionist.xml
```

```xml
<?xml version="1.0" encoding="utf-8"?>
<include>
  <context name="ai_receptionist">
    <!-- Handle incoming calls -->
    <extension name="ai_incoming">
      <condition field="destination_number" expression="^(\d+)$">
        <!-- Answer the call -->
        <action application="answer"/>
        
        <!-- Set variables -->
        <action application="set" data="call_uuid=${uuid}"/>
        <action application="set" data="caller_number=${caller_id_number}"/>
        
        <!-- Enable recording if configured -->
        <action application="set" data="RECORD_STEREO=true"/>
        <action application="set" data="recording_path=/var/lib/freeswitch/recordings/${uuid}.wav"/>
        
        <!-- Send webhook to Flask -->
        <action application="curl" data="http://localhost:5000/v1/phone/incoming post uuid=${uuid}&amp;caller=${caller_id_number}&amp;destination=$1"/>
        
        <!-- Park call for AI processing -->
        <action application="park"/>
      </condition>
    </extension>
    
    <!-- Voicemail extension -->
    <extension name="voicemail">
      <condition field="destination_number" expression="^vm_(\d+)$">
        <action application="answer"/>
        <action application="sleep" data="1000"/>
        <action application="voicemail" data="default ${domain_name} $1"/>
      </condition>
    </extension>
  </context>
</include>
```

### 2. Configure Event Socket (ESL)

Edit ESL configuration:

```bash
sudo nano /etc/freeswitch/autoload_configs/event_socket.conf.xml
```

```xml
<configuration name="event_socket.conf" description="Socket Client">
  <settings>
    <param name="nat-map" value="false"/>
    <param name="listen-ip" value="127.0.0.1"/>
    <param name="listen-port" value="8021"/>
    <param name="password" value="YourSecurePasswordHere"/>
    <param name="apply-inbound-acl" value="lan"/>
  </settings>
</configuration>
```

### 3. Configure SIP Profile

Edit the internal SIP profile:

```bash
sudo nano /etc/freeswitch/sip_profiles/internal.xml
```

```xml
<profile name="internal">
  <settings>
    <param name="sip-ip" value="$${local_ip_v4}"/>
    <param name="sip-port" value="5060"/>
    <param name="rtp-ip" value="$${local_ip_v4}"/>
    
    <!-- For NAT traversal -->
    <param name="ext-rtp-ip" value="auto-nat"/>
    <param name="ext-sip-ip" value="auto-nat"/>
    
    <!-- WebRTC support -->
    <param name="ws-binding" value=":5066"/>
    <param name="wss-binding" value=":7443"/>
    
    <!-- Codec preferences -->
    <param name="inbound-codec-prefs" value="OPUS,PCMU,PCMA"/>
    <param name="outbound-codec-prefs" value="OPUS,PCMU,PCMA"/>
  </settings>
</profile>
```

### 4. Configure TTS (Text-to-Speech)

Install and configure Flite TTS:

```bash
sudo apt-get install -y flite

# Test TTS
echo "Hello, this is a test" | flite -voice slt
```

Configure mod_flite:

```bash
sudo nano /etc/freeswitch/autoload_configs/modules.conf.xml
```

Add:
```xml
<load module="mod_flite"/>
```

### 5. Set Variables

Edit global variables:

```bash
sudo nano /etc/freeswitch/vars.xml
```

```xml
<include>
  <!-- Your external IP -->
  <X-PRE-PROCESS cmd="set" data="external_ip=YOUR.PUBLIC.IP.HERE"/>
  
  <!-- Domain for WebRTC -->
  <X-PRE-PROCESS cmd="set" data="domain=your-domain.com"/>
  
  <!-- Default password for extensions -->
  <X-PRE-PROCESS cmd="set" data="default_password=ChangeMe123!"/>
</include>
```

## Flask Integration

### 1. Add FreeSWITCH Handler to app.py

```python
import ESL

class FreeSwitchHandler:
    def __init__(self):
        self.host = os.getenv('FREESWITCH_HOST', 'localhost')
        self.port = int(os.getenv('FREESWITCH_PORT', '8021'))
        self.password = os.getenv('FREESWITCH_PASSWORD', 'ClueCon')
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = ESL.ESLconnection(self.host, self.port, self.password)
            if self.connection.connected():
                logger.info("Connected to FreeSWITCH")
                return True
        except Exception as e:
            logger.error(f"FreeSWITCH connection failed: {e}")
        return False
    
    def answer_call(self, uuid):
        if self.connection:
            self.connection.api(f"uuid_answer {uuid}")
    
    def play_tts(self, uuid, text):
        if self.connection:
            # Escape special characters
            text = text.replace("'", "")
            cmd = f"uuid_broadcast {uuid} speak::flite|slt|'{text}'"
            self.connection.api(cmd)
    
    def hangup_call(self, uuid):
        if self.connection:
            self.connection.api(f"uuid_kill {uuid}")

# Initialize handler
fs_handler = FreeSwitchHandler()
```

### 2. Add Phone Webhook Endpoint

```python
@app.route('/v1/phone/incoming', methods=['POST'])
def handle_incoming_call():
    """Handle incoming phone calls from FreeSWITCH"""
    try:
        # Get call details
        call_uuid = request.form.get('uuid')
        caller_number = request.form.get('caller')
        destination = request.form.get('destination')
        
        # Answer the call
        fs_handler.answer_call(call_uuid)
        
        # Play greeting
        greeting = "Hello, you've reached our AI receptionist. How can I help you?"
        fs_handler.play_tts(call_uuid, greeting)
        
        # Create session for this call
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            'call_uuid': call_uuid,
            'caller': caller_number,
            'type': 'phone',
            'start_time': datetime.utcnow()
        }
        
        return jsonify({'status': 'success', 'session_id': session_id})
        
    except Exception as e:
        logger.error(f"Call handling error: {e}")
        return jsonify({'error': str(e)}), 500
```

### 3. Update .env File

```env
# FreeSWITCH Configuration
FREESWITCH_HOST=localhost
FREESWITCH_PORT=8021
FREESWITCH_PASSWORD=YourSecurePasswordHere
```

## SIP Provider Setup

### Option 1: Twilio SIP Trunk

1. Create a Twilio account
2. Purchase a phone number
3. Create SIP trunk configuration:

```bash
sudo nano /etc/freeswitch/sip_profiles/external/twilio.xml
```

```xml
<gateway name="twilio">
  <param name="username" value="YOUR_TWILIO_SID"/>
  <param name="password" value="YOUR_TWILIO_AUTH_TOKEN"/>
  <param name="proxy" value="YOUR_DOMAIN.pstn.twilio.com"/>
  <param name="register" value="false"/>
  <param name="caller-id-in-from" value="true"/>
</gateway>
```

### Option 2: Generic SIP Provider

```xml
<gateway name="my_provider">
  <param name="username" value="your_sip_username"/>
  <param name="password" value="your_sip_password"/>
  <param name="realm" value="sip.provider.com"/>
  <param name="proxy" value="sip.provider.com"/>
  <param name="register" value="true"/>
  <param name="expire-seconds" value="600"/>
</gateway>
```

## Testing

### 1. Test FreeSWITCH Status

```bash
# Enter FreeSWITCH console
sudo fs_cli

# Check status
/status

# Check SIP registrations
/sofia status

# Exit console
/exit
```

### 2. Test ESL Connection

```python
# test_esl.py
import ESL

conn = ESL.ESLconnection('localhost', '8021', 'YourPasswordHere')
if conn.connected():
    print("ESL connection successful!")
    e = conn.api("status")
    print(e.getBody())
else:
    print("Failed to connect")
```

### 3. Make Test Call

```bash
# From fs_cli console
originate user/1000 &echo()

# Or call the AI receptionist
originate user/1000 &transfer(ai_receptionist XML ai_receptionist)
```

### 4. Test WebRTC (Browser Calling)

Create test HTML:

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/sip.js@0.20.0/dist/sip.min.js"></script>
</head>
<body>
    <button onclick="makeCall()">Test Call</button>
    <script>
        const userAgent = new SIP.UserAgent({
            uri: 'sip:test@your-domain.com',
            transportOptions: {
                server: 'wss://your-domain.com:7443'
            }
        });
        
        function makeCall() {
            const target = SIP.UserAgent.makeURI('sip:ai_receptionist@your-domain.com');
            const inviter = new SIP.Inviter(userAgent, target);
            inviter.invite();
        }
    </script>
</body>
</html>
```

## Troubleshooting

### FreeSWITCH Won't Start

```bash
# Check for errors
sudo journalctl -u freeswitch -n 50

# Check if port is in use
sudo netstat -tulpn | grep 5060

# Verify permissions
sudo chown -R freeswitch:freeswitch /etc/freeswitch
sudo chown -R freeswitch:freeswitch /var/lib/freeswitch
```

### No Audio on Calls

```bash
# Check codec support
fs_cli -x "show codecs"

# Verify RTP ports are open
sudo iptables -L -n | grep 10000

# Test audio device
fs_cli -x "originate user/1000 &playback(/usr/share/freeswitch/sounds/en/us/callie/ivr/8000/ivr-welcome.wav)"
```

### ESL Connection Failed

```bash
# Verify ESL is listening
netstat -an | grep 8021

# Check ACL settings
fs_cli -x "show api"

# Test with default password
fs_cli -H localhost -P 8021 -p ClueCon
```

### Calls Not Routing to Flask

```bash
# Check webhook URL
curl -X POST http://localhost:5000/v1/phone/incoming \
  -d "uuid=test-uuid&caller=1234567890&destination=1000"

# Monitor FreeSWITCH logs
fs_cli -x "console loglevel debug"
```

## Security Considerations

### 1. Change Default Passwords

```bash
# Generate strong password
openssl rand -base64 32

# Update in:
# - /etc/freeswitch/autoload_configs/event_socket.conf.xml
# - /etc/freeswitch/vars.xml
# - .env file
```

### 2. Implement Rate Limiting

```xml
<!-- In SIP profile -->
<param name="max-registrations-per-extension" value="2"/>
<param name="challenge-realm" value="auto_from"/>
<param name="nonce-ttl" value="60"/>
```

### 3. Enable TLS/SRTP

```bash
# Generate certificates
cd /etc/freeswitch/tls
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout server.key -out server.crt

# Configure in SIP profile
<param name="tls" value="true"/>
<param name="tls-only" value="false"/>
<param name="tls-bind-params" value="transport=tls"/>
<param name="tls-cert-dir" value="/etc/freeswitch/tls"/>
```

### 4. Firewall Rules

```bash
# Restrict ESL to localhost only
sudo ufw delete allow 8021
sudo ufw allow from 127.0.0.1 to any port 8021

# Restrict SIP to known providers
sudo ufw allow from PROVIDER_IP to any port 5060
```

## Performance Tuning

### 1. Increase Limits

```bash
# Edit /etc/security/limits.conf
freeswitch soft nofile 65536
freeswitch hard nofile 65536
freeswitch soft nproc 32768
freeswitch hard nproc 32768
```

### 2. Optimize Database

```xml
<!-- In switch.conf.xml -->
<param name="max-sessions" value="1000"/>
<param name="sessions-per-second" value="30"/>
<param name="rtp-start-port" value="10000"/>
<param name="rtp-end-port" value="20000"/>
```

## Monitoring

### Setup Log Rotation

```bash
sudo nano /etc/logrotate.d/freeswitch
```

```
/var/log/freeswitch/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    sharedscripts
    postrotate
        /usr/bin/fs_cli -x "fsctl send_sighup" > /dev/null
    endscript
}
```

### Monitor with Fail2ban

```bash
sudo apt-get install fail2ban

# Create jail
sudo nano /etc/fail2ban/jail.d/freeswitch.conf
```

```ini
[freeswitch]
enabled = true
port = 5060,5061,5080,5081
protocol = udp
filter = freeswitch
logpath = /var/log/freeswitch/freeswitch.log
maxretry = 10
bantime = 3600
findtime = 600
```

## Next Steps

1. Configure your SIP provider
2. Update DNS records for your domain
3. Test incoming and outgoing calls
4. Set up monitoring and alerts
5. Configure backup and disaster recovery

## Support Resources

- [FreeSWITCH Documentation](https://freeswitch.org/confluence/)
- [FreeSWITCH Forums](https://forum.freeswitch.org/)
- [ESL Python Documentation](https://freeswitch.org/confluence/display/FREESWITCH/Python+ESL)
- [SIP Debugging Guide](https://freeswitch.org/confluence/display/FREESWITCH/Debugging)

---

**Note:** This guide assumes FreeSWITCH 1.10.x. Some configurations may vary for different versions.
