use std::collections::HashMap;
use std::os::raw::c_void;
use std::sync::{Mutex, OnceLock};
use std::thread::JoinHandle;

#[cfg(unix)]
use std::net::SocketAddr;
#[cfg(unix)]
use std::sync::atomic::{AtomicI64, Ordering};
#[cfg(unix)]
use std::thread;
#[cfg(unix)]
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use clap::Parser;
#[cfg(unix)]
use tokio::io::{AsyncRead, AsyncReadExt, AsyncWrite, AsyncWriteExt};
#[cfg(unix)]
use tokio_util::sync::CancellationToken;

#[cfg(unix)]
use crate::config::{Direction, DirectionConfig, Profile};
#[cfg(not(unix))]
use crate::config::{DirectionConfig, Profile};
#[cfg(unix)]
use crate::shaper::{PacketShaper, ShapeOutcome};

pub const TUN2PROXY_SOURCE: &str = "https://github.com/tun2proxy/tun2proxy";
pub const TUN2PROXY_REV: &str = "eed123fbbec06295bf83f9be36d5a0f64ed9a8cb";
pub const TUN_FD_ARG: &str = "--tun-fd";
pub const PROXY_ARG_PREFIX: &str = "--proxy=socks5://";
pub const DNS_ARG: &str = "--dns=over-tcp";
pub const IPV6_ARG: &str = "--ipv6-enabled";
pub const MAX_SESSIONS_ARG: &str = "--max-sessions=256";
pub const CLOSE_FD_ON_DROP_ARG: &str = "--close-fd-on-drop=true";
#[cfg(unix)]
const TUN_MTU: u16 = 1500;
#[cfg(unix)]
const STARTUP_TIMEOUT: Duration = Duration::from_secs(3);
#[cfg(unix)]
const SOCKS_BIND_ADDR: &str = "127.0.0.1:0";
const MAX_QUEUE_PACKETS: usize = 2048;

#[cfg(unix)]
static NEXT_HANDLE: AtomicI64 = AtomicI64::new(1);
static RUNTIMES: OnceLock<Mutex<HashMap<i64, NativeRuntime>>> = OnceLock::new();

struct NativeRuntime {
    #[cfg(unix)]
    cancel: CancellationToken,
    join: Option<JoinHandle<()>>,
}

pub fn direct_runtime_args(tun_fd: i32, ipv6: bool) -> Vec<String> {
    let mut args = vec![
        TUN_FD_ARG.to_string(),
        tun_fd.to_string(),
        format!("{PROXY_ARG_PREFIX}127.0.0.1:1080"),
        DNS_ARG.to_string(),
        MAX_SESSIONS_ARG.to_string(),
        CLOSE_FD_ON_DROP_ARG.to_string(),
    ];
    if ipv6 {
        args.push(IPV6_ARG.to_string());
    }
    args
}

#[no_mangle]
pub extern "system" fn Java_io_solox_networkagent_nativebridge_NativeTunnel_nativeStart(
    _env: *mut c_void,
    _class: *mut c_void,
    _tun_fd: i32,
    ipv6_enabled: u8,
    uplink_delay_ms: i32,
    uplink_jitter_ms: i32,
    uplink_loss_pct: f64,
    uplink_bandwidth_kbps: i32,
    downlink_delay_ms: i32,
    downlink_jitter_ms: i32,
    downlink_loss_pct: f64,
    downlink_bandwidth_kbps: i32,
) -> i64 {
    if _tun_fd < 0 {
        return -10;
    }
    let Some(profile) = native_profile(
        uplink_delay_ms,
        uplink_jitter_ms,
        uplink_loss_pct,
        uplink_bandwidth_kbps,
        downlink_delay_ms,
        downlink_jitter_ms,
        downlink_loss_pct,
        downlink_bandwidth_kbps,
    ) else {
        return -11;
    };
    let Ok(args) = parse_tun2proxy_args(_tun_fd, ipv6_enabled != 0) else {
        return -12;
    };
    start_runtime(_tun_fd, profile, args)
}

