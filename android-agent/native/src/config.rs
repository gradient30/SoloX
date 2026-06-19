#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Direction {
    Uplink,
    Downlink,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Protocol {
    Tcp,
    Udp,
    Other(u8),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PacketMeta {
    pub ip_version: u8,
    pub protocol: Protocol,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct DirectionConfig {
    pub delay_ms: u64,
    pub jitter_ms: u64,
    pub loss_pct: f64,
    pub bandwidth_kbps: Option<u64>,
    pub max_queue_packets: usize,
}

impl Default for DirectionConfig {
    fn default() -> Self {
        Self {
            delay_ms: 0,
            jitter_ms: 0,
            loss_pct: 0.0,
            bandwidth_kbps: None,
            max_queue_packets: 1024,
        }
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Profile {
    pub uplink: DirectionConfig,
    pub downlink: DirectionConfig,
}
