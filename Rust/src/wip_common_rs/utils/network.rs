use std::net::{SocketAddr, IpAddr, Ipv4Addr, ToSocketAddrs};
use std::time::{Duration, Instant};
use std::collections::HashMap;
use tokio::net::{UdpSocket, TcpSocket};
use tokio::time::timeout;

#[derive(Debug, Clone)]
pub struct NetworkStats {
    pub packets_sent: u64,
    pub packets_received: u64,
    pub bytes_sent: u64,
    pub bytes_received: u64,
    pub connection_attempts: u64,
    pub connection_failures: u64,
    pub avg_response_time: Duration,
    pub last_activity: Option<Instant>,
}
impl NetworkStats { pub fn new()->Self{ Self{ packets_sent:0, packets_received:0, bytes_sent:0, bytes_received:0, connection_attempts:0, connection_failures:0, avg_response_time:Duration::ZERO, last_activity:None } } pub fn record_sent(&mut self, bytes:usize){ self.packets_sent+=1; self.bytes_sent+=bytes as u64; self.last_activity=Some(Instant::now()); } pub fn record_received(&mut self, bytes:usize){ self.packets_received+=1; self.bytes_received+=bytes as u64; self.last_activity=Some(Instant::now()); } pub fn record_connection_attempt(&mut self){ self.connection_attempts+=1; } pub fn record_connection_failure(&mut self){ self.connection_failures+=1; } pub fn update_response_time(&mut self, rt:Duration){ if self.avg_response_time==Duration::ZERO { self.avg_response_time=rt; } else { let c=self.avg_response_time.as_millis() as u64; let n=rt.as_millis() as u64; self.avg_response_time=Duration::from_millis((c+n)/2); } } }

pub struct NetworkDiagnostics { stats: HashMap<String, NetworkStats> }
impl NetworkDiagnostics { pub fn new()->Self{ Self{ stats:HashMap::new() } } pub fn get_stats(&self, host:&str)->Option<&NetworkStats>{ self.stats.get(host) } pub fn get_stats_mut(&mut self, host:&str)->&mut NetworkStats{ self.stats.entry(host.to_string()).or_insert_with(NetworkStats::new) }
    pub async fn ping_host(&mut self, host:&str, port:u16, timeout_duration:Duration)->Result<Duration,String>{ let start=Instant::now(); let stats=self.get_stats_mut(host); stats.record_connection_attempt(); let addr=format!("{}:{}", host, port); let socket_addr:SocketAddr = addr.parse().map_err(|e| format!("Invalid address {}: {}", addr, e))?; let socket = TcpSocket::new_v4().map_err(|e| { stats.record_connection_failure(); format!("Failed to create socket: {}", e) })?; match timeout(timeout_duration, socket.connect(socket_addr)).await { Ok(Ok(_)) => { let rt=start.elapsed(); stats.update_response_time(rt); Ok(rt) } Ok(Err(e)) => { stats.record_connection_failure(); Err(format!("Connection failed: {}", e)) } Err(_) => { stats.record_connection_failure(); Err("Connection timeout".into()) } } }
    pub async fn test_udp_connectivity(&mut self, host:&str, port:u16, test_data:&[u8])->Result<Duration,String>{ let start=Instant::now(); let stats=self.get_stats_mut(host); stats.record_connection_attempt(); let socket = UdpSocket::bind("0.0.0.0:0").await.map_err(|e| format!("Failed to bind UDP socket: {}", e))?; let addr=format!("{}:{}", host, port); let target:SocketAddr = addr.parse().map_err(|e| format!("Invalid address {}: {}", addr, e))?; match socket.send_to(test_data, target).await { Ok(bytes_sent)=>{ stats.record_sent(bytes_sent); let mut buf=[0u8;1024]; match timeout(Duration::from_secs(5), socket.recv_from(&mut buf)).await { Ok(Ok((bytes_received,_)))=>{ let rt=start.elapsed(); stats.record_received(bytes_received); stats.update_response_time(rt); Ok(rt) } Ok(Err(e))=>{ stats.record_connection_failure(); Err(format!("UDP receive failed: {}", e)) } Err(_)=>{ stats.record_connection_failure(); Err("UDP receive timeout".into()) } } } Err(e)=>{ stats.record_connection_failure(); Err(format!("UDP send failed: {}", e)) } } }
    pub fn get_all_stats(&self)->&HashMap<String, NetworkStats>{ &self.stats } pub fn reset_stats(&mut self, host:Option<&str>){ match host { Some(h)=>{ self.stats.remove(h); } None => { self.stats.clear(); } } } }

pub async fn resolve_ipv4(hostname:&str)->Result<Ipv4Addr,String>{ let addresses:Vec<SocketAddr> = format!("{}:80", hostname).to_socket_addrs().map_err(|e| format!("Failed to resolve hostname {}: {}", hostname, e))?.collect(); for addr in addresses { if let IpAddr::V4(ipv4) = addr.ip(){ return Ok(ipv4); } } Err(format!("No IPv4 address found for hostname: {}", hostname)) }
pub async fn check_network_connectivity(hosts:&[(&str,u16)])->HashMap<String,bool>{ let mut results=HashMap::new(); let mut diag=NetworkDiagnostics::new(); for &(h,p) in hosts { let ok = diag.ping_host(h,p, Duration::from_secs(5)).await.is_ok(); results.insert(format!("{}:{}", h, p), ok); } results }
pub fn get_local_ip()->Result<Ipv4Addr,String>{ use std::net::UdpSocket; let socket = UdpSocket::bind("0.0.0.0:0").map_err(|e| format!("Failed to bind socket: {}", e))?; socket.connect("8.8.8.8:80").map_err(|e| format!("Failed to connect to test address: {}", e))?; let local_addr=socket.local_addr().map_err(|e| format!("Failed to get local address: {}", e))?; if let IpAddr::V4(ipv4)=local_addr.ip(){ Ok(ipv4) } else { Err("Not an IPv4 address".into()) } }