#[cfg(not(unix))]
fn start_runtime(_tun_fd: i32, _profile: Profile, _args: tun2proxy::Args) -> i64 {
    0
}

#[cfg(unix)]
fn start_runtime(tun_fd: i32, profile: Profile, args: tun2proxy::Args) -> i64 {
    let handle = NEXT_HANDLE.fetch_add(1, Ordering::Relaxed);
    let cancel = CancellationToken::new();
    let thread_cancel = cancel.clone();
    let (ready_tx, ready_rx) = std::sync::mpsc::sync_channel(1);
    let join = thread::spawn(move || {
        let result = run_native_tunnel(tun_fd, profile, args, thread_cancel, ready_tx);
        if let Err(err) = result {
            eprintln!("SoloX native tunnel stopped: {err}");
        }
    });

    match ready_rx.recv_timeout(STARTUP_TIMEOUT) {
        Ok(Ok(())) => {
            runtimes().lock().unwrap().insert(
                handle,
                NativeRuntime {
                    cancel,
                    join: Some(join),
                },
            );
            handle
        }
        Ok(Err(_)) | Err(_) => {
            cancel.cancel();
            let _ = join.join();
            -13
        }
    }
}

#[no_mangle]
pub extern "system" fn Java_io_solox_networkagent_nativebridge_NativeTunnel_nativeStop(
    _env: *mut c_void,
    _class: *mut c_void,
    _handle: i64,
) {
    let runtime = runtimes().lock().unwrap().remove(&_handle);
    if let Some(mut runtime) = runtime {
        #[cfg(unix)]
        runtime.cancel.cancel();
        if let Some(join) = runtime.join.take() {
            let _ = join.join();
        }
    }
}

fn runtimes() -> &'static Mutex<HashMap<i64, NativeRuntime>> {
    RUNTIMES.get_or_init(|| Mutex::new(HashMap::new()))
}

fn parse_tun2proxy_args(tun_fd: i32, ipv6: bool) -> Result<tun2proxy::Args, clap::Error> {
    let args =
        std::iter::once("tun2proxy-bin".to_string()).chain(direct_runtime_args(tun_fd, ipv6));
    tun2proxy::Args::try_parse_from(args)
}

#[allow(clippy::too_many_arguments)]
fn native_profile(
    uplink_delay_ms: i32,
    uplink_jitter_ms: i32,
    uplink_loss_pct: f64,
    uplink_bandwidth_kbps: i32,
    downlink_delay_ms: i32,
    downlink_jitter_ms: i32,
    downlink_loss_pct: f64,
    downlink_bandwidth_kbps: i32,
) -> Option<Profile> {
    Some(Profile {
        uplink: native_direction(
            uplink_delay_ms,
            uplink_jitter_ms,
            uplink_loss_pct,
            uplink_bandwidth_kbps,
        )?,
        downlink: native_direction(
            downlink_delay_ms,
            downlink_jitter_ms,
            downlink_loss_pct,
            downlink_bandwidth_kbps,
        )?,
    })
}

fn native_direction(
    delay_ms: i32,
    jitter_ms: i32,
    loss_pct: f64,
    bandwidth_kbps: i32,
) -> Option<DirectionConfig> {
    if delay_ms < 0 || jitter_ms < 0 || !(0.0..=100.0).contains(&loss_pct) || bandwidth_kbps < 0 {
        return None;
    }
    Some(DirectionConfig {
        delay_ms: delay_ms as u64,
        jitter_ms: jitter_ms as u64,
        loss_pct,
        bandwidth_kbps: if bandwidth_kbps == 0 {
            None
        } else {
            Some(bandwidth_kbps as u64)
        },
        max_queue_packets: MAX_QUEUE_PACKETS,
    })
}

