-- AI Receptionist Database Schema
-- Version 1.0
-- Compatible with MySQL 5.7+ / MariaDB 10.3+

CREATE DATABASE IF NOT EXISTS ai_receptionist;
USE ai_receptionist;

-- =============================================
-- Users Table - Core user accounts
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(32) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    phone VARCHAR(20),
    company VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    preferences JSON DEFAULT '{}',
    theme_preference ENUM('light', 'dark', 'auto') DEFAULT 'dark',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- User Contacts - Contact management
-- =============================================
CREATE TABLE IF NOT EXISTS user_contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    company VARCHAR(255),
    relationship ENUM('colleague', 'family', 'friend', 'client', 'vip', 'vendor', 'other') DEFAULT 'other',
    priority INT DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    notes TEXT,
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_priority (priority),
    INDEX idx_relationship (relationship)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Call Rules - Screening and routing rules
-- =============================================
CREATE TABLE IF NOT EXISTS call_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    rule_type ENUM('blacklist', 'whitelist', 'redirect', 'voicemail', 'custom') NOT NULL,
    conditions JSON NOT NULL,
    action JSON NOT NULL,
    priority INT DEFAULT 10,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_active (user_id, active),
    INDEX idx_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Receptionist Calls - Call history and transcripts
-- =============================================
CREATE TABLE IF NOT EXISTS receptionist_calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    caller_info JSON,
    conversation JSON,
    summary JSON,
    sentiment_score FLOAT DEFAULT 0,
    screening_action JSON,
    duration INT DEFAULT 0,
    status ENUM('completed', 'abandoned', 'voicemail', 'blocked') DEFAULT 'completed',
    call_quality ENUM('complete', 'partial', 'incomplete') DEFAULT 'complete',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_session (session_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Receptionist Links - Public share links
-- =============================================
CREATE TABLE IF NOT EXISTS receptionist_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    click_count INT DEFAULT 0,
    last_accessed TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_slug (slug),
    INDEX idx_user_active (user_id, active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Phone Settings - Phone system configuration
-- =============================================
CREATE TABLE IF NOT EXISTS phone_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    phone_enabled BOOLEAN DEFAULT FALSE,
    phone_number VARCHAR(20),
    sip_username VARCHAR(100),
    sip_password VARCHAR(255),
    voicemail_enabled BOOLEAN DEFAULT TRUE,
    voicemail_greeting TEXT,
    call_recording BOOLEAN DEFAULT FALSE,
    business_hours JSON DEFAULT '{}',
    webhook_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_phone_enabled (phone_enabled),
    INDEX idx_phone_number (phone_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Phone Calls - Phone call records
-- =============================================
CREATE TABLE IF NOT EXISTS phone_calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    call_uuid VARCHAR(100) UNIQUE,
    caller_number VARCHAR(20),
    called_number VARCHAR(20),
    duration INT DEFAULT 0,
    recording_url VARCHAR(500),
    transcription TEXT,
    status ENUM('active', 'completed', 'failed', 'busy', 'no_answer') DEFAULT 'active',
    direction ENUM('inbound', 'outbound') DEFAULT 'inbound',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_created (user_id, created_at DESC),
    INDEX idx_call_uuid (call_uuid),
    INDEX idx_status (status),
    INDEX idx_caller (caller_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Messages - Saved messages from callers
-- =============================================
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    call_id INT,
    sender_name VARCHAR(255),
    sender_phone VARCHAR(20),
    sender_email VARCHAR(255),
    message TEXT NOT NULL,
    urgency ENUM('low', 'normal', 'high', 'urgent') DEFAULT 'normal',
    is_read BOOLEAN DEFAULT FALSE,
    follow_up_needed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (call_id) REFERENCES receptionist_calls(id) ON DELETE SET NULL,
    INDEX idx_user_unread (user_id, is_read),
    INDEX idx_urgency (urgency),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Analytics - Aggregated statistics
-- =============================================
CREATE TABLE IF NOT EXISTS analytics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    total_calls INT DEFAULT 0,
    messages_taken INT DEFAULT 0,
    spam_blocked INT DEFAULT 0,
    avg_duration FLOAT DEFAULT 0,
    avg_sentiment FLOAT DEFAULT 0,
    peak_hour INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_date (user_id, date),
    INDEX idx_user_date (user_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- System Logs - Audit trail
-- =============================================
CREATE TABLE IF NOT EXISTS system_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    details JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Default Data - Sample configuration
-- =============================================

-- Create default admin user (password: admin123)
INSERT INTO users (username, email, name, display_name, password_hash, preferences) VALUES 
('admin', 'admin@example.com', 'Admin User', 'Administrator', 
 SHA2('admin123', 256), 
 '{"greeting_style": "professional", "screening_level": "medium", "timezone": "America/Chicago"}')
ON DUPLICATE KEY UPDATE id=id;

-- Create sample call rules
INSERT INTO call_rules (user_id, rule_type, conditions, action, priority) 
SELECT id, 'blacklist', '{"keyword": "warranty"}', '{"type": "block", "reason": "Spam keyword"}', 1
FROM users WHERE username = 'admin'
ON DUPLICATE KEY UPDATE id=id;

-- Create sample business hours
INSERT INTO phone_settings (user_id, business_hours)
SELECT id, '{
  "monday": {"enabled": true, "start": "09:00", "end": "17:00"},
  "tuesday": {"enabled": true, "start": "09:00", "end": "17:00"},
  "wednesday": {"enabled": true, "start": "09:00", "end": "17:00"},
  "thursday": {"enabled": true, "start": "09:00", "end": "17:00"},
  "friday": {"enabled": true, "start": "09:00", "end": "17:00"},
  "saturday": {"enabled": false, "start": "09:00", "end": "12:00"},
  "sunday": {"enabled": false, "start": "09:00", "end": "12:00"}
}'
FROM users WHERE username = 'admin'
ON DUPLICATE KEY UPDATE id=id;

-- =============================================
-- Views for reporting
-- =============================================

CREATE OR REPLACE VIEW daily_call_summary AS
SELECT 
    user_id,
    DATE(created_at) as call_date,
    COUNT(*) as total_calls,
    SUM(CASE WHEN JSON_EXTRACT(summary, '$.message_taken') = true THEN 1 ELSE 0 END) as messages,
    AVG(duration) as avg_duration,
    AVG(sentiment_score) as avg_sentiment
FROM receptionist_calls
GROUP BY user_id, DATE(created_at);

CREATE OR REPLACE VIEW contact_activity AS
SELECT 
    uc.id as contact_id,
    uc.user_id,
    uc.name,
    uc.relationship,
    uc.priority,
    COUNT(rc.id) as call_count,
    MAX(rc.created_at) as last_call
FROM user_contacts uc
LEFT JOIN receptionist_calls rc ON 
    rc.user_id = uc.user_id AND 
    JSON_EXTRACT(rc.caller_info, '$.phone') = uc.phone
GROUP BY uc.id;

-- =============================================
-- Stored Procedures
-- =============================================

DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS cleanup_old_sessions()
BEGIN
    -- Delete sessions older than 30 days
    DELETE FROM receptionist_calls 
    WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
    AND status = 'abandoned';
    
    -- Archive completed calls older than 90 days
    -- (You would move these to an archive table in production)
END$$

CREATE PROCEDURE IF NOT EXISTS update_analytics(IN p_user_id INT, IN p_date DATE)
BEGIN
    INSERT INTO analytics (user_id, date, total_calls, messages_taken, spam_blocked, avg_duration, avg_sentiment)
    SELECT 
        user_id,
        DATE(created_at),
        COUNT(*),
        SUM(CASE WHEN JSON_EXTRACT(summary, '$.message_taken') = true THEN 1 ELSE 0 END),
        SUM(CASE WHEN JSON_EXTRACT(screening_action, '$.action') = 'spam' THEN 1 ELSE 0 END),
        AVG(duration),
        AVG(sentiment_score)
    FROM receptionist_calls
    WHERE user_id = p_user_id AND DATE(created_at) = p_date
    GROUP BY user_id, DATE(created_at)
    ON DUPLICATE KEY UPDATE
        total_calls = VALUES(total_calls),
        messages_taken = VALUES(messages_taken),
        spam_blocked = VALUES(spam_blocked),
        avg_duration = VALUES(avg_duration),
        avg_sentiment = VALUES(avg_sentiment);
END$$

DELIMITER ;

-- =============================================
-- Grants for application user
-- =============================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ai_receptionist.* TO 'ai_user'@'localhost';
-- GRANT EXECUTE ON ai_receptionist.* TO 'ai_user'@'localhost';

-- =============================================
-- Final setup
-- =============================================
SELECT 'AI Receptionist database schema created successfully!' as status;
