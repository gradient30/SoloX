#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct Counters {
    pub accepted_packets: u64,
    pub dropped_packets: u64,
    pub overflow_drops: u64,
    pub shaped_bytes: u64,
}
