from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime, timezone
import ipaddress
import json
import logging
import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict
import re
import shutil
import socket
import sqlite3
import ssl
import subprocess
import sys
from typing import List, Optional
import uuid
import xml.etree.ElementTree as ET

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", ROOT_DIR / "spy_scanner.db")).expanduser()
SCHEMA_PATH = ROOT_DIR / "schema.sql"
db_initialized = False

app = FastAPI()
api_router = APIRouter(prefix="/api")
active_scans: dict[str, dict] = {}

CAMERA_VENDORS = {
    "00:80:F0": "Panasonic",
    "00:1C:B3": "Apple",
    "00:40:8C": "Axis Communications",
    "00:0E:8E": "SparkLAN",
    "00:12:43": "Cisco",
    "00:0F:7C": "ACTi",
    "00:1A:07": "Arecont Vision",
    "00:01:C0": "CompuLab",
    "00:0C:29": "VMware",
    "00:50:C2": "TRENDnet",
    "00:04:A5": "Barco",
    "00:09:18": "Samsung",
    "B4:A3:82": "Hikvision",
    "44:47:CC": "Hikvision",
    "C0:56:E3": "Hikvision",
    "54:C4:15": "Hikvision",
    "A4:14:37": "Dahua",
    "3C:EF:8C": "Dahua",
    "E0:50:8B": "Dahua",
    "00:62:6E": "Dahua",
    "7C:DD:90": "Reolink",
    "EC:71:DB": "Reolink",
    "00:E0:4C": "Realtek",
    "00:18:AE": "TVT",
    "DC:B5:0D": "Amcrest",
    "9C:8E:CD": "Amcrest",
    "40:9B:CD": "Foscam",
    "C4:D6:55": "Foscam",
    "78:A5:04": "TP-Link",
    "50:C7:BF": "TP-Link",
    "00:1E:58": "D-Link",
    "28:10:7B": "D-Link",
    "AC:CF:23": "Wansview",
    "00:15:5D": "Hyper-V",
    "08:00:27": "VirtualBox",
}

PORT_LABELS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    53: "DNS",
    80: "HTTP",
    88: "HTTP-ALT",
    139: "NetBIOS",
    443: "HTTPS",
    445: "SMB",
    554: "RTSP",
    631: "IPP",
    2020: "Camera-P2P",
    5000: "NAS-UI",
    5001: "NAS-SSL",
    5060: "SIP",
    8000: "HTTP-ALT",
    8080: "HTTP-ALT",
    8200: "Hikvision-SDK",
    8443: "HTTPS-ALT",
    8888: "HTTP-ALT",
    9000: "Camera-Control",
    9100: "JetDirect",
    9295: "Remote",
    9296: "Remote",
    37777: "Dahua-DVR",
    62078: "iDevice",
}

HTTP_PORTS = {80, 88, 443, 8000, 8080, 8443, 8888}
CAMERA_PORTS = {554, 2020, 8200, 9000, 37777}
CAMERA_VENDOR_KEYWORDS = {
    "hikvision",
    "dahua",
    "reolink",
    "amcrest",
    "foscam",
    "axis",
    "wansview",
    "acti",
    "arecont",
}
SCAN_PORTS = [
    21, 22, 23, 53, 80, 88, 139, 443, 445, 554, 631, 2020, 5000, 5001,
    5060, 8000, 8080, 8200, 8443, 8888, 9000, 9100, 9295, 9296, 37777, 62078,
]
DISCOVERY_PORTS = [80, 443, 445, 554, 8000, 8080]
HOST_SCAN_CONCURRENCY = 64
PORT_TIMEOUT_SECONDS = 0.35
BANNER_TIMEOUT_SECONDS = 1.0
PING_TIMEOUT_MS = 400
ENABLE_NMAP = shutil.which("nmap") is not None


class ServiceOut(BaseModel):
    port: int
    protocol: str = "tcp"
    service: str
    product: Optional[str] = None
    banner: Optional[str] = None
    notes: List[str] = []


class DeviceOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    ip: str
    mac: str
    vendor: str
    model: Optional[str] = None
    open_ports: List[int]
    device_type: str
    risk_score: int
    risk_factors: List[str]
    hostname: Optional[str] = None
    rtsp_open: bool = False
    web_ports_open: bool = False
    first_seen: str
    last_seen: str
    scan_engine: str = "tcp-connect"
    services: List[ServiceOut] = []


class ScanOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    subnet: str
    interface: str
    started_at: str
    completed_at: Optional[str] = None
    status: str
    total_devices: int = 0
    cameras_found: int = 0
    high_risk_count: int = 0
    devices: List[DeviceOut] = []
    scan_engine: str = "tcp-connect"
    progress: int = 0
    logs: List[str] = []


class ScanStartRequest(BaseModel):
    subnet: Optional[str] = "192.168.1.0/24"
    interface: Optional[str] = "eth0"


class StatsOut(BaseModel):
    total_scans: int
    total_devices_found: int
    total_cameras_found: int
    total_high_risk: int
    recent_scans: List[dict]


def _open_db_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    global db_initialized
    if not SCHEMA_PATH.exists():
        raise RuntimeError(f"Missing schema file: {SCHEMA_PATH}")
    with _open_db_connection() as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.commit()
    db_initialized = True


def ensure_db_initialized() -> None:
    if not db_initialized:
        init_db()


def get_db_connection() -> sqlite3.Connection:
    ensure_db_initialized()
    return _open_db_connection()


def persist_scan(scan_doc: dict) -> None:
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO scans (
                id, subnet, interface, started_at, completed_at, status,
                total_devices, cameras_found, high_risk_count, scan_engine, scan_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_doc["id"],
                scan_doc["subnet"],
                scan_doc["interface"],
                scan_doc["started_at"],
                scan_doc["completed_at"],
                scan_doc["status"],
                scan_doc["total_devices"],
                scan_doc["cameras_found"],
                scan_doc["high_risk_count"],
                scan_doc["scan_engine"],
                json.dumps(scan_doc),
            ),
        )
        connection.commit()


