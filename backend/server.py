from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import random
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# --- Known Camera Manufacturers (MAC prefix -> Vendor) ---
CAMERA_VENDORS = {
    "00:80:F0": "Panasonic", "00:1C:B3": "Apple", "00:40:8C": "Axis Communications",
    "00:0E:8E": "SparkLAN", "00:12:43": "Cisco", "00:0F:7C": "ACTi",
    "00:1A:07": "Arecont Vision", "00:01:C0": "CompuLab", "00:0C:29": "VMware",
    "00:50:C2": "TRENDnet", "00:04:A5": "Barco", "00:09:18": "Samsung",
    "B4:A3:82": "Hikvision", "44:47:CC": "Hikvision", "C0:56:E3": "Hikvision",
    "54:C4:15": "Hikvision", "A4:14:37": "Dahua", "3C:EF:8C": "Dahua",
    "E0:50:8B": "Dahua", "00:62:6E": "Dahua", "7C:DD:90": "Reolink",
    "EC:71:DB": "Reolink", "00:E0:4C": "Realtek", "00:18:AE": "TVT",
    "DC:B5:0D": "Amcrest", "9C:8E:CD": "Amcrest", "40:9B:CD": "Foscam",
    "C4:D6:55": "Foscam", "78:A5:04": "TP-Link", "50:C7:BF": "TP-Link",
    "00:1E:58": "D-Link", "28:10:7B": "D-Link", "AC:CF:23": "Wansview",
    "00:15:5D": "Hyper-V", "08:00:27": "VirtualBox",
}

COMMON_DEVICES = [
    {"type": "router", "vendor": "TP-Link", "ports": [80, 443, 53], "mac_prefix": "78:A5:04"},
    {"type": "router", "vendor": "Netgear", "ports": [80, 443], "mac_prefix": "00:1E:2A"},
    {"type": "phone", "vendor": "Apple", "ports": [62078], "mac_prefix": "00:1C:B3"},
    {"type": "phone", "vendor": "Samsung", "ports": [5060], "mac_prefix": "00:09:18"},
    {"type": "laptop", "vendor": "Dell", "ports": [445, 139], "mac_prefix": "00:14:22"},
    {"type": "printer", "vendor": "HP", "ports": [80, 443, 631, 9100], "mac_prefix": "00:1E:0B"},
    {"type": "smart_tv", "vendor": "LG", "ports": [80, 8080, 9080], "mac_prefix": "00:1C:62"},
    {"type": "iot_device", "vendor": "Amazon", "ports": [8443, 443], "mac_prefix": "44:65:0D"},
    {"type": "nas", "vendor": "Synology", "ports": [80, 443, 5000, 5001], "mac_prefix": "00:11:32"},
    {"type": "game_console", "vendor": "Sony", "ports": [9295, 9296], "mac_prefix": "00:1D:0D"},
]

CAMERA_DEVICES = [
    {"vendor": "Hikvision", "model": "DS-2CD2143G2-IU", "ports": [80, 443, 554, 8000, 8200], "mac_prefix": "B4:A3:82"},
    {"vendor": "Hikvision", "model": "DS-2CD2085FWD-I", "ports": [80, 554, 8000], "mac_prefix": "44:47:CC"},
    {"vendor": "Dahua", "model": "IPC-HDW5442TM-ASE", "ports": [80, 554, 8080, 37777], "mac_prefix": "A4:14:37"},
    {"vendor": "Dahua", "model": "IPC-HFW2431T-ZS", "ports": [80, 554, 37777], "mac_prefix": "3C:EF:8C"},
    {"vendor": "Reolink", "model": "RLC-810A", "ports": [80, 554, 8000, 9000], "mac_prefix": "7C:DD:90"},
    {"vendor": "Amcrest", "model": "IP4M-1051B", "ports": [80, 554, 8080, 37777], "mac_prefix": "DC:B5:0D"},
    {"vendor": "Foscam", "model": "FI9961EP", "ports": [80, 443, 554, 88], "mac_prefix": "40:9B:CD"},
    {"vendor": "Axis", "model": "P3245-V", "ports": [80, 443, 554], "mac_prefix": "00:40:8C"},
    {"vendor": "Unknown", "model": "Generic IP Cam", "ports": [80, 554, 8080], "mac_prefix": "AC:CF:23"},
    {"vendor": "TP-Link", "model": "Tapo C200", "ports": [80, 554, 2020], "mac_prefix": "50:C7:BF"},
]

