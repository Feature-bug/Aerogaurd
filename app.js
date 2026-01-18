// AeroGuard v3.0 - Production Ready
lucide.createIcons();

let history = { ax: [], ay: [], az: [], labels: [] };
const MAX_DATAPOINTS = 50;
let lastDataTimestamp = null;

// --- CHART INITIALIZATION ---
const chart = new ApexCharts(document.querySelector("#chart"), {
    series: [
        { name: 'X', data: [] },
        { name: 'Y', data: [] },
        { name: 'Z', data: [] }
    ],
    chart: { 
        type: 'line', 
        height: '100%', 
        toolbar: { show: false }, 
        animations: { 
            enabled: true, 
            easing: 'linear', 
            dynamicAnimation: { speed: 800 } 
        }, 
        background: 'transparent', 
        foreColor: '#475569' 
    },
    stroke: { curve: 'smooth', width: 2.5 },
    colors: ['#38bdf8', '#fb7185', '#10b981'],
    grid: { 
        borderColor: 'rgba(255,255,255,0.02)', 
        strokeDashArray: 4 
    },
    xaxis: { 
        labels: { show: false }, 
        axisBorder: { show: false }, 
        axisTicks: { show: false } 
    },
    yaxis: { 
        min: -2, 
        max: 2, 
        labels: { style: { fontSize: '10px' } } 
    },
    legend: { show: false },
    tooltip: { theme: 'dark' }
});
chart.render();

// ============================================
// UTILITY FUNCTIONS
// ============================================

function toggleSimulator() {
    const panel = document.getElementById('sim-panel');
    panel.classList.toggle('hidden');
    if (!panel.classList.contains('hidden')) {
        addLog("WARN", "⚠️ Simulation mode - NOT REAL DATA!");
    }
}

function addLog(type, msg) {
    const box = document.getElementById('logs');
    if (!box) return;
    
    const div = document.createElement('div');
    const time = new Date().toLocaleTimeString('en-GB', { hour12: false });
    
    let color = 'text-sky-400';
    if (type === 'WARN') color = 'text-amber-400';
    if (type === 'ERR') color = 'text-rose-400';
    if (type === 'GPS') color = 'text-emerald-400';
    if (type === 'MOTOR') color = 'text-purple-400';
    if (type === 'SIM') color = 'text-purple-400';
    if (type === 'INFO') color = 'text-slate-400';
    
    div.innerHTML = `<span class="text-slate-600">[${time}]</span> <span class="font-bold ${color}">${type}</span>: ${msg}`;
    box.prepend(div);
    if (box.children.length > 30) box.lastElementChild.remove();
}

function setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.innerText = val;
}

// ============================================
// SIMULATOR FUNCTIONS
// ============================================

