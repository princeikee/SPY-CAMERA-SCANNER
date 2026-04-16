# SpyCam Scanner - PRD

## Original Problem Statement
Build a spy camera scanner / network spy camera detector - a cybersecurity tool to detect potential IP cameras and surveillance devices on a local network using legitimate network scanning techniques.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Shadcn/UI + Framer Motion + Phosphor Icons
- **Backend**: FastAPI (Python) + Motor (async MongoDB)
- **Database**: MongoDB
- **Design Theme**: Dark tactical "Control Room" aesthetic (Chivo/IBM Plex Sans/JetBrains Mono fonts)

## User Personas
- Cybersecurity professionals performing network audits
- Privacy-conscious users checking for hidden cameras in Airbnb/hotels
- IT administrators monitoring network devices

## Core Requirements
1. Network Discovery - Scan subnet for connected devices
2. Camera Detection - Identify potential cameras via port analysis and MAC vendor matching
3. Risk Scoring - 0-100 risk score based on open ports, vendor, behavior
4. Scan History - Store and retrieve past scan results
5. Export - Download scan results as JSON

## What's Been Implemented (April 16, 2026)
- Full backend API with scan creation, history, stats, export, deletion
- Simulated network scanning with realistic device generation (routers, phones, cameras, etc.)
- Camera detection logic: RTSP(554)=+40, Web ports=+20, MAC vendor=+20, Camera ports=+20
- Dashboard with metrics cards, scan animation, device table, filter dropdown
- Device details side sheet with full port analysis and risk factors
- Scan history page with view/export/delete functionality
- Dark tactical UI with Chivo/IBM Plex Sans/JetBrains Mono typography
- Color-coded risk levels (Critical/High/Medium/Low)
- Responsive design

## Prioritized Backlog
### P0 (Done)
- [x] Network scanning simulation
- [x] Device detection & classification
- [x] Risk scoring system
- [x] Dashboard with metrics
- [x] Device table with filtering
- [x] Scan history CRUD
- [x] Export to JSON

### P1 (Next)
- [ ] Real network scanning with python-nmap (for self-hosted deployments)
- [ ] Continuous monitoring mode (--watch)
- [ ] CSV export format
- [ ] RTSP stream preview attempt

### P2 (Future)
- [ ] MAC vendor lookup via online API
- [ ] "New device detected" alerts
- [ ] Network topology visualization
- [ ] Scheduled auto-scans
- [ ] Email notifications for high-risk devices
