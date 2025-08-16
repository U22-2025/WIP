use std::fs::{File, OpenOptions};
use std::io::{Write, BufWriter};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Local};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum LogLevel { Trace=0, Debug=1, Info=2, Warn=3, Error=4 }
impl LogLevel {
    pub fn from_str(s: &str) -> Result<Self, String> { match s.to_lowercase().as_str(){"trace"=>Ok(LogLevel::Trace),"debug"=>Ok(LogLevel::Debug),"info"=>Ok(LogLevel::Info),"warn"=>Ok(LogLevel::Warn),"error"=>Ok(LogLevel::Error),_=>Err(format!("Invalid log level: {}", s))} }
    pub fn as_str(&self)->&'static str{match self{LogLevel::Trace=>"TRACE",LogLevel::Debug=>"DEBUG",LogLevel::Info=>"INFO",LogLevel::Warn=>"WARN",LogLevel::Error=>"ERROR"}}
}

#[derive(Debug, Clone)]
pub struct LogEntry { pub timestamp: DateTime<Local>, pub level: LogLevel, pub module: String, pub message: String, pub file: Option<String>, pub line: Option<u32> }
impl LogEntry { pub fn new(level: LogLevel, module: &str, message: &str)->Self{ Self{ timestamp: Local::now(), level, module: module.into(), message: message.into(), file: None, line: None } } pub fn with_location(mut self, file:&str, line:u32)->Self{ self.file=Some(file.into()); self.line=Some(line); self } }

pub struct UnifiedLogFormatter { include_timestamps: bool, include_location: bool, color_enabled: bool }
impl UnifiedLogFormatter {
    pub fn new()->Self{ Self{ include_timestamps:true, include_location:true, color_enabled:true } }
    pub fn with_timestamps(mut self, en:bool)->Self{ self.include_timestamps=en; self }
    pub fn with_location(mut self, en:bool)->Self{ self.include_location=en; self }
    pub fn with_colors(mut self, en:bool)->Self{ self.color_enabled=en; self }
    pub fn format(&self, entry: &LogEntry)->String{
        let mut parts=Vec::new();
        if self.include_timestamps { parts.push(format!("[{}]", entry.timestamp.format("%Y-%m-%d %H:%M:%S%.3f"))); }
        let level_str = if self.color_enabled { match entry.level { LogLevel::Trace=>format!("\x1b[37m{}\x1b[0m", entry.level.as_str()), LogLevel::Debug=>format!("\x1b[36m{}\x1b[0m", entry.level.as_str()), LogLevel::Info=>format!("\x1b[32m{}\x1b[0m", entry.level.as_str()), LogLevel::Warn=>format!("\x1b[33m{}\x1b[0m", entry.level.as_str()), LogLevel::Error=>format!("\x1b[31m{}\x1b[0m", entry.level.as_str()) } } else { entry.level.as_str().to_string() };
        parts.push(format!("[{}]", level_str));
        parts.push(format!("[{}]", entry.module));
        if self.include_location { if let (Some(f), Some(l)) = (&entry.file, entry.line) { parts.push(format!("[{}:{}]", f,l)); } }
        parts.push(entry.message.clone());
        parts.join(" ")
    }
}

pub struct LogRotation { max_file_size: u64, max_files: usize, current_size: u64 }
impl LogRotation { pub fn new(max_file_size:u64, max_files:usize)->Self{ Self{max_file_size,max_files,current_size:0} } pub fn should_rotate(&self)->bool{ self.current_size>=self.max_file_size } pub fn add_bytes(&mut self, b:u64){ self.current_size+=b } pub fn reset(&mut self){ self.current_size=0 } pub fn rotate_files(&self, base: &Path)->Result<(),String>{ for i in (1..self.max_files).rev(){ let from=self.get_rotated_path(base, i-1); let to=self.get_rotated_path(base, i); if from.exists(){ std::fs::rename(&from,&to).map_err(|e| format!("Failed to rotate log file: {}", e))?; } } if base.exists(){ let rotated=self.get_rotated_path(base,0); std::fs::rename(base,&rotated).map_err(|e| format!("Failed to rotate current log file: {}", e))?; } Ok(()) } fn get_rotated_path(&self, base:&Path, idx:usize)->PathBuf{ if let Some(parent)=base.parent(){ if let Some(stem)=base.file_stem(){ if let Some(ext)=base.extension(){ return parent.join(format!("{}.{}.{}", stem.to_string_lossy(), idx, ext.to_string_lossy())); } else { return parent.join(format!("{}.{}", stem.to_string_lossy(), idx)); } } } base.with_extension(format!("{}", idx)) } }

