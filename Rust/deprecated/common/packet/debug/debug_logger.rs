use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};
use crate::common::utils::log_config::{LogEntry, LogLevel, UnifiedLogFormatter};
use crate::wip_common_rs::packet::core::PacketFormat;

#[derive(Debug, Clone)]
pub struct PacketDebugInfo {
    pub packet_id: u16,
    pub packet_type: String,
    pub direction: PacketDirection,
    pub timestamp: u64,
    pub size: usize,
    pub checksum: Option<u16>,
    pub fields: HashMap<String, String>,
    pub raw_data: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum PacketDirection {
    Outbound,
    Inbound,
}

impl PacketDirection {
    pub fn as_str(&self) -> &'static str {
        match self {
            PacketDirection::Outbound => "OUT",
            PacketDirection::Inbound => "IN",
        }
    }
}

pub struct PacketDebugLogger {
    inner: Arc<Mutex<PacketDebugLoggerInner>>,
}

struct PacketDebugLoggerInner {
    entries: Vec<PacketDebugInfo>,
    max_entries: usize,
    formatter: UnifiedLogFormatter,
    enabled: bool,
    filter_levels: Vec<LogLevel>,
}

impl PacketDebugLogger {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(Mutex::new(PacketDebugLoggerInner {
                entries: Vec::new(),
                max_entries: 1000,
                formatter: UnifiedLogFormatter::new()
                    .with_timestamps(true)
                    .with_colors(true),
                enabled: true,
                filter_levels: vec![LogLevel::Debug, LogLevel::Info, LogLevel::Warn, LogLevel::Error],
            })),
        }
    }

    pub fn with_max_entries(self, max_entries: usize) -> Self {
        if let Ok(mut inner) = self.inner.lock() {
            inner.max_entries = max_entries;
        }
        self
    }

    pub fn with_formatter(self, formatter: UnifiedLogFormatter) -> Self {
        if let Ok(mut inner) = self.inner.lock() {
            inner.formatter = formatter;
        }
        self
    }

    pub fn set_enabled(&self, enabled: bool) {
        if let Ok(mut inner) = self.inner.lock() {
            inner.enabled = enabled;
        }
    }

    pub fn set_filter_levels(&self, levels: Vec<LogLevel>) {
        if let Ok(mut inner) = self.inner.lock() {
            inner.filter_levels = levels;
        }
    }

    pub fn log_packet<P: PacketFormat>(&self, packet: &P, direction: PacketDirection) {
        if let Ok(mut inner) = self.inner.lock() {
            if !inner.enabled {
                return;
            }

            let packet_bytes = packet.to_bytes();
            let mut fields = HashMap::new();
            
            // Extract common packet information
            let packet_id = packet.packet_id();
            fields.insert("packet_id".to_string(), packet_id.to_string());
            
            // Add packet-specific fields (this would be implemented by each packet type)
            // For now, we'll add some basic information
            fields.insert("size".to_string(), packet_bytes.len().to_string());
            
            let debug_info = PacketDebugInfo {
                packet_id: packet.packet_id(),
                packet_type: std::any::type_name::<P>().to_string(),
                direction,
                timestamp: SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_millis() as u64,
                size: packet_bytes.len(),
                checksum: None, // packet.verify_checksum().ok() doesn't return checksum value
                fields,
                raw_data: packet_bytes,
            };

            // Add to entries and maintain max size
            inner.entries.push(debug_info.clone());
            if inner.entries.len() > inner.max_entries {
                inner.entries.remove(0);
            }

            // Log to console if debug level is enabled
            if inner.filter_levels.contains(&LogLevel::Debug) {
                self.log_packet_details(&inner, &debug_info);
            }
        }
    }

    pub fn log_packet_raw(&self, data: &[u8], direction: PacketDirection, packet_type: &str) {
        if let Ok(mut inner) = self.inner.lock() {
            if !inner.enabled {
                return;
            }

            let debug_info = PacketDebugInfo {
                packet_id: if data.len() >= 2 { 
                    u16::from_le_bytes([data[0], data[1]]) 
                } else { 
                    0 
                },
                packet_type: packet_type.to_string(),
                direction,
                timestamp: SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_millis() as u64,
                size: data.len(),
                checksum: None,
                fields: HashMap::new(),
                raw_data: data.to_vec(),
            };

            inner.entries.push(debug_info.clone());
            if inner.entries.len() > inner.max_entries {
                inner.entries.remove(0);
            }

            if inner.filter_levels.contains(&LogLevel::Debug) {
                self.log_packet_details(&inner, &debug_info);
            }
        }
    }

    pub fn get_packet_history(&self) -> Vec<PacketDebugInfo> {
        if let Ok(inner) = self.inner.lock() {
            inner.entries.clone()
        } else {
            Vec::new()
        }
    }

    pub fn get_packets_by_type(&self, packet_type: &str) -> Vec<PacketDebugInfo> {
        if let Ok(inner) = self.inner.lock() {
            inner.entries.iter()
                .filter(|entry| entry.packet_type == packet_type)
                .cloned()
                .collect()
        } else {
            Vec::new()
        }
    }

    pub fn get_packets_by_direction(&self, direction: PacketDirection) -> Vec<PacketDebugInfo> {
        if let Ok(inner) = self.inner.lock() {
            inner.entries.iter()
                .filter(|entry| entry.direction == direction)
                .cloned()
                .collect()
        } else {
            Vec::new()
        }
    }

    pub fn clear_history(&self) {
        if let Ok(mut inner) = self.inner.lock() {
            inner.entries.clear();
        }
    }

    pub fn dump_packet_details(&self, packet_info: &PacketDebugInfo) -> String {
        let mut output = Vec::new();
        
        output.push(format!("=== Packet Debug Info ==="));
        output.push(format!("Type: {}", packet_info.packet_type));
        output.push(format!("Direction: {}", packet_info.direction.as_str()));
        output.push(format!("ID: {}", packet_info.packet_id));
        output.push(format!("Size: {} bytes", packet_info.size));
        output.push(format!("Timestamp: {}", packet_info.timestamp));
        
        if let Some(checksum) = packet_info.checksum {
            output.push(format!("Checksum: 0x{:04X}", checksum));
        }

        if !packet_info.fields.is_empty() {
            output.push(format!("Fields:"));
            for (key, value) in &packet_info.fields {
                output.push(format!("  {}: {}", key, value));
            }
        }

        output.push(format!("Raw Data ({} bytes):", packet_info.raw_data.len()));
        output.push(self.format_hex_dump(&packet_info.raw_data));
        output.push(format!("========================"));

        output.join("\n")
    }

    pub fn format_communication_flow(&self, start_time: Option<u64>, end_time: Option<u64>) -> String {
        let entries = if let Ok(inner) = self.inner.lock() {
            inner.entries.clone()
        } else {
            return "Failed to access packet history".to_string();
        };

        let filtered_entries: Vec<_> = entries.iter()
            .filter(|entry| {
                if let Some(start) = start_time {
                    if entry.timestamp < start {
                        return false;
                    }
                }
                if let Some(end) = end_time {
                    if entry.timestamp > end {
                        return false;
                    }
                }
                true
            })
            .collect();

        let mut output = Vec::new();
        output.push(format!("=== Communication Flow ==="));
        output.push(format!("Total packets: {}", filtered_entries.len()));
        output.push(format!(""));

        for entry in filtered_entries {
            let direction_arrow = match entry.direction {
                PacketDirection::Outbound => "-->",
                PacketDirection::Inbound => "<--",
            };
            
            output.push(format!(
                "[{}] {} {} ID:{} Size:{} Type:{}",
                entry.timestamp,
                direction_arrow,
                entry.direction.as_str(),
                entry.packet_id,
                entry.size,
                entry.packet_type.split("::").last().unwrap_or(&entry.packet_type)
            ));
        }

        output.push(format!("==========================="));
        output.join("\n")
    }

    fn log_packet_details(&self, inner: &PacketDebugLoggerInner, packet_info: &PacketDebugInfo) {
        let log_entry = LogEntry::new(
            LogLevel::Debug,
            "packet_debug",
            &format!(
                "Packet {} ID:{} Size:{} Type:{}",
                packet_info.direction.as_str(),
                packet_info.packet_id,
                packet_info.size,
                packet_info.packet_type.split("::").last().unwrap_or(&packet_info.packet_type)
            )
        );
        
        let formatted = inner.formatter.format(&log_entry);
        println!("{}", formatted);
        
        // If trace level is enabled, also show hex dump
        if inner.filter_levels.contains(&LogLevel::Trace) {
            println!("{}", self.format_hex_dump(&packet_info.raw_data));
        }
    }

    fn format_hex_dump(&self, data: &[u8]) -> String {
        let mut lines = Vec::new();
        
        for (i, chunk) in data.chunks(16).enumerate() {
            let mut hex_part = String::new();
            let mut ascii_part = String::new();
            
            for (j, byte) in chunk.iter().enumerate() {
                hex_part.push_str(&format!("{:02X} ", byte));
                
                let c = if byte.is_ascii_graphic() || *byte == b' ' {
                    *byte as char
                } else {
                    '.'
                };
                ascii_part.push(c);
                
                if j == 7 {
                    hex_part.push(' ');
                }
            }
            
            // Pad hex part to align ASCII
            while hex_part.len() < 50 {
                hex_part.push(' ');
            }
            
            lines.push(format!("{:08X}  {}  |{}|", i * 16, hex_part, ascii_part));
        }
        
        lines.join("\n")
    }

    pub fn get_statistics(&self) -> PacketDebugStats {
        if let Ok(inner) = self.inner.lock() {
            let mut stats = PacketDebugStats::new();
            
            for entry in &inner.entries {
                stats.total_packets += 1;
                stats.total_bytes += entry.size;
                
                match entry.direction {
                    PacketDirection::Outbound => stats.outbound_packets += 1,
                    PacketDirection::Inbound => stats.inbound_packets += 1,
                }
                
                *stats.packet_types.entry(entry.packet_type.clone()).or_insert(0) += 1;
            }
            
            stats
        } else {
            PacketDebugStats::new()
        }
    }
}

#[derive(Debug, Clone)]
pub struct PacketDebugStats {
    pub total_packets: usize,
    pub total_bytes: usize,
    pub outbound_packets: usize,
    pub inbound_packets: usize,
    pub packet_types: HashMap<String, usize>,
}

impl PacketDebugStats {
    pub fn new() -> Self {
        Self {
            total_packets: 0,
            total_bytes: 0,
            outbound_packets: 0,
            inbound_packets: 0,
            packet_types: HashMap::new(),
        }
    }
}