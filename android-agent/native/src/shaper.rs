use std::collections::VecDeque;

use crate::config::{Direction, DirectionConfig, PacketMeta, Profile, Protocol};
use crate::counters::Counters;

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ShapeOutcome {
    Queued { release_at_ms: u64 },
    DroppedByLoss,
    DroppedByOverflow,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct QueuedPacket {
    release_at_ms: u64,
    bytes: Vec<u8>,
}

#[derive(Clone, Debug)]
pub struct PacketShaper {
    profile: Profile,
    rng: DeterministicRng,
    uplink: VecDeque<QueuedPacket>,
    downlink: VecDeque<QueuedPacket>,
    uplink_next_release_ms: u64,
    downlink_next_release_ms: u64,
    counters: Counters,
}

impl PacketShaper {
    pub fn new(profile: Profile, seed: u64) -> Self {
        validate_config(profile.uplink);
        validate_config(profile.downlink);
        Self {
            profile,
            rng: DeterministicRng::new(seed),
            uplink: VecDeque::new(),
            downlink: VecDeque::new(),
            uplink_next_release_ms: 0,
            downlink_next_release_ms: 0,
            counters: Counters::default(),
        }
    }

    pub fn enqueue(&mut self, direction: Direction, bytes: Vec<u8>, now_ms: u64) -> ShapeOutcome {
        let config = self.config(direction);
        let queue_len = self.queue(direction).len();
        if queue_len >= config.max_queue_packets {
            self.counters.overflow_drops += 1;
            self.counters.dropped_packets += 1;
            return ShapeOutcome::DroppedByOverflow;
        }
        if self.should_drop(config.loss_pct) {
            self.counters.dropped_packets += 1;
            return ShapeOutcome::DroppedByLoss;
        }

        let release_at_ms = self.release_time(direction, config, bytes.len(), now_ms);
        self.queue_mut(direction).push_back(QueuedPacket {
            release_at_ms,
            bytes,
        });
        self.counters.accepted_packets += 1;
        self.counters.shaped_bytes += self
            .queue(direction)
            .back()
            .map_or(0, |p| p.bytes.len() as u64);
        ShapeOutcome::Queued { release_at_ms }
    }

    pub fn poll_ready(&mut self, direction: Direction, now_ms: u64) -> Vec<Vec<u8>> {
        let queue = self.queue_mut(direction);
        let mut ready = Vec::new();
        while queue
            .front()
            .is_some_and(|packet| packet.release_at_ms <= now_ms)
        {
            if let Some(packet) = queue.pop_front() {
                ready.push(packet.bytes);
            }
        }
        ready
    }

    pub fn counters(&self) -> Counters {
        self.counters
    }

    fn config(&self, direction: Direction) -> DirectionConfig {
        match direction {
            Direction::Uplink => self.profile.uplink,
            Direction::Downlink => self.profile.downlink,
        }
    }

    fn queue(&self, direction: Direction) -> &VecDeque<QueuedPacket> {
        match direction {
            Direction::Uplink => &self.uplink,
            Direction::Downlink => &self.downlink,
        }
    }

    fn queue_mut(&mut self, direction: Direction) -> &mut VecDeque<QueuedPacket> {
        match direction {
            Direction::Uplink => &mut self.uplink,
            Direction::Downlink => &mut self.downlink,
        }
    }

    fn next_release_mut(&mut self, direction: Direction) -> &mut u64 {
        match direction {
            Direction::Uplink => &mut self.uplink_next_release_ms,
            Direction::Downlink => &mut self.downlink_next_release_ms,
        }
    }

    fn should_drop(&mut self, loss_pct: f64) -> bool {
        if loss_pct <= 0.0 {
            return false;
        }
        if loss_pct >= 100.0 {
            return true;
        }
        self.rng.next_unit() * 100.0 < loss_pct
    }

    fn release_time(
        &mut self,
        direction: Direction,
        config: DirectionConfig,
        packet_len: usize,
        now_ms: u64,
    ) -> u64 {
        let jitter_ms = if config.jitter_ms == 0 {
            0
        } else {
            self.rng.next_bounded(config.jitter_ms + 1)
        };
        let base = now_ms + config.delay_ms + jitter_ms;
        let Some(kbps) = config.bandwidth_kbps else {
            return base;
        };
        if kbps == 0 {
            return base;
        }
        let transmit_ms = (packet_len as u64 * 8 * 1000).div_ceil(kbps * 1000);
        let next = self.next_release_mut(direction);
        let release = base.max(*next) + transmit_ms;
        *next = release;
        release
    }
}

pub fn classify_packet(packet: &[u8]) -> Option<PacketMeta> {
    let first = *packet.first()?;
    match first >> 4 {
        4 if packet.len() >= 20 => Some(PacketMeta {
            ip_version: 4,
            protocol: protocol_from_number(packet[9]),
        }),
        6 if packet.len() >= 40 => Some(PacketMeta {
            ip_version: 6,
            protocol: protocol_from_number(packet[6]),
        }),
        _ => None,
    }
}

fn protocol_from_number(value: u8) -> Protocol {
    match value {
        6 => Protocol::Tcp,
        17 => Protocol::Udp,
        other => Protocol::Other(other),
    }
}

fn validate_config(config: DirectionConfig) {
    assert!(
        (0.0..=100.0).contains(&config.loss_pct),
        "loss_pct must be 0..=100"
    );
    assert!(
        config.max_queue_packets > 0,
        "max_queue_packets must be positive"
    );
}

#[derive(Clone, Debug)]
struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    fn new(seed: u64) -> Self {
        Self { state: seed.max(1) }
    }

    fn next_u64(&mut self) -> u64 {
        self.state = self
            .state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.state
    }

    fn next_unit(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / ((1u64 << 53) as f64)
    }

    fn next_bounded(&mut self, upper_exclusive: u64) -> u64 {
        self.next_u64() % upper_exclusive
    }
}