# --- Models ---
class DeviceOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    ip: str
    mac: str
    vendor: str
    model: Optional[str] = None
    open_ports: List[int]
    device_type: str  # "Unknown" | "Possible Camera" | "Likely Camera" | "Router" | "Phone" etc
    risk_score: int
    risk_factors: List[str]
    hostname: Optional[str] = None
    rtsp_open: bool = False
    web_ports_open: bool = False
    first_seen: str
    last_seen: str

class ScanOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    subnet: str
    interface: str
    started_at: str
    completed_at: Optional[str] = None
    status: str  # "running" | "completed" | "failed"
    total_devices: int = 0
    cameras_found: int = 0
    high_risk_count: int = 0
    devices: List[DeviceOut] = []

class ScanStartRequest(BaseModel):
    subnet: Optional[str] = "192.168.1.0/24"
    interface: Optional[str] = "eth0"

class StatsOut(BaseModel):
    total_scans: int
    total_devices_found: int
    total_cameras_found: int
    total_high_risk: int
    recent_scans: List[dict]

# --- Helper Functions ---
def generate_mac(prefix: str) -> str:
    return f"{prefix}:{random.randint(0,255):02X}:{random.randint(0,255):02X}:{random.randint(0,255):02X}"

def calculate_risk(ports: List[int], mac: str) -> tuple:
    score = 0
    factors = []
    rtsp = 554 in ports
    web_ports = [p for p in ports if p in [80, 8080, 8000, 8888, 88]]
    camera_ports = [p for p in ports if p in [37777, 8200, 9000, 2020]]

    if rtsp:
        score += 40
        factors.append("RTSP port 554 open (+40)")
    if len(web_ports) >= 2:
        score += 20
        factors.append(f"Multiple web ports open: {web_ports} (+20)")
    elif len(web_ports) == 1:
        score += 10
        factors.append(f"Web port open: {web_ports[0]} (+10)")
    
    mac_prefix = mac[:8].upper()
    vendor_match = any(
        vendor.lower() in ["hikvision", "dahua", "reolink", "amcrest", "foscam", "axis", "wansview", "acti", "arecont"]
        for prefix_key, vendor in CAMERA_VENDORS.items()
        if mac.upper().startswith(prefix_key)
    )
    if vendor_match:
        score += 20
        factors.append("MAC vendor matches known camera manufacturer (+20)")
    
    if camera_ports:
        score += 20
        factors.append(f"Camera-specific ports detected: {camera_ports} (+20)")

    return min(score, 100), factors, rtsp, len(web_ports) > 0

def classify_device(risk_score: int, rtsp: bool) -> str:
    if risk_score >= 60:
        return "Likely Camera"
    elif risk_score >= 30 or rtsp:
        return "Possible Camera"
    return "Unknown"