pub struct FileLogger { file: Arc<Mutex<Option<BufWriter<File>>>>, path: PathBuf, formatter: UnifiedLogFormatter, rotation: Option<LogRotation>, min_level: LogLevel }
impl FileLogger {
    pub fn new<P: AsRef<Path>>(path:P)->Result<Self,String>{ let path=path.as_ref().to_path_buf(); let file=Self::open_log_file(&path)?; Ok(Self{ file:Arc::new(Mutex::new(Some(BufWriter::new(file)))), path, formatter:UnifiedLogFormatter::new().with_colors(false), rotation:None, min_level:LogLevel::Info }) }
    pub fn with_rotation(mut self, max_size:u64, max_files:usize)->Self{ self.rotation=Some(LogRotation::new(max_size,max_files)); self }
    pub fn with_formatter(mut self, f:UnifiedLogFormatter)->Self{ self.formatter=f; self }
    pub fn with_min_level(mut self, lvl:LogLevel)->Self{ self.min_level=lvl; self }
    pub fn log(&self, entry:&LogEntry)->Result<(),String>{ if entry.level < self.min_level { return Ok(());} let formatted=self.formatter.format(entry); let line=format!("{}\n", formatted); let mut file_guard=self.file.lock().unwrap(); if let Some(rot) = &self.rotation { if rot.should_rotate(){ if let Some(writer)=file_guard.take(){ drop(writer);} rot.rotate_files(&self.path).map_err(|e| format!("Log rotation failed: {}", e))?; let new_file=Self::open_log_file(&self.path)?; *file_guard=Some(BufWriter::new(new_file)); } }
        if let Some(writer)=file_guard.as_mut(){ writer.write_all(line.as_bytes()).map_err(|e| format!("Failed to write to log file: {}", e))?; writer.flush().map_err(|e| format!("Failed to flush log file: {}", e))?; }
        Ok(()) }
    fn open_log_file(path:&Path)->Result<File,String>{ if let Some(parent)=path.parent(){ std::fs::create_dir_all(parent).map_err(|e| format!("Failed to create log directory: {}", e))?; } OpenOptions::new().create(true).append(true).open(path).map_err(|e| format!("Failed to open log file: {}", e)) }
}

pub struct ConsoleLogger { formatter: UnifiedLogFormatter, min_level: LogLevel }
impl ConsoleLogger { pub fn new()->Self{ Self{ formatter:UnifiedLogFormatter::new(), min_level:LogLevel::Info } } pub fn with_formatter(mut self, f:UnifiedLogFormatter)->Self{ self.formatter=f; self } pub fn with_min_level(mut self, l:LogLevel)->Self{ self.min_level=l; self } pub fn log(&self, entry:&LogEntry){ if entry.level < self.min_level { return; } let formatted=self.formatter.format(entry); match entry.level { LogLevel::Error => eprintln!("{}", formatted), _ => println!("{}", formatted), } } }

#[macro_export]
macro_rules! log_trace { ($logger:expr, $module:expr, $($arg:tt)*) => { $logger.log(&crate::wip_common_rs::utils::log_config::LogEntry::new(crate::wip_common_rs::utils::log_config::LogLevel::Trace, $module, &format!($($arg)*)).with_location(file!(), line!())) } } 
#[macro_export]
macro_rules! log_debug { ($logger:expr, $module:expr, $($arg:tt)*) => { $logger.log(&crate::wip_common_rs::utils::log_config::LogEntry::new(crate::wip_common_rs::utils::log_config::LogLevel::Debug, $module, &format!($($arg)*)).with_location(file!(), line!())) } }
#[macro_export]
macro_rules! log_info { ($logger:expr, $module:expr, $($arg:tt)*) => { $logger.log(&crate::wip_common_rs::utils::log_config::LogEntry::new(crate::wip_common_rs::utils::log_config::LogLevel::Info, $module, &format!($($arg)*)).with_location(file!(), line!())) } }
#[macro_export]
macro_rules! log_warn { ($logger:expr, $module:expr, $($arg:tt)*) => { $logger.log(&crate::wip_common_rs::utils::log_config::LogEntry::new(crate::wip_common_rs::utils::log_config::LogLevel::Warn, $module, &format!($($arg)*)).with_location(file!(), line!())) } }
#[macro_export]
macro_rules! log_error { ($logger:expr, $module:expr, $($arg:tt)*) => { $logger.log(&crate::wip_common_rs::utils::log_config::LogEntry::new(crate::wip_common_rs::utils::log_config::LogLevel::Error, $module, &format!($($arg)*)).with_location(file!(), line!())) } }