def fetch_scan(scan_id: str) -> Optional[dict]:
    with get_db_connection() as connection:
        row = connection.execute("SELECT scan_json FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if not row:
        return None
    return json.loads(row["scan_json"])


def fetch_all_scans() -> List[dict]:
    with get_db_connection() as connection:
        rows = connection.execute("SELECT scan_json FROM scans ORDER BY started_at DESC LIMIT 100").fetchall()
    return [json.loads(row["scan_json"]) for row in rows]


def active_log(message: str) -> str:
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"[{timestamp}] {message}"


def set_active_scan(scan_id: str, **updates) -> None:
    if scan_id in active_scans:
        active_scans[scan_id].update(updates)


def append_active_scan_log(scan_id: str, message: str) -> None:
    if scan_id in active_scans:
        active_scans[scan_id]["logs"] = [*active_scans[scan_id].get("logs", []), active_log(message)]


def delete_saved_scan(scan_id: str) -> bool:
    with get_db_connection() as connection:
        result = connection.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        connection.commit()
    return result.rowcount > 0


def fetch_stats_payload() -> dict:
    with get_db_connection() as connection:
        totals = connection.execute(
            """
            SELECT
                COUNT(*) AS total_scans,
                COALESCE(SUM(total_devices), 0) AS total_devices_found,
                COALESCE(SUM(cameras_found), 0) AS total_cameras_found,
                COALESCE(SUM(high_risk_count), 0) AS total_high_risk
            FROM scans
            """
        ).fetchone()
        recent_rows = connection.execute(
            """
            SELECT id, subnet, interface, started_at, completed_at, status,
                   total_devices, cameras_found, high_risk_count, scan_engine
            FROM scans
            ORDER BY started_at DESC
            LIMIT 5
            """
        ).fetchall()

    return {
        "total_scans": totals["total_scans"] if totals else 0,
        "total_devices_found": totals["total_devices_found"] if totals else 0,
        "total_cameras_found": totals["total_cameras_found"] if totals else 0,
        "total_high_risk": totals["total_high_risk"] if totals else 0,
        "recent_scans": [dict(row) for row in recent_rows],
    }


def lookup_vendor_from_mac(mac: str) -> str:
    if not mac or mac == "Unknown":
        return "Unknown"
    normalized_mac = mac.upper().replace("-", ":")
    for prefix, vendor in CAMERA_VENDORS.items():
        if normalized_mac.startswith(prefix):
            return vendor
    return "Unknown"


def build_note(label: str, value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return f"{label}: {cleaned}"


def calculate_risk(ports: List[int], mac: str, services: Optional[List[dict]] = None) -> tuple:
    score = 0
    factors = []
    rtsp = 554 in ports
    web_ports = [port for port in ports if port in HTTP_PORTS]
    camera_ports = [port for port in ports if port in CAMERA_PORTS]

    if rtsp:
        score += 40
        factors.append("RTSP port 554 open (+40)")
    if len(web_ports) >= 2:
        score += 20
        factors.append(f"Multiple web ports open: {web_ports} (+20)")
    elif len(web_ports) == 1:
        score += 10
        factors.append(f"Web port open: {web_ports[0]} (+10)")
    if 23 in ports:
        score += 15
        factors.append("Telnet port 23 exposed (+15)")
    if 21 in ports:
        score += 10
        factors.append("FTP port 21 exposed (+10)")

    vendor = lookup_vendor_from_mac(mac)
    if vendor != "Unknown" and any(keyword in vendor.lower() for keyword in CAMERA_VENDOR_KEYWORDS):
        score += 20
        factors.append("MAC vendor matches known camera manufacturer (+20)")

    if camera_ports:
        score += 20
        factors.append(f"Camera-specific ports detected: {camera_ports} (+20)")

    for service in services or []:
        product = (service.get("product") or "").lower()
        banner = (service.get("banner") or "").lower()
        service_name = (service.get("service") or "").lower()
        combined = " ".join([product, banner, service_name])
        if any(keyword in combined for keyword in CAMERA_VENDOR_KEYWORDS):
            score += 15
            factors.append(f"Service fingerprint suggests camera vendor on port {service['port']} (+15)")
            break

    return min(score, 100), factors, rtsp, len(web_ports) > 0


def classify_device(risk_score: int, rtsp: bool) -> str:
    if risk_score >= 60:
        return "Likely Camera"
    if risk_score >= 30 or rtsp:
        return "Possible Camera"
    return "Unknown"


def infer_device_type(ip: str, ports: List[int], hostname: Optional[str], risk_score: int, rtsp: bool) -> str:
    lowered_hostname = (hostname or "").lower()
    if risk_score >= 30 or rtsp:
        return classify_device(risk_score, rtsp)
    if ip.endswith(".1") and any(port in ports for port in [53, 80, 443]):
        return "Router"
    if any(port in ports for port in [631, 9100]):
        return "Printer"
    if 5060 in ports:
        return "Phone"
    if any(port in ports for port in [5000, 5001]):
        return "NAS"
    if any(port in ports for port in [9295, 9296]):
        return "Game Console"
    if any(port in ports for port in [139, 445]):
        return "Computer"
    if "tv" in lowered_hostname:
        return "Smart TV"
    return "Unknown"


def build_basic_device(ip: str, hostname: Optional[str], scan_engine: str = "icmp-arp") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "ip": ip,
        "mac": "Unknown",
        "vendor": "Unknown",
        "model": None,
        "open_ports": [],
        "device_type": "Unknown",
        "risk_score": 0,
        "risk_factors": [],
        "hostname": hostname,
        "rtsp_open": False,
        "web_ports_open": False,
        "first_seen": now,
        "last_seen": now,
        "scan_engine": scan_engine,
        "services": [],
    }


def build_basic_device_with_mac(ip: str, hostname: Optional[str], mac: str) -> dict:
    device = build_basic_device(ip, hostname)
    device["mac"] = mac
    device["vendor"] = lookup_vendor_from_mac(mac)
    return device


def get_arp_entries() -> dict:
    try:
        result = subprocess.run(
            ["arp", "-a"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    entries = {}
    windows_pattern = re.compile(r"^\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:-]{14,17})\s+\w+", re.MULTILINE)
    unix_pattern = re.compile(r"\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]{17})", re.MULTILINE)
    for ip, mac in windows_pattern.findall(result.stdout):
        entries[ip] = mac.replace("-", ":").upper()
    for ip, mac in unix_pattern.findall(result.stdout):
        entries[ip] = mac.upper()
    return entries


def parse_http_response(response_text: str) -> tuple:
    server = None
    title = None
    server_match = re.search(r"^Server:\s*(.+)$", response_text, re.IGNORECASE | re.MULTILINE)
    title_match = re.search(r"<title>(.*?)</title>", response_text, re.IGNORECASE | re.DOTALL)
    if server_match:
        server = server_match.group(1).strip()
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
    return server, title


async def collect_http_fingerprint(ip: str, port: int) -> dict:
    notes = []
    try:
        ssl_context = None
        if port in {443, 8443}:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port, ssl=ssl_context),
            timeout=BANNER_TIMEOUT_SECONDS,
        )
        request = f"GET / HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n"
        writer.write(request.encode("ascii", errors="ignore"))
        await writer.drain()
        data = await asyncio.wait_for(reader.read(2048), timeout=BANNER_TIMEOUT_SECONDS)
        writer.close()
        await writer.wait_closed()

        text = data.decode("utf-8", errors="ignore")
        server, title = parse_http_response(text)
        note_server = build_note("Server", server)
        note_title = build_note("Title", title)
        if note_server:
            notes.append(note_server)
        if note_title:
            notes.append(note_title)

        return {
            "port": port,
            "protocol": "tcp",
            "service": PORT_LABELS.get(port, "HTTP"),
            "product": server,
            "banner": title or server,
            "notes": notes,
        }
    except Exception:
        return {"port": port, "protocol": "tcp", "service": PORT_LABELS.get(port, "HTTP"), "product": None, "banner": None, "notes": []}


async def collect_rtsp_fingerprint(ip: str, port: int) -> dict:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=BANNER_TIMEOUT_SECONDS)
        request = f"OPTIONS rtsp://{ip}:{port}/ RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: SpyScanner\r\n\r\n"
        writer.write(request.encode("ascii", errors="ignore"))
        await writer.drain()
        data = await asyncio.wait_for(reader.read(1024), timeout=BANNER_TIMEOUT_SECONDS)
        writer.close()
        await writer.wait_closed()
        text = data.decode("utf-8", errors="ignore")
        public_match = re.search(r"^Public:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        notes = []
        if public_match:
            notes.append(f"RTSP Methods: {public_match.group(1).strip()}")
        return {
            "port": port,
            "protocol": "tcp",
            "service": "RTSP",
            "product": None,
            "banner": text.splitlines()[0] if text else None,
            "notes": notes,
        }
    except Exception:
        return {"port": port, "protocol": "tcp", "service": "RTSP", "product": None, "banner": None, "notes": []}


async def collect_generic_banner(ip: str, port: int) -> dict:
    service_name = PORT_LABELS.get(port, f"Port-{port}")
    notes = []
    banner = None
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=BANNER_TIMEOUT_SECONDS)
        if port in {21, 22, 23}:
            data = await asyncio.wait_for(reader.read(256), timeout=BANNER_TIMEOUT_SECONDS)
            banner = data.decode("utf-8", errors="ignore").strip() or None
        writer.close()
        await writer.wait_closed()
    except Exception:
        banner = None

    note = build_note("Observed", banner)
    if note:
        notes.append(note)
    return {"port": port, "protocol": "tcp", "service": service_name, "product": None, "banner": banner, "notes": notes}