def generate_scan_devices(subnet: str) -> List[dict]:
    base_ip = subnet.rsplit('.', 1)[0]
    devices = []
    used_ips = set()
    
    # Add router at .1
    router = COMMON_DEVICES[0]
    ip = f"{base_ip}.1"
    used_ips.add(ip)
    mac = generate_mac(router["mac_prefix"])
    risk, factors, rtsp, web = calculate_risk(router["ports"], mac)
    devices.append({
        "id": str(uuid.uuid4()), "ip": ip, "mac": mac,
        "vendor": router["vendor"], "model": "Archer AX73",
        "open_ports": router["ports"], "device_type": "Router",
        "risk_score": risk, "risk_factors": factors,
        "hostname": "router.local", "rtsp_open": rtsp, "web_ports_open": web,
        "first_seen": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
    })

    # Add random normal devices
    num_normal = random.randint(5, 10)
    for _ in range(num_normal):
        template = random.choice(COMMON_DEVICES[1:])
        while True:
            ip_end = random.randint(2, 254)
            ip = f"{base_ip}.{ip_end}"
            if ip not in used_ips:
                used_ips.add(ip)
                break
        mac = generate_mac(template["mac_prefix"])
        ports = template["ports"][:]
        if random.random() < 0.1:
            ports.append(random.choice([8080, 8000]))
        risk, factors, rtsp, web = calculate_risk(ports, mac)
        dtype = template["type"].replace("_", " ").title()
        if risk >= 30:
            dtype = classify_device(risk, rtsp)
        
        hostname = None
        if template["type"] == "phone":
            hostname = f"{template['vendor'].lower()}-phone.local"
        elif template["type"] == "laptop":
            hostname = f"{template['vendor'].lower()}-pc.local"

        devices.append({
            "id": str(uuid.uuid4()), "ip": ip, "mac": mac,
            "vendor": template["vendor"], "model": None,
            "open_ports": sorted(ports), "device_type": dtype,
            "risk_score": risk, "risk_factors": factors,
            "hostname": hostname, "rtsp_open": rtsp, "web_ports_open": web,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        })

    # Add camera devices (1–4)
    num_cameras = random.randint(1, 4)
    for _ in range(num_cameras):
        cam = random.choice(CAMERA_DEVICES)
        while True:
            ip_end = random.randint(100, 254)
            ip = f"{base_ip}.{ip_end}"
            if ip not in used_ips:
                used_ips.add(ip)
                break
        mac = generate_mac(cam["mac_prefix"])
        ports = cam["ports"][:]
        risk, factors, rtsp, web = calculate_risk(ports, mac)
        dtype = classify_device(risk, rtsp)
        
        devices.append({
            "id": str(uuid.uuid4()), "ip": ip, "mac": mac,
            "vendor": cam["vendor"], "model": cam["model"],
            "open_ports": sorted(ports), "device_type": dtype,
            "risk_score": risk, "risk_factors": factors,
            "hostname": None, "rtsp_open": rtsp, "web_ports_open": web,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        })

    devices.sort(key=lambda d: d["ip"])
    return devices

# --- Routes ---

@api_router.get("/")
async def root():
    return {"message": "SpyCam Scanner API"}

@api_router.post("/scans/start", response_model=ScanOut)
async def start_scan(req: ScanStartRequest):
    scan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    devices = generate_scan_devices(req.subnet)
    cameras = [d for d in devices if d["device_type"] in ["Likely Camera", "Possible Camera"]]
    high_risk = [d for d in devices if d["risk_score"] >= 60]
    
    scan_doc = {
        "id": scan_id,
        "subnet": req.subnet,
        "interface": req.interface,
        "started_at": now,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "total_devices": len(devices),
        "cameras_found": len(cameras),
        "high_risk_count": len(high_risk),
        "devices": devices,
    }
    
    await db.scans.insert_one(scan_doc)
    
    return ScanOut(**scan_doc)

@api_router.get("/scans", response_model=List[ScanOut])
async def list_scans():
    scans = await db.scans.find({}, {"_id": 0}).sort("started_at", -1).to_list(100)
    return [ScanOut(**s) for s in scans]

@api_router.get("/scans/{scan_id}", response_model=ScanOut)
async def get_scan(scan_id: str):
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanOut(**scan)

@api_router.delete("/scans/{scan_id}")
async def delete_scan(scan_id: str):
    result = await db.scans.delete_one({"id": scan_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {"message": "Scan deleted"}

@api_router.get("/scans/{scan_id}/export")
async def export_scan(scan_id: str):
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan

@api_router.get("/stats", response_model=StatsOut)
async def get_stats():
    total_scans = await db.scans.count_documents({})
    
    pipeline = [
        {"$group": {
            "_id": None,
            "total_devices": {"$sum": "$total_devices"},
            "total_cameras": {"$sum": "$cameras_found"},
            "total_high_risk": {"$sum": "$high_risk_count"},
        }}
    ]
    agg = await db.scans.aggregate(pipeline).to_list(1)
    
    stats = agg[0] if agg else {"total_devices": 0, "total_cameras": 0, "total_high_risk": 0}
    
    recent = await db.scans.find({}, {"_id": 0, "devices": 0}).sort("started_at", -1).to_list(5)
    
    return StatsOut(
        total_scans=total_scans,
        total_devices_found=stats.get("total_devices", 0),
        total_cameras_found=stats.get("total_cameras", 0),
        total_high_risk=stats.get("total_high_risk", 0),
        recent_scans=recent,
    )

# Include router + middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
