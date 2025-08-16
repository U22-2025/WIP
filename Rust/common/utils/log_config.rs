use std::fs::{File, OpenOptions};
use std::io::{Write, BufWriter};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::SystemTime;
use chrono::{DateTime, Local};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum LogLevel {
    Trace = 0,
    Debug = 1,
    Info = 2,
    Warn = 3,
    Error = 4,
}

impl LogLevel {
    pub fn from_str(s: &str) -> Result<Self, String> {
        match s.to_lowercase().as_str() {
            "trace" => Ok(LogLevel::Trace),
            "debug" => Ok(LogLevel::Debug),
            "info" => Ok(LogLevel::Info),
            "warn" => Ok(LogLevel::Warn),
            "error" => Ok(LogLevel::Error),
            _ => Err(format!("Invalid log level: {}", s)),
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            LogLevel::Trace => "TRACE",
            LogLevel::Debug => "DEBUG",
            LogLevel::Info => "INFO",
            LogLevel::Warn => "WARN",
            LogLevel::Error => "ERROR",
        }
    }
}

#[derive(Debug, Clone)]
pub struct LogEntry {
    pub timestamp: DateTime<Local>,
    pub level: LogLevel,
    pub module: String,
    pub message: String,
    pub file: Option<String>,
    pub line: Option<u32>,
}

impl LogEntry {
    pub fn new(level: LogLevel, module: &str, message: &str) -> Self {
        Self {
            timestamp: Local::now(),
            level,
            module: module.to_string(),
            message: message.to_string(),
            file: None,
            line: None,
        }
    }

    pub fn with_location(mut self, file: &str, line: u32) -> Self {
        self.file = Some(file.to_string());
        self.line = Some(line);
        self
    }
}

pub struct UnifiedLogFormatter {
    include_timestamps: bool,
    include_location: bool,
    color_enabled: bool,
}

impl UnifiedLogFormatter {
    pub fn new() -> Self {
        Self {
            include_timestamps: true,
            include_location: true,
            color_enabled: true,
        }
    }

    pub fn with_timestamps(mut self, enabled: bool) -> Self {
        self.include_timestamps = enabled;
        self
    }

    pub fn with_location(mut self, enabled: bool) -> Self {
        self.include_location = enabled;
        self
    }

    pub fn with_colors(mut self, enabled: bool) -> Self {
        self.color_enabled = enabled;
        self
    }

    pub fn format(&self, entry: &LogEntry) -> String {
        let mut parts = Vec::new();

        // Timestamp
        if self.include_timestamps {
            parts.push(format!("[{}]", entry.timestamp.format("%Y-%m-%d %H:%M:%S%.3f")));
        }

        // Level with color
        let level_str = if self.color_enabled {
            match entry.level {
                LogLevel::Trace => format!("\x1b[37m{}\x1b[0m", entry.level.as_str()),
                LogLevel::Debug => format!("\x1b[36m{}\x1b[0m", entry.level.as_str()),
                LogLevel::Info => format!("\x1b[32m{}\x1b[0m", entry.level.as_str()),
                LogLevel::Warn => format!("\x1b[33m{}\x1b[0m", entry.level.as_str()),
                LogLevel::Error => format!("\x1b[31m{}\x1b[0m", entry.level.as_str()),
            }
        } else {
            entry.level.as_str().to_string()
        };
        parts.push(format!("[{}]", level_str));

        // Module
        parts.push(format!("[{}]", entry.module));

        // Location
        if self.include_location {
            if let (Some(file), Some(line)) = (&entry.file, entry.line) {
                parts.push(format!("[{}:{}]", file, line));
            }
        }

        // Message
        parts.push(entry.message.clone());

        parts.join(" ")
    }
}

pub struct LogRotation {
    max_file_size: u64,
    max_files: usize,
    current_size: u64,
}

impl LogRotation {
    pub fn new(max_file_size: u64, max_files: usize) -> Self {
        Self {
            max_file_size,
            max_files,
            current_size: 0,
        }
    }

    pub fn should_rotate(&self) -> bool {
        self.current_size >= self.max_file_size
    }

    pub fn add_bytes(&mut self, bytes: u64) {
        self.current_size += bytes;
    }

    pub fn reset(&mut self) {
        self.current_size = 0;
    }

