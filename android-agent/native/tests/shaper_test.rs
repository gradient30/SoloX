use solox_network_agent_native::{
    classify_packet, Direction, DirectionConfig, PacketMeta, PacketShaper, Profile, Protocol,
    ShapeOutcome,
};

fn packet(len: usize) -> Vec<u8> {
    vec![0u8; len]
}

#[test]
fn zero_profile_is_pass_through() {
    let mut shaper = PacketShaper::new(Profile::default(), 7);
    assert_eq!(
        shaper.enqueue(Direction::Uplink, packet(128), 100),
        ShapeOutcome::Queued { release_at_ms: 100 }
    );
    assert_eq!(shaper.poll_ready(Direction::Uplink, 100), vec![packet(128)]);
    assert_eq!(shaper.counters().accepted_packets, 1);
}

#[test]
fn uplink_and_downlink_profiles_are_independent() {
    let profile = Profile {
        uplink: DirectionConfig {
            delay_ms: 100,
            ..DirectionConfig::default()
        },
        downlink: DirectionConfig {
            delay_ms: 300,
            ..DirectionConfig::default()
        },
    };
    let mut shaper = PacketShaper::new(profile, 7);
    assert_eq!(
        shaper.enqueue(Direction::Uplink, packet(64), 0),
        ShapeOutcome::Queued { release_at_ms: 100 }
    );
    assert_eq!(
        shaper.enqueue(Direction::Downlink, packet(64), 0),
        ShapeOutcome::Queued { release_at_ms: 300 }
    );
    assert_eq!(shaper.poll_ready(Direction::Uplink, 99).len(), 0);
    assert_eq!(shaper.poll_ready(Direction::Uplink, 100).len(), 1);
    assert_eq!(shaper.poll_ready(Direction::Downlink, 299).len(), 0);
    assert_eq!(shaper.poll_ready(Direction::Downlink, 300).len(), 1);
}

#[test]
fn selected_loss_consumes_packet_without_forwarding() {
    let profile = Profile {
        uplink: DirectionConfig {
            loss_pct: 100.0,
            ..DirectionConfig::default()
        },
        ..Profile::default()
    };
    let mut shaper = PacketShaper::new(profile, 1);
    assert_eq!(
        shaper.enqueue(Direction::Uplink, packet(64), 0),
        ShapeOutcome::DroppedByLoss
    );
    assert_eq!(shaper.poll_ready(Direction::Uplink, 10).len(), 0);
    assert_eq!(shaper.counters().dropped_packets, 1);
}

#[test]
fn fixed_delay_never_releases_early() {
    let profile = Profile {
        uplink: DirectionConfig {
            delay_ms: 250,
            ..DirectionConfig::default()
        },
        ..Profile::default()
    };
    let mut shaper = PacketShaper::new(profile, 1);
    shaper.enqueue(Direction::Uplink, packet(32), 10);
    assert_eq!(shaper.poll_ready(Direction::Uplink, 259).len(), 0);
    assert_eq!(shaper.poll_ready(Direction::Uplink, 260).len(), 1);
}

#[test]
fn jitter_is_bounded() {
    let profile = Profile {
        uplink: DirectionConfig {
            delay_ms: 10,
            jitter_ms: 40,
            ..DirectionConfig::default()
        },
        ..Profile::default()
    };
    let mut shaper = PacketShaper::new(profile, 123);
    for _ in 0..20 {
        match shaper.enqueue(Direction::Uplink, packet(1), 1000) {
            ShapeOutcome::Queued { release_at_ms } => {
                assert!((1010..=1050).contains(&release_at_ms))
            }
            other => panic!("unexpected outcome: {other:?}"),
        }
    }
}

#[test]
fn token_bucket_bandwidth_converges_within_ten_percent() {
    let profile = Profile {
        uplink: DirectionConfig {
            bandwidth_kbps: Some(1000),
            ..DirectionConfig::default()
        },
        ..Profile::default()
    };
    let mut shaper = PacketShaper::new(profile, 1);
    let mut last_release = 0;
    for _ in 0..100 {
        if let ShapeOutcome::Queued { release_at_ms } =
            shaper.enqueue(Direction::Uplink, packet(1000), 0)
        {
            last_release = release_at_ms;
        }
    }
    assert!(
        (720..=880).contains(&last_release),
        "last release was {last_release}ms"
    );
}

#[test]
fn queue_memory_has_fixed_maximum_and_reports_overflow() {
    let profile = Profile {
        uplink: DirectionConfig {
            delay_ms: 10,
            max_queue_packets: 1,
            ..DirectionConfig::default()
        },
        ..Profile::default()
    };
    let mut shaper = PacketShaper::new(profile, 1);
    assert!(matches!(
        shaper.enqueue(Direction::Uplink, packet(8), 0),
        ShapeOutcome::Queued { .. }
    ));
    assert_eq!(
        shaper.enqueue(Direction::Uplink, packet(8), 0),
        ShapeOutcome::DroppedByOverflow
    );
    assert_eq!(shaper.counters().overflow_drops, 1);
}

#[test]
fn packet_metadata_classifies_ipv4_and_ipv6_without_payload() {
    let mut ipv4 = vec![
        0x45, 0, 0, 20, 0, 0, 0, 0, 64, 17, 0, 0, 1, 1, 1, 1, 8, 8, 8, 8,
    ];
    ipv4.extend_from_slice(b"payload-is-ignored");
    assert_eq!(
        classify_packet(&ipv4),
        Some(PacketMeta {
            ip_version: 4,
            protocol: Protocol::Udp
        })
    );

    let mut ipv6 = vec![0x60, 0, 0, 0, 0, 0, 6, 64];
    ipv6.extend_from_slice(&[0u8; 32]);
    ipv6.extend_from_slice(b"payload-is-ignored");
    assert_eq!(
        classify_packet(&ipv6),
        Some(PacketMeta {
            ip_version: 6,
            protocol: Protocol::Tcp
        })
    );
}