#[cfg(unix)]
fn run_native_tunnel(
    _tun_fd: i32,
    profile: Profile,
    mut args: tun2proxy::Args,
    shutdown: CancellationToken,
    ready: std::sync::mpsc::SyncSender<Result<(), String>>,
) -> Result<(), String> {
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .map_err(|err| err.to_string())?;
    runtime.block_on(async move {
        let socks = tokio::net::TcpListener::bind(SOCKS_BIND_ADDR)
            .await
            .map_err(|err| err.to_string())?;
        let socks_addr = socks.local_addr().map_err(|err| err.to_string())?;
        args.proxy = tun2proxy::ArgProxy::try_from(format!("socks5://{socks_addr}").as_str())
            .map_err(|err| err.to_string())?;
        let socks_shutdown = shutdown.clone();
        let socks_profile = profile;
        let socks_task = tokio::spawn(run_socks5_proxy(socks, socks_profile, socks_shutdown));
        let _ = ready.send(Ok(()));
        let result = tun2proxy::general_run_async(args, TUN_MTU, false, shutdown.clone()).await;
        shutdown.cancel();
        let _ = socks_task.await;
        result.map(|_| ()).map_err(|err| err.to_string())
    })
}

#[cfg(unix)]
async fn run_socks5_proxy(
    listener: tokio::net::TcpListener,
    profile: Profile,
    shutdown: CancellationToken,
) -> std::io::Result<()> {
    loop {
        let (client, _) = tokio::select! {
            _ = shutdown.cancelled() => return Ok(()),
            accepted = listener.accept() => accepted?,
        };
        let session_profile = profile;
        let session_shutdown = shutdown.clone();
        tokio::spawn(async move {
            if let Err(err) = handle_socks5_session(client, session_profile, session_shutdown).await
            {
                eprintln!("SoloX SOCKS5 session stopped: {err}");
            }
        });
    }
}