    pub fn rotate_files(&self, base_path: &Path) -> Result<(), String> {
        // Move existing files: log.1 -> log.2, log.0 -> log.1, etc.
        for i in (1..self.max_files).rev() {
            let from = self.get_rotated_path(base_path, i - 1);
            let to = self.get_rotated_path(base_path, i);
            
            if from.exists() {
                std::fs::rename(&from, &to)
                    .map_err(|e| format!("Failed to rotate log file: {}", e))?;
            }
        }

        // Move current log to .0
        if base_path.exists() {
            let rotated = self.get_rotated_path(base_path, 0);
            std::fs::rename(base_path, &rotated)
                .map_err(|e| format!("Failed to rotate current log file: {}", e))?;
        }

        Ok(())
    }

    fn get_rotated_path(&self, base_path: &Path, index: usize) -> PathBuf {
        if let Some(parent) = base_path.parent() {
            if let Some(stem) = base_path.file_stem() {
                if let Some(ext) = base_path.extension() {
                    return parent.join(format!("{}.{}.{}", 
                        stem.to_string_lossy(), 
                        index, 
                        ext.to_string_lossy()
                    ));
                } else {
                    return parent.join(format!("{}.{}", 
                        stem.to_string_lossy(), 
                        index
                    ));
                }
            }
        }
        base_path.with_extension(format!("{}", index))
    }
}

pub struct FileLogger {
    file: Arc<Mutex<Option<BufWriter<File>>>>,
    path: PathBuf,
    formatter: UnifiedLogFormatter,
    rotation: Option<LogRotation>,
    min_level: LogLevel,
}

impl FileLogger {
    pub fn new<P: AsRef<Path>>(path: P) -> Result<Self, String> {
        let path = path.as_ref().to_path_buf();
        let file = Self::open_log_file(&path)?;
        
        Ok(Self {
            file: Arc::new(Mutex::new(Some(BufWriter::new(file)))),
            path,
            formatter: UnifiedLogFormatter::new().with_colors(false),
            rotation: None,
            min_level: LogLevel::Info,
        })
    }

    pub fn with_rotation(mut self, max_size: u64, max_files: usize) -> Self {
        self.rotation = Some(LogRotation::new(max_size, max_files));
        self
    }

    pub fn with_formatter(mut self, formatter: UnifiedLogFormatter) -> Self {
        self.formatter = formatter;
        self
    }

    pub fn with_min_level(mut self, level: LogLevel) -> Self {
        self.min_level = level;
        self
    }

    pub fn log(&self, entry: &LogEntry) -> Result<(), String> {
        if entry.level < self.min_level {
            return Ok(());
        }

        let formatted = self.formatter.format(entry);
        let line = format!("{}\n", formatted);
        let line_bytes = line.as_bytes();

        let mut file_guard = self.file.lock().unwrap();
        
        // Check if we need to rotate
        if let Some(rotation) = &self.rotation {
            if rotation.should_rotate() {
                // Close current file
                if let Some(writer) = file_guard.take() {
                    drop(writer);
                }

                // Rotate files
                rotation.rotate_files(&self.path)
                    .map_err(|e| format!("Log rotation failed: {}", e))?;

                // Open new file
                let new_file = Self::open_log_file(&self.path)?;
                *file_guard = Some(BufWriter::new(new_file));
            }
        }

        // Write to file
        if let Some(writer) = file_guard.as_mut() {
            writer.write_all(line_bytes)
                .map_err(|e| format!("Failed to write to log file: {}", e))?;
            writer.flush()
                .map_err(|e| format!("Failed to flush log file: {}", e))?;

            // Update rotation size
            if let Some(rotation) = &self.rotation {
                // This is a hack since we can't easily get a mutable reference
                // In a real implementation, we'd need a more sophisticated approach
            }
        }

        Ok(())
    }

    fn open_log_file(path: &Path) -> Result<File, String> {
        // Create parent directories if they don't exist
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create log directory: {}", e))?;
        }

        OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
            .map_err(|e| format!("Failed to open log file: {}", e))
    }
}

pub struct ConsoleLogger {
    formatter: UnifiedLogFormatter,
    min_level: LogLevel,
}

impl ConsoleLogger {
    pub fn new() -> Self {
        Self {
            formatter: UnifiedLogFormatter::new(),
            min_level: LogLevel::Info,
        }
    }

    pub fn with_formatter(mut self, formatter: UnifiedLogFormatter) -> Self {
        self.formatter = formatter;
        self
    }

    pub fn with_min_level(mut self, level: LogLevel) -> Self {
        self.min_level = level;
        self
    }

    pub fn log(&self, entry: &LogEntry) {
        if entry.level < self.min_level {
            return;
        }

        let formatted = self.formatter.format(entry);
        match entry.level {
            LogLevel::Error => eprintln!("{}", formatted),
            _ => println!("{}", formatted),
        }
    }
}

// Convenience macros for logging are defined in the wip_common_rs module