async def fingerprint_service(ip: str, port: int) -> dict:
    if port in HTTP_PORTS:
        return await collect_http_fingerprint(ip, port)
    if port == 554:
        return await collect_rtsp_fingerprint(ip, port)
    return await collect_generic_banner(ip, port)


async def probe_port(ip: str, port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=PORT_TIMEOUT_SECONDS)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def resolve_hostname(ip: str) -> Optional[str]:
    try:
        host, _, _ = await asyncio.to_thread(socket.gethostbyaddr, ip)
        return host
    except Exception:
        return None


async def scan_host(ip: str, host_sem: asyncio.Semaphore) -> Optional[dict]:
    async with host_sem:
        checks = await asyncio.gather(*(probe_port(ip, port) for port in SCAN_PORTS))
        open_ports = [port for port, is_open in zip(SCAN_PORTS, checks) if is_open]
        if not open_ports:
            return None

        hostname = await resolve_hostname(ip)
        services = await asyncio.gather(*(fingerprint_service(ip, port) for port in open_ports))
        now = datetime.now(timezone.utc).isoformat()
        risk, factors, rtsp, web = calculate_risk(open_ports, "Unknown", services)

        return {
            "id": str(uuid.uuid4()),
            "ip": ip,
            "mac": "Unknown",
            "vendor": "Unknown",
            "model": None,
            "open_ports": open_ports,
            "device_type": infer_device_type(ip, open_ports, hostname, risk, rtsp),
            "risk_score": risk,
            "risk_factors": factors,
            "hostname": hostname,
            "rtsp_open": rtsp,
            "web_ports_open": web,
            "first_seen": now,
            "last_seen": now,
            "scan_engine": "tcp-connect",
            "services": services,
        }


def ping_host(ip: str) -> bool:
    if sys.platform.startswith("win"):
        command = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_MS), ip]
    else:
        command = ["ping", "-c", "1", "-W", "1", ip]

    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=3)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


async def discover_host(ip: str, host_sem: asyncio.Semaphore) -> Optional[dict]:
    async with host_sem:
        ping_task = asyncio.to_thread(ping_host, ip)
        port_task = asyncio.gather(*(probe_port(ip, port) for port in DISCOVERY_PORTS))
        ping_ok, checks = await asyncio.gather(ping_task, port_task)
        open_ports = [port for port, is_open in zip(DISCOVERY_PORTS, checks) if is_open]
        if not ping_ok and not open_ports:
            return None

        hostname = await resolve_hostname(ip)
        return {
            "ip": ip,
            "hostname": hostname,
            "open_ports": open_ports,
            "ping_ok": ping_ok,
        }


def parse_nmap_xml(xml_text: str) -> List[dict]:
    root = ET.fromstring(xml_text)
    devices = []
    for host in root.findall("host"):
        status = host.find("status")
        if status is not None and status.attrib.get("state") != "up":
            continue

        address_el = host.find("address[@addrtype='ipv4']")
        if address_el is None:
            continue

        ip = address_el.attrib["addr"]
        hostname_el = host.find("hostnames/hostname")
        hostname = hostname_el.attrib.get("name") if hostname_el is not None else None
        mac_el = host.find("address[@addrtype='mac']")
        mac = mac_el.attrib.get("addr", "Unknown") if mac_el is not None else "Unknown"
        vendor = mac_el.attrib.get("vendor", lookup_vendor_from_mac(mac)) if mac_el is not None else "Unknown"

        open_ports = []
        services = []
        for port_el in host.findall("ports/port"):
            state_el = port_el.find("state")
            if state_el is None or state_el.attrib.get("state") != "open":
                continue
            port = int(port_el.attrib["portid"])
            service_el = port_el.find("service")
            service_name = service_el.attrib.get("name") if service_el is not None else PORT_LABELS.get(port, "unknown")
            product = service_el.attrib.get("product") if service_el is not None else None
            version = service_el.attrib.get("version") if service_el is not None else None
            extrainfo = service_el.attrib.get("extrainfo") if service_el is not None else None
            notes = []
            for value in [build_note("Version", version), build_note("Extra", extrainfo)]:
                if value:
                    notes.append(value)
            services.append({
                "port": port,
                "protocol": port_el.attrib.get("protocol", "tcp"),
                "service": service_name,
                "product": product,
                "banner": version,
                "notes": notes,
            })
            open_ports.append(port)

        if not open_ports:
            continue

        now = datetime.now(timezone.utc).isoformat()
        risk, factors, rtsp, web = calculate_risk(open_ports, mac, services)
        devices.append({
            "id": str(uuid.uuid4()),
            "ip": ip,
            "mac": mac,
            "vendor": vendor,
            "model": None,
            "open_ports": sorted(open_ports),
            "device_type": infer_device_type(ip, open_ports, hostname, risk, rtsp),
            "risk_score": risk,
            "risk_factors": factors,
            "hostname": hostname,
            "rtsp_open": rtsp,
            "web_ports_open": web,
            "first_seen": now,
            "last_seen": now,
            "scan_engine": "nmap",
            "services": services,
        })

    devices.sort(key=lambda item: ipaddress.ip_address(item["ip"]))
    return devices


def run_nmap_scan(subnet: str) -> List[dict]:
    command = ["nmap", "-Pn", "-n", "-T4", "--open", "-sV", "-p", ",".join(str(port) for port in SCAN_PORTS), "-oX", "-", subnet]
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or "nmap scan failed")
    return parse_nmap_xml(result.stdout)


async def perform_network_scan(subnet: str, scan_id: Optional[str] = None) -> tuple[List[dict], str]:
    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid subnet: {subnet}") from exc

    hosts = list(network.hosts())
    if len(hosts) > 1024:
        raise HTTPException(status_code=400, detail="Subnet too large. Use /22 or smaller.")

    if scan_id:
        append_active_scan_log(scan_id, f"Queued {len(hosts)} hosts from subnet {subnet}")
        set_active_scan(scan_id, progress=5)

    if ENABLE_NMAP:
        try:
            if scan_id:
                append_active_scan_log(scan_id, "Using nmap engine for service detection")
                append_active_scan_log(scan_id, "Detailed live progress is limited while nmap runs")
                set_active_scan(scan_id, progress=15)
            devices = await asyncio.to_thread(run_nmap_scan, subnet)
            if scan_id:
                set_active_scan(scan_id, progress=95)
                append_active_scan_log(scan_id, f"Nmap reported {len(devices)} responsive hosts")
            return devices, "nmap"
        except Exception as exc:
            logger.warning("Falling back to tcp-connect scan because nmap failed: %s", exc)
            if scan_id:
                append_active_scan_log(scan_id, "Nmap unavailable, falling back to tcp-connect engine")

    host_sem = asyncio.Semaphore(HOST_SCAN_CONCURRENCY)
    total_hosts = len(hosts)
    append_limit = 40

    if scan_id:
        append_active_scan_log(scan_id, f"Running host discovery on {total_hosts} targets")
        set_active_scan(scan_id, progress=10)

    discovery_tasks = [asyncio.create_task(discover_host(str(host), host_sem)) for host in hosts]
    discovered_hosts = []
    processed_discovery = 0
    for task in asyncio.as_completed(discovery_tasks):
        result = await task
        processed_discovery += 1
        if result:
            discovered_hosts.append(result)
            if scan_id and len(discovered_hosts) <= append_limit:
                if result["open_ports"]:
                    append_active_scan_log(
                        scan_id,
                        f"Discovery hit: {result['ip']} on {','.join(str(port) for port in result['open_ports'])}",
                    )
                else:
                    append_active_scan_log(scan_id, f"Discovery hit: {result['ip']} responded to ping/ARP")
        if scan_id:
            progress = 10 + int((processed_discovery / max(total_hosts, 1)) * 30)
            set_active_scan(scan_id, progress=min(progress, 40))

    if scan_id:
        append_active_scan_log(scan_id, f"Discovery complete: {len(discovered_hosts)} responsive hosts")
        set_active_scan(scan_id, progress=45)

    detailed_tasks = [
        (host, asyncio.create_task(scan_host(host["ip"], host_sem)))
        for host in discovered_hosts
    ]
    devices = []
    processed_detail = 0
    total_detail = len(detailed_tasks)

    task_lookup = {task: host for host, task in detailed_tasks}
    pending = set(task_lookup.keys())
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            device = await task
            host = task_lookup[task]
            processed_detail += 1
            if device:
                devices.append(device)
                if scan_id and len(devices) <= append_limit:
                    port_summary = ",".join(str(port) for port in device["open_ports"][:4])
                    append_active_scan_log(
                        scan_id,
                        f"Fingerprint: {device['ip']} responded on {port_summary}{'...' if len(device['open_ports']) > 4 else ''}",
                    )
            elif host.get("ping_ok"):
                devices.append(build_basic_device(host["ip"], host.get("hostname")))
                if scan_id and len(devices) <= append_limit:
                    append_active_scan_log(scan_id, f"Host {host['ip']} is alive but exposes no common ports")
            if scan_id:
                if total_detail == 0:
                    set_active_scan(scan_id, progress=90)
                else:
                    progress = 45 + int((processed_detail / total_detail) * 45)
                    set_active_scan(scan_id, progress=min(progress, 92))

    arp_entries = get_arp_entries()
    discovered_ips = {host["ip"] for host in discovered_hosts}
    for ip, mac in arp_entries.items():
        try:
            if ipaddress.ip_address(ip) not in network:
                continue
        except ValueError:
            continue
        if ip in discovered_ips or any(device["ip"] == ip for device in devices):
            continue
        hostname = await resolve_hostname(ip)
        devices.append(build_basic_device_with_mac(ip, hostname, mac))
        if scan_id and len(devices) <= append_limit:
            append_active_scan_log(scan_id, f"ARP hit: {ip} is on-link but exposes no common ports")

    if scan_id:
        append_active_scan_log(scan_id, "Enriching devices with ARP and vendor data")
        set_active_scan(scan_id, progress=94)
    for device in devices:
        mac = arp_entries.get(device["ip"], "Unknown")
        risk, factors, rtsp, web = calculate_risk(device["open_ports"], mac, device["services"])
        device["mac"] = mac
        device["vendor"] = lookup_vendor_from_mac(mac)
        device["risk_score"] = risk
        device["risk_factors"] = factors
        device["rtsp_open"] = rtsp
        device["web_ports_open"] = web
        device["device_type"] = infer_device_type(device["ip"], device["open_ports"], device.get("hostname"), risk, rtsp)

    devices.sort(key=lambda item: ipaddress.ip_address(item["ip"]))
    if scan_id:
        append_active_scan_log(scan_id, f"Scan sweep complete: {len(devices)} responsive hosts found")
        set_active_scan(scan_id, progress=97)
    return devices, "tcp-connect"


async def run_scan_job(scan_id: str, subnet: str, interface: str, started_at: str) -> None:
    try:
        append_active_scan_log(scan_id, f"Starting scan on {subnet} via {interface}")
        devices, engine = await perform_network_scan(subnet, scan_id=scan_id)
        cameras = [device for device in devices if device["device_type"] in ["Likely Camera", "Possible Camera"]]
        high_risk = [device for device in devices if device["risk_score"] >= 60]
        completed_at = datetime.now(timezone.utc).isoformat()
        scan_doc = {
            "id": scan_id,
            "subnet": subnet,
            "interface": interface,
            "started_at": started_at,
            "completed_at": completed_at,
            "status": "completed",
            "total_devices": len(devices),
            "cameras_found": len(cameras),
            "high_risk_count": len(high_risk),
            "devices": devices,
            "scan_engine": engine,
            "progress": 100,
            "logs": [*active_scans.get(scan_id, {}).get("logs", []), active_log("Scan completed successfully")],
        }
        await asyncio.to_thread(persist_scan, scan_doc)
        active_scans.pop(scan_id, None)
    except Exception as exc:
        logger.exception("Scan job failed")
        if scan_id in active_scans:
            append_active_scan_log(scan_id, f"Scan failed: {exc}")
            set_active_scan(
                scan_id,
                status="failed",
                completed_at=datetime.now(timezone.utc).isoformat(),
                progress=100,
            )


def run_scan_job_sync(scan_id: str, subnet: str, interface: str, started_at: str) -> None:
    asyncio.run(run_scan_job(scan_id, subnet, interface, started_at))


@api_router.get("/")
async def root():
    return {"message": "SpyCam Scanner API"}


@api_router.post("/scans/start", response_model=ScanOut)
async def start_scan(req: ScanStartRequest):
    scan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    scan_doc = {
        "id": scan_id,
        "subnet": req.subnet,
        "interface": req.interface,
        "started_at": now,
        "completed_at": None,
        "status": "running",
        "total_devices": 0,
        "cameras_found": 0,
        "high_risk_count": 0,
        "devices": [],
        "scan_engine": "pending",
        "progress": 0,
        "logs": [active_log(f"Scan requested for {req.subnet}")],
    }
    active_scans[scan_id] = scan_doc
    asyncio.create_task(asyncio.to_thread(run_scan_job_sync, scan_id, req.subnet, req.interface, now))
    return ScanOut(**scan_doc)


@api_router.get("/scans", response_model=List[ScanOut])
async def list_scans():
    scans = await asyncio.to_thread(fetch_all_scans)
    running = list(active_scans.values())
    combined = sorted([*running, *scans], key=lambda scan: scan["started_at"], reverse=True)
    return [ScanOut(**scan) for scan in combined]


@api_router.get("/scans/{scan_id}", response_model=ScanOut)
async def get_scan(scan_id: str):
    scan = active_scans.get(scan_id)
    if not scan:
        scan = await asyncio.to_thread(fetch_scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanOut(**scan)


@api_router.delete("/scans/{scan_id}")
async def delete_scan(scan_id: str):
    deleted = await asyncio.to_thread(delete_saved_scan, scan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {"message": "Scan deleted"}


@api_router.get("/scans/{scan_id}/export")
async def export_scan(scan_id: str):
    scan = await asyncio.to_thread(fetch_scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@api_router.get("/stats", response_model=StatsOut)
async def get_stats():
    stats = await asyncio.to_thread(fetch_stats_payload)
    return StatsOut(**stats)


@app.on_event("startup")
async def startup() -> None:
    await asyncio.to_thread(init_db)


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
