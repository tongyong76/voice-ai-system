-- Voice AI System Database Initialization

CREATE DATABASE IF NOT EXISTS voice_ai
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE voice_ai;

-- Device table
CREATE TABLE IF NOT EXISTS devices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128),
    location VARCHAR(256),
    firmware_version VARCHAR(32),
    status ENUM('online', 'offline', 'busy', 'error') DEFAULT 'offline',
    last_heartbeat DATETIME,
    last_upload DATETIME,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_heartbeat (last_heartbeat)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Task table
CREATE TABLE IF NOT EXISTS tasks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    target_device_ids JSON,
    config JSON,
    status ENUM('pending', 'dispatched', 'running', 'completed', 'failed') DEFAULT 'pending',
    scheduled_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    created_by BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audio records table
CREATE TABLE IF NOT EXISTS audio_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    device_id BIGINT NOT NULL,
    task_id BIGINT,
    file_path VARCHAR(512) NOT NULL,
    file_size BIGINT,
    duration_ms INT,
    sample_rate INT DEFAULT 16000,
    format VARCHAR(16) DEFAULT 'opus',
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    inference_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    INDEX idx_device_time (device_id, upload_time),
    INDEX idx_inference (inference_status),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Transcript table
CREATE TABLE IF NOT EXISTS transcripts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    audio_id BIGINT NOT NULL,
    full_text TEXT,
    language VARCHAR(16) DEFAULT 'zh',
    segments JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audio (audio_id),
    FULLTEXT INDEX ft_text (full_text),
    FOREIGN KEY (audio_id) REFERENCES audio_records(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Speaker records table
CREATE TABLE IF NOT EXISTS speaker_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    audio_id BIGINT NOT NULL,
    speaker_label VARCHAR(64),
    speaker_id BIGINT,
    embedding BLOB,
    confidence FLOAT,
    start_ms INT,
    end_ms INT,
    INDEX idx_audio (audio_id),
    INDEX idx_speaker (speaker_id),
    FOREIGN KEY (audio_id) REFERENCES audio_records(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Speaker table
CREATE TABLE IF NOT EXISTS speakers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    tags JSON,
    embedding BLOB,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Emotion records table
CREATE TABLE IF NOT EXISTS emotion_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    audio_id BIGINT NOT NULL,
    label VARCHAR(32),
    confidence FLOAT,
    start_ms INT,
    end_ms INT,
    INDEX idx_audio (audio_id),
    FOREIGN KEY (audio_id) REFERENCES audio_records(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- NLU results table
CREATE TABLE IF NOT EXISTS nlu_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    audio_id BIGINT NOT NULL,
    keywords JSON,
    intent VARCHAR(64),
    entities JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audio (audio_id),
    FOREIGN KEY (audio_id) REFERENCES audio_records(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Alert rules table
CREATE TABLE IF NOT EXISTS alert_rules (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    condition_type VARCHAR(32),
    condition_expr JSON,
    action_type VARCHAR(32),
    action_target VARCHAR(256),
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Alert logs table
CREATE TABLE IF NOT EXISTS alert_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_id BIGINT,
    audio_id BIGINT,
    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by BIGINT,
    INDEX idx_time (triggered_at),
    INDEX idx_acknowledged (acknowledged)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