#[cfg(unix)]
async fn handle_socks5_session(
    mut client: tokio::net::TcpStream,
    profile: Profile,
    shutdown: CancellationToken,
) -> std::io::Result<()> {
    let mut header = [0_u8; 2];
    client.read_exact(&mut header).await?;
    if header[0] != 0x05 {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "unsupported SOCKS version",
        ));
    }
    let methods_len = usize::from(header[1]);
    let mut methods = vec![0_u8; methods_len];
    client.read_exact(&mut methods).await?;
    client.write_all(&[0x05, 0x00]).await?;

    let mut request = [0_u8; 4];
    client.read_exact(&mut request).await?;
    if request[0] != 0x05 {
        client
            .write_all(&[0x05, 0x07, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
            .await?;
        return Err(std::io::Error::new(
            std::io::ErrorKind::Unsupported,
            "unsupported SOCKS request version",
        ));
    }
    if request[1] == 0x03 {
        return handle_socks5_udp_associate(client, profile, shutdown).await;
    }
    if request[1] != 0x01 {
        client
            .write_all(&[0x05, 0x07, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
            .await?;
        return Err(std::io::Error::new(
            std::io::ErrorKind::Unsupported,
            "only SOCKS5 CONNECT and UDP ASSOCIATE are supported",
        ));
    }
    let host = read_socks_host(&mut client, request[3]).await?;
    let mut port = [0_u8; 2];
    client.read_exact(&mut port).await?;
    let target = format!("{host}:{}", u16::from_be_bytes(port));
    let server = match tokio::net::TcpStream::connect(target).await {
        Ok(server) => server,
        Err(err) => {
            client
                .write_all(&[0x05, 0x05, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
                .await?;
            return Err(err);
        }
    };
    client
        .write_all(&[0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0])
        .await?;

    let (client_reader, client_writer) = tokio::io::split(client);
    let (server_reader, server_writer) = tokio::io::split(server);
    let uplink = tokio::spawn(copy_shaped(
        client_reader,
        server_writer,
        Direction::Uplink,
        profile,
        shutdown.clone(),
        0x51A7E11,
    ));
    let downlink = tokio::spawn(copy_shaped(
        server_reader,
        client_writer,
        Direction::Downlink,
        profile,
        shutdown,
        0xD0A7111,
    ));
    let _ = tokio::join!(uplink, downlink);
    Ok(())
}

#[cfg(unix)]
async fn handle_socks5_udp_associate(
    mut client: tokio::net::TcpStream,
    profile: Profile,
    shutdown: CancellationToken,
) -> std::io::Result<()> {
    let udp = tokio::net::UdpSocket::bind("127.0.0.1:0").await?;
    let udp_addr = udp.local_addr()?;
    let mut response = vec![0x05, 0x00, 0x00];
    append_socks_addr(&mut response, udp_addr);
    client.write_all(&response).await?;

    let server = tokio::net::UdpSocket::bind("0.0.0.0:0").await?;
    let mut client_addr: Option<SocketAddr> = None;
    let mut shaper = PacketShaper::new(profile, 0x5CC50001);
    let mut client_buffer = vec![0_u8; 65_535];
    let mut server_buffer = vec![0_u8; 65_535];
    loop {
        tokio::select! {
            _ = shutdown.cancelled() => return Ok(()),
            received = udp.recv_from(&mut client_buffer) => {
                let (len, addr) = received?;
                client_addr = Some(addr);
                let Some((target, payload_offset)) = parse_socks_udp_packet(&client_buffer[..len]).await? else {
                    continue;
                };
                let packets = shape_datagram(&mut shaper, Direction::Uplink, client_buffer[payload_offset..len].to_vec()).await;
                for packet in packets {
                    server.send_to(&packet, target).await?;
                }
            }
            received = server.recv_from(&mut server_buffer) => {
                let (len, source) = received?;
                let Some(addr) = client_addr else {
                    continue;
                };
                let packets = shape_datagram(&mut shaper, Direction::Downlink, server_buffer[..len].to_vec()).await;
                for packet in packets {
                    let mut framed = Vec::with_capacity(packet.len() + 32);
                    framed.extend_from_slice(&[0, 0, 0]);
                    append_socks_addr(&mut framed, source);
                    framed.extend_from_slice(&packet);
                    udp.send_to(&framed, addr).await?;
                }
            }
            read = client.read_u8() => {
                match read {
                    Ok(_) => continue,
                    Err(_) => return Ok(()),
                }
            }
        }
    }
}

#[cfg(unix)]
async fn shape_datagram(
    shaper: &mut PacketShaper,
    direction: Direction,
    bytes: Vec<u8>,
) -> Vec<Vec<u8>> {
    let now = now_ms();
    match shaper.enqueue(direction, bytes, now) {
        ShapeOutcome::DroppedByLoss | ShapeOutcome::DroppedByOverflow => Vec::new(),
        ShapeOutcome::Queued { release_at_ms } => {
            let delay_ms = release_at_ms.saturating_sub(now_ms());
            if delay_ms > 0 {
                tokio::time::sleep(Duration::from_millis(delay_ms)).await;
            }
            shaper.poll_ready(direction, now_ms())
        }
    }
}

#[cfg(unix)]
async fn parse_socks_udp_packet(packet: &[u8]) -> std::io::Result<Option<(SocketAddr, usize)>> {
    if packet.len() < 4 || packet[0] != 0 || packet[1] != 0 {
        return Ok(None);
    }
    if packet[2] != 0 {
        return Ok(None);
    }
    let atyp = packet[3];
    let (host, port_offset) = match atyp {
        0x01 if packet.len() >= 10 => (
            std::net::IpAddr::V4(std::net::Ipv4Addr::new(
                packet[4], packet[5], packet[6], packet[7],
            )),
            8,
        ),
        0x04 if packet.len() >= 22 => {
            let mut addr = [0_u8; 16];
            addr.copy_from_slice(&packet[4..20]);
            (std::net::IpAddr::V6(std::net::Ipv6Addr::from(addr)), 20)
        }
        0x03 if packet.len() >= 5 => {
            let len = usize::from(packet[4]);
            if packet.len() < 5 + len + 2 {
                return Ok(None);
            }
            let name = String::from_utf8(packet[5..5 + len].to_vec()).map_err(|err| {
                std::io::Error::new(std::io::ErrorKind::InvalidData, err.to_string())
            })?;
            let port_offset = 5 + len;
            let port = u16::from_be_bytes([packet[port_offset], packet[port_offset + 1]]);
            let mut addrs = tokio::net::lookup_host((name.as_str(), port)).await?;
            let Some(addr) = addrs.next() else {
                return Ok(None);
            };
            return Ok(Some((addr, port_offset + 2)));
        }
        _ => return Ok(None),
    };
    if packet.len() < port_offset + 2 {
        return Ok(None);
    }
    let port = u16::from_be_bytes([packet[port_offset], packet[port_offset + 1]]);
    Ok(Some((SocketAddr::new(host, port), port_offset + 2)))
}

#[cfg(unix)]
fn append_socks_addr(buffer: &mut Vec<u8>, addr: SocketAddr) {
    match addr {
        SocketAddr::V4(v4) => {
            buffer.push(0x01);
            buffer.extend_from_slice(&v4.ip().octets());
            buffer.extend_from_slice(&v4.port().to_be_bytes());
        }
        SocketAddr::V6(v6) => {
            buffer.push(0x04);
            buffer.extend_from_slice(&v6.ip().octets());
            buffer.extend_from_slice(&v6.port().to_be_bytes());
        }
    }
}

#[cfg(unix)]
async fn read_socks_host<R>(reader: &mut R, atyp: u8) -> std::io::Result<String>
where
    R: AsyncRead + Unpin,
{
    match atyp {
        0x01 => {
            let mut addr = [0_u8; 4];
            reader.read_exact(&mut addr).await?;
            Ok(std::net::Ipv4Addr::from(addr).to_string())
        }
        0x03 => {
            let mut len = [0_u8; 1];
            reader.read_exact(&mut len).await?;
            let mut name = vec![0_u8; usize::from(len[0])];
            reader.read_exact(&mut name).await?;
            String::from_utf8(name).map_err(|err| {
                std::io::Error::new(std::io::ErrorKind::InvalidData, err.to_string())
            })
        }
        0x04 => {
            let mut addr = [0_u8; 16];
            reader.read_exact(&mut addr).await?;
            Ok(std::net::Ipv6Addr::from(addr).to_string())
        }
        _ => Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "unsupported SOCKS address type",
        )),
    }
}

#[cfg(unix)]
async fn copy_shaped<R, W>(
    mut reader: R,
    mut writer: W,
    direction: Direction,
    profile: Profile,
    shutdown: CancellationToken,
    seed: u64,
) -> std::io::Result<()>
where
    R: AsyncRead + Unpin,
    W: AsyncWrite + Unpin,
{
    let mut shaper = PacketShaper::new(profile, seed);
    let mut buffer = vec![0_u8; TUN_MTU as usize + 128];
    loop {
        let read = tokio::select! {
            _ = shutdown.cancelled() => return Ok(()),
            read = reader.read(&mut buffer) => read?,
        };
        if read == 0 {
            return Ok(());
        }
        let now = now_ms();
        match shaper.enqueue(direction, buffer[..read].to_vec(), now) {
            ShapeOutcome::DroppedByLoss | ShapeOutcome::DroppedByOverflow => continue,
            ShapeOutcome::Queued { release_at_ms } => {
                let delay_ms = release_at_ms.saturating_sub(now_ms());
                if delay_ms > 0 {
                    tokio::select! {
                        _ = shutdown.cancelled() => return Ok(()),
                        _ = tokio::time::sleep(Duration::from_millis(delay_ms)) => {}
                    }
                }
                for packet in shaper.poll_ready(direction, now_ms()) {
                    tokio::select! {
                        _ = shutdown.cancelled() => return Ok(()),
                        write = writer.write_all(&packet) => write?,
                    }
                }
            }
        }
    }
}

#[cfg(unix)]
fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}