async function sendSimData(mode) {
    let payload = {};
    
    if (mode === 'NORMAL') {
        payload = {
            gps: { 
                latitude: 10.0145, 
                longitude: 76.3200, 
                satellites: 18, 
                hdop: 110, // Raw value * 100
                gps_quality: "EXCELLENT"
            },
            mpu: { 
                vibration_rms: 0.05, 
                ax: 0.01, 
                ay: 0.01, 
                az: 1.0, 
                tilt_angle: 0.2 
            },
            motor: { 
                rpm: 1450, 
                hall_detected: true 
            },
            environment: { 
                temperature: 28.0, 
                humidity: 65, 
                light_percent: 75 
            },
            system: { 
                scan_triggered: false 
            }
        };
        addLog("SIM", "✅ Normal conditions set");
        
    } else if (mode === 'WARNING') {
        payload = {
            gps: { 
                latitude: 9.9410, 
                longitude: 76.2710, 
                satellites: 9, 
                hdop: 450,
                gps_quality: "MODERATE"
            },
            mpu: { 
                vibration_rms: 0.42, 
                ax: 0.05, 
                ay: 0.03, 
                az: 0.98, 
                tilt_angle: 5.0 
            },
            motor: { 
                rpm: 3200, 
                hall_detected: true 
            },
            environment: { 
                temperature: 32.0, 
                humidity: 75, 
                light_percent: 60 
            },
            system: { 
                scan_triggered: false 
            }
        };
        addLog("SIM", "⚠️ Warning state triggered");
        
    } else if (mode === 'CRITICAL') {
        payload = {
            gps: { 
                latitude: 9.9300, 
                longitude: 76.2670, 
                satellites: 4, 
                hdop: 1200,
                gps_quality: "POOR"
            },
            mpu: { 
                vibration_rms: 0.85, 
                ax: 0.15, 
                ay: 0.12, 
                az: 0.90, 
                tilt_angle: 15.0 
            },
            motor: { 
                rpm: 100, 
                hall_detected: false 
            },
            environment: { 
                temperature: 35.0, 
                humidity: 85, 
                light_percent: 40 
            },
            system: { 
                scan_triggered: false 
            }
        };
        addLog("SIM", "🚨 Critical state activated");
        
    } else if (mode === 'SCAN') {
        payload = { 
            system: { 
                scan_triggered: true 
            } 
        };
        addLog("SYS", "🔍 Diagnostic scan initiated");
        setTimeout(() => {
            sendSimData('NORMAL');
        }, 3000);
    }

    try {
        const response = await fetch('/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            addLog("ERR", `Failed to send data: ${response.status}`);
        }
    } catch (e) { 
        addLog("ERR", "Server connection failed"); 
        console.error('Simulator error:', e);
    }
}

// ============================================
// MAIN SYNC FUNCTION
// ============================================

async function sync() {
    try {
        // Cache-busting to prevent stale data
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/current?_=${timestamp}`, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        
        if (!response.ok) throw new Error("Server offline");
        const d = await response.json();

        // ============================================
        // DATA CHANGE DETECTION & LOGGING
        // ============================================
        if (lastDataTimestamp !== d.system.timestamp) {
            const source = d.system.source || "UNKNOWN";
            
            // Log GPS fix acquisition
            if (d.gps.latitude !== null && d.gps.longitude !== null && d.gps.satellites >= 4) {
                if (!lastDataTimestamp || d.gps.satellites !== 0) {
                    addLog("GPS", `Fix: ${d.gps.latitude.toFixed(4)}, ${d.gps.longitude.toFixed(4)} (${d.gps.satellites} sats)`);
                }
            }
            
            // Log motor activity
            if (d.motor.rpm > 500 && (!lastDataTimestamp || d.motor.rpm > 100)) {
                addLog("MOTOR", `Active: ${Math.round(d.motor.rpm)} RPM`);
            }
            
            lastDataTimestamp = d.system.timestamp;
        }

        // ============================================
        // ENVIRONMENT DATA
        // ============================================
        setVal('val-temp', d.environment.temperature !== null ? `${d.environment.temperature.toFixed(1)}°C` : '--°C');
        setVal('val-humid', d.environment.humidity !== null ? `${d.environment.humidity.toFixed(0)}%` : '--%');
        setVal('val-light', d.environment.light_percent !== null ? d.environment.light_percent.toFixed(0) : '--');
        
        // ============================================
        // MPU DATA
        // ============================================
        setVal('val-vib', d.mpu.vibration_rms.toFixed(3));
        setVal('val-tilt', `${d.mpu.tilt_angle.toFixed(1)}°`);
        
        // ============================================
        // MOTOR DATA
        // ============================================
        setVal('val-rpm', Math.round(d.motor.rpm));
        
        // Hall Sensor Status
        const hallTag = document.getElementById('hall-tag');
        if (hallTag) {
            if (d.motor.hall_detected) {
                hallTag.innerText = "HALL OK";
                hallTag.className = "text-[8px] font-black px-2 py-1 rounded-lg bg-emerald-400/10 text-emerald-400 border border-emerald-400/20";
            } else {
                hallTag.innerText = "HALL FAULT";
                hallTag.className = "text-[8px] font-black px-2 py-1 rounded-lg bg-rose-400/10 text-rose-400 border border-rose-400/20";
            }
        }

        // Fan rotation animation
        const fanIcon = document.getElementById('fan-icon');
        if (fanIcon) {
            if (d.motor.rpm > 500) {
                fanIcon.classList.add('spin-slow');
            } else {
                fanIcon.classList.remove('spin-slow');
            }
        }
        
        // ============================================
        // GPS DATA
        // ============================================
        
        // GPS Coordinates
        if (d.gps.latitude !== null && d.gps.longitude !== null) {
            setVal('val-lat', d.gps.latitude.toFixed(6));
            setVal('val-long', d.gps.longitude.toFixed(6));
        } else {
            setVal('val-lat', 'NO FIX');
            setVal('val-long', 'NO FIX');
        }
        
        // Satellites
        setVal('val-sats', d.gps.satellites || 0);
        
        // HDOP Display
        const hdopRaw = d.gps.hdop || 9999;
        const hdopActual = hdopRaw > 50 ? hdopRaw / 100.0 : hdopRaw;
        const hdopEl = document.getElementById('val-hdop');
        
        if (hdopEl) {
            if (hdopActual < 99) {
                hdopEl.innerText = hdopActual.toFixed(2);
                
                // Color code based on quality
                if (hdopActual < 2.0) {
                    hdopEl.className = 'text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20';
                } else if (hdopActual < 5.0) {
                    hdopEl.className = 'text-sky-400 font-bold bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20';
                } else if (hdopActual < 10.0) {
                    hdopEl.className = 'text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20';
                } else {
                    hdopEl.className = 'text-rose-400 font-bold bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20';
                }
            } else {
                hdopEl.innerText = "--";
                hdopEl.className = 'text-slate-400 font-bold bg-slate-500/10 px-2 py-0.5 rounded border border-slate-500/20';
            }
        }
        
        // GPS Quality Label
        const gpsQuality = d.gps.gps_quality || "UNKNOWN";
        const gpsQualityEl = document.getElementById('gps-quality');
        
        if (gpsQualityEl) {
            gpsQualityEl.innerText = gpsQuality;
            
            if (gpsQuality === "IDEAL" || gpsQuality === "EXCELLENT") {
                gpsQualityEl.className = 'text-[8px] font-black text-emerald-400 mt-1';
            } else if (gpsQuality === "GOOD") {
                gpsQualityEl.className = 'text-[8px] font-black text-sky-400 mt-1';
            } else if (gpsQuality === "MODERATE") {
                gpsQualityEl.className = 'text-[8px] font-black text-amber-400 mt-1';
            } else if (gpsQuality === "POOR" || gpsQuality === "FAIR") {
                gpsQualityEl.className = 'text-[8px] font-black text-rose-400 mt-1';
            } else {
                gpsQualityEl.className = 'text-[8px] font-black text-slate-500 mt-1';
            }
        }
        
        // Geo-Zone Display
        const zoneEl = document.getElementById('val-zone');
        if (zoneEl) {
            const zone = d.gps.geo_zone || "UNKNOWN";
            zoneEl.innerText = zone;
            
            if (zone === 'GREEN') {
                zoneEl.className = 'text-emerald-400 font-black uppercase tracking-tighter';
            } else if (zone === 'YELLOW') {
                zoneEl.className = 'text-amber-400 font-black uppercase tracking-tighter';
            } else if (zone === 'RED') {
                zoneEl.className = 'text-rose-500 font-black uppercase tracking-tighter';
            } else {
                zoneEl.className = 'text-slate-500 font-black uppercase tracking-tighter';
            }
        }

        // ============================================
        // RISK ASSESSMENT DISPLAY
        // ============================================
        
        const riskScore = d.system.risk_score || 0;
        const riskLevel = d.system.risk_level || 'STANDBY';
        
        setVal('val-risk', riskScore);
        setVal('val-blocked-reason', d.system.blocked_reason || "Awaiting Telemetry");
        
        // Risk Progress Bar
        const riskBar = document.getElementById('risk-progress');
        if (riskBar) {
            riskBar.style.width = `${riskScore}%`;
            riskBar.style.transition = 'width 0.3s ease';
            
            if (riskLevel === 'SAFE') {
                riskBar.style.backgroundColor = '#10b981';
            } else if (riskLevel === 'CAUTION') {
                riskBar.style.backgroundColor = '#f59e0b';
            } else if (riskLevel === 'ABORT') {
                riskBar.style.backgroundColor = '#ef4444';
            } else {
                riskBar.style.backgroundColor = '#64748b';
            }
        }
        
        // Risk Card Border
        const riskCard = riskBar?.parentElement?.parentElement;
        if (riskCard) {
            if (riskLevel === 'SAFE') {
                riskCard.className = 'xl:col-span-2 glass p-6 rounded-3xl border-t-2 border-t-emerald-500/50 relative overflow-hidden group';
            } else if (riskLevel === 'CAUTION') {
                riskCard.className = 'xl:col-span-2 glass p-6 rounded-3xl border-t-2 border-t-amber-500/50 relative overflow-hidden group';
            } else if (riskLevel === 'ABORT') {
                riskCard.className = 'xl:col-span-2 glass p-6 rounded-3xl border-t-2 border-t-rose-500/50 relative overflow-hidden group';
            } else {
                riskCard.className = 'xl:col-span-2 glass p-6 rounded-3xl border-t-2 border-t-slate-500/50 relative overflow-hidden group';
            }
        }
        
        // Risk Score Text Color
        const riskValue = document.getElementById('val-risk');
        if (riskValue) {
            if (riskLevel === 'SAFE') {
                riskValue.className = 'text-6xl font-black mono text-emerald-400 tracking-tighter';
            } else if (riskLevel === 'CAUTION') {
                riskValue.className = 'text-6xl font-black mono text-amber-400 tracking-tighter';
            } else if (riskLevel === 'ABORT') {
                riskValue.className = 'text-6xl font-black mono text-rose-400 tracking-tighter';
            } else {
                riskValue.className = 'text-6xl font-black mono text-slate-400 tracking-tighter';
            }
        }
        
        // Alert Label
        const alertLabel = document.getElementById('val-blocked-label');
        if (alertLabel) {
            if (riskLevel === 'SAFE') {
                alertLabel.className = 'text-[10px] font-black uppercase text-emerald-500 flex items-center gap-1';
                alertLabel.innerText = 'OPERATIONAL';
            } else if (riskLevel === 'CAUTION') {
                alertLabel.className = 'text-[10px] font-black uppercase text-amber-500 flex items-center gap-1';
                alertLabel.innerText = 'WARNING';
            } else if (riskLevel === 'ABORT') {
                alertLabel.className = 'text-[10px] font-black uppercase text-rose-500 flex items-center gap-1';
                alertLabel.innerText = 'ABORT';
            } else {
                alertLabel.className = 'text-[10px] font-black uppercase text-slate-500 flex items-center gap-1';
                alertLabel.innerText = 'STANDBY';
            }
        }

        // ============================================
        // SYSTEM READINESS STATUS
        // ============================================
        
        const statusText = document.getElementById('risk-status');
        const readiness = document.getElementById('sys-readiness');
        
        if (statusText && readiness) {
            if (riskLevel === 'SAFE') {
                readiness.className = "px-8 py-2 glass rounded-2xl border-l-4 border-l-emerald-500 flex items-center gap-6 shadow-xl";
                statusText.className = "font-black text-xl text-emerald-400 uppercase tracking-tighter neon-text";
                statusText.innerText = "SAFE_TO_FLY";
            } else if (riskLevel === 'CAUTION') {
                readiness.className = "px-8 py-2 glass rounded-2xl border-l-4 border-l-amber-500 flex items-center gap-6 shadow-xl";
                statusText.className = "font-black text-xl text-amber-500 uppercase tracking-tighter neon-text";
                statusText.innerText = "CAUTION";
            } else if (riskLevel === 'ABORT') {
                readiness.className = "px-8 py-2 glass rounded-2xl border-l-4 border-l-rose-500 flex items-center gap-6 shadow-xl";
                statusText.className = "font-black text-xl text-rose-500 uppercase tracking-tighter neon-text";
                statusText.innerText = "ABORT";
            } else {
                readiness.className = "px-8 py-2 glass rounded-2xl border-l-4 border-l-slate-500 flex items-center gap-6 shadow-xl";
                statusText.className = "font-black text-xl text-slate-400 uppercase tracking-tighter neon-text";
                statusText.innerText = "STANDBY";
            }
        }

        // ============================================
        // CONNECTION STATUS
        // ============================================
        
        const connTag = document.getElementById('conn-tag');
        if (connTag) {
            connTag.className = "flex items-center gap-2 text-emerald-400 font-black";
            connTag.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 status-pulse"></span> LINK_ACTIVE`;
        }
        
        // Data Source Indicator
        const source = d.system.source || "UNKNOWN";
        const sourceText = document.getElementById('data-source-text');
        const sourceIndicator = document.getElementById('data-source-indicator');

        if (sourceText && sourceIndicator) {
            sourceText.innerText = source;
            
            if (source === "ESP32") {
                sourceIndicator.className = "flex items-center gap-2 px-2 py-1 rounded bg-emerald-500/10 border border-emerald-500/20";
                sourceText.className = "text-emerald-400 font-bold";
                // Re-create icons for dynamically updated content
                lucide.createIcons();
            } else if (source === "WEB_SIM") {
                sourceIndicator.className = "flex items-center gap-2 px-2 py-1 rounded bg-purple-500/10 border border-purple-500/20";
                sourceText.className = "text-purple-400 font-bold";
                lucide.createIcons();
            } else {
                sourceIndicator.className = "flex items-center gap-2 px-2 py-1 rounded bg-slate-500/10 border border-slate-500/20";
                sourceText.className = "text-slate-400 font-bold";
                lucide.createIcons();
            }
        }
        
        // ============================================
        // TIMESTAMP & CLOCK
        // ============================================
        
        const clockEl = document.getElementById('clock');
        if (clockEl) {
            clockEl.innerText = new Date().toLocaleTimeString('en-GB', { hour12: false });
        }
        
        setVal('update-stamp', `Last Packet: ${new Date(d.system.timestamp).toLocaleTimeString()}`);

        // ============================================
        // CHART UPDATE (MPU Accelerometer)
        // ============================================
        
        history.ax.push(d.mpu.ax || 0);
        history.ay.push(d.mpu.ay || 0);
        history.az.push(d.mpu.az || 1);
        
        if (history.ax.length > MAX_DATAPOINTS) {
            history.ax.shift(); 
            history.ay.shift(); 
            history.az.shift();
        }
        
        chart.updateSeries([
            { data: history.ax }, 
            { data: history.ay }, 
            { data: history.az }
        ]);

    } catch (err) {
        console.error('❌ Sync error:', err);
        
        // Update connection status to offline
        const connTag = document.getElementById('conn-tag');
        if (connTag) {
            connTag.className = "flex items-center gap-2 text-rose-500 font-black";
            connTag.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-500"></span> OFFLINE`;
        }
    }
}

// ============================================
// INITIALIZATION
// ============================================

// Start sync loop (500ms = 2 updates per second)
setInterval(sync, 500);

// Initial sync
sync();

// Startup logs
addLog("INIT", "🚁 AeroGuard v3.0 Mission Control Online");
addLog("INFO", "Waiting for telemetry data...");