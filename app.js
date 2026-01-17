// AeroGuard v3.0 Core Logic - REAL-TIME FIXED
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
        type: 'line', height: '100%', toolbar: { show: false }, 
        animations: { enabled: true, easing: 'linear', dynamicAnimation: { speed: 800 } }, 
        background: 'transparent', foreColor: '#475569' 
    },
    stroke: { curve: 'smooth', width: 2.5 },
    colors: ['#38bdf8', '#fb7185', '#10b981'],
    grid: { borderColor: 'rgba(255,255,255,0.02)', strokeDashArray: 4 },
    xaxis: { labels: { show: false }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: { min: -15, max: 15, labels: { style: { fontSize: '10px' } } },
    legend: { show: false },
    tooltip: { theme: 'dark' }
});
chart.render();

function toggleSimulator() {
    document.getElementById('sim-panel').classList.toggle('hidden');
}

function addLog(type, msg) {
    const box = document.getElementById('logs');
    if (!box) return;
    const div = document.createElement('div');
    const time = new Date().toLocaleTimeString('en-GB', { hour12: false });
    div.innerHTML = `<span class="text-slate-600">[${time}]</span> <span class="font-bold text-sky-400">${type}</span>: ${msg}`;
    box.prepend(div);
    if (box.children.length > 30) box.lastElementChild.remove();
}

async function sendSimData(mode) {
    let payload = {};
    if (mode === 'NORMAL') {
        payload = {
            gps: { latitude: 9.9500, longitude: 76.2900, satellites: 18, hdop: 1.10 },
            mpu: { vibration_rms: 0.05, ax: 0.01, ay: 0.01, az: 1.0, tilt_angle: 0.2 },
            motor: { rpm: 1450, hall_detected: true },
            environment: { temperature: 28.0, humidity: 65, light_percent: 75 },
            system: { scan_triggered: false }
        };
    } else if (mode === 'WARNING') {
        payload = {
            gps: { latitude: 9.9400, longitude: 76.2800, satellites: 9, hdop: 4.5 },
            mpu: { vibration_rms: 0.42, ax: 0.05, ay: 0.03, az: 1.0, tilt_angle: 5.0 },
            motor: { rpm: 3200, hall_detected: true },
            environment: { temperature: 32.0, humidity: 75, light_percent: 60 },
            system: { scan_triggered: false }
        };
    } else if (mode === 'CRITICAL') {
        payload = {
            gps: { latitude: 9.9300, longitude: 76.2670, satellites: 4, hdop: 12.0 },
            mpu: { vibration_rms: 0.85, ax: 0.15, ay: 0.12, az: 0.95, tilt_angle: 15.0 },
            motor: { rpm: 100, hall_detected: false },
            environment: { temperature: 35.0, humidity: 85, light_percent: 40 },
            system: { scan_triggered: false }
        };
    } else if (mode === 'SCAN') {
        payload = { system: { scan_triggered: true } };
    }

    try {
        await fetch('/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        addLog("SIM", `Condition ${mode} injected.`);
    } catch (e) { addLog("ERR", "Sim failed."); }
}

async function sync() {
    try {
        // CRITICAL FIX: Cache-busting with timestamp
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/current?_=${timestamp}`, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        
        if (!response.ok) throw new Error("Offline");
        const d = await response.json();

        // DEBUGGING: Log when new data arrives
        if (lastDataTimestamp !== d.system.timestamp) {
            console.log(`[${new Date().toLocaleTimeString()}] 📡 NEW DATA - Light: ${d.environment.light_percent}%, Temp: ${d.environment.temperature}°C, RPM: ${d.motor.rpm}`);
            lastDataTimestamp = d.system.timestamp;
        }

        // 1. Hardware Scan Overlay (Triggered by Physical Button)
        const scanOverlay = document.getElementById('scan-overlay');
        if (scanOverlay) {
            if (d.system.scan_triggered) {
                if (scanOverlay.classList.contains('hidden')) {
                    addLog("SCAN", "Hardware Signal: Diagnostic Triggered");
                }
                scanOverlay.classList.remove('hidden');
            } else {
                scanOverlay.classList.add('hidden');
            }
        }

        // 2. Telemetry slots
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val;
        };

        // Environment Data
        setVal('val-temp', `${d.environment.temperature.toFixed(1)}°C`);
        setVal('val-humid', `${d.environment.humidity.toFixed(0)}%`);
        setVal('val-light', d.environment.light_percent.toFixed(0));
        
        // MPU Data
        setVal('val-vib', d.mpu.vibration_rms.toFixed(3));
        setVal('val-tilt', `${d.mpu.tilt_angle.toFixed(1)}°`);
        
        // Motor Data
        setVal('val-rpm', Math.round(d.motor.rpm));
        
        // GPS Data
        setVal('val-lat', d.gps.latitude.toFixed(6));
        setVal('val-long', d.gps.longitude.toFixed(6));
        setVal('val-sats', d.gps.satellites);
        setVal('val-hdop', d.gps.hdop.toFixed(2));
        
        // Geo-Zone with color coding
        const zoneEl = document.getElementById('val-zone');
        if (zoneEl) {
            zoneEl.innerText = d.gps.geo_zone;
            if (d.gps.geo_zone === 'GREEN') {
                zoneEl.className = 'text-emerald-400 font-black uppercase tracking-tighter';
            } else if (d.gps.geo_zone === 'YELLOW') {
                zoneEl.className = 'text-amber-400 font-black uppercase tracking-tighter';
            } else {
                zoneEl.className = 'text-rose-500 font-black uppercase tracking-tighter';
            }
        };
        
        // Weather Data
        if (d.weather) {
            setVal('val-wind', `${d.weather.wind_speed.toFixed(1)} m/s`);
            setVal('val-wind-display', d.weather.wind_speed.toFixed(1));
            setVal('val-weather-cond', d.weather.condition);
        }
        
        // Risk Assessment
        setVal('val-risk', d.system.risk_score);
        setVal('val-blocked-reason', d.system.blocked_reason || "Systems Nominal");
        setVal('update-stamp', `Last Packet: ${new Date(d.system.timestamp).toLocaleTimeString()}`);

        // Progress Bar - Smooth animation with color based on risk level
        const riskBar = document.getElementById('risk-progress');
        if (riskBar) {
            riskBar.style.width = `${d.system.risk_score}%`;
            riskBar.style.transition = 'width 0.3s ease';
            
            // Update progress bar color based on risk level
            if (d.system.risk_level === 'SAFE') {
                riskBar.style.backgroundColor = '#10b981'; // Green
            } else if (d.system.risk_level === 'CAUTION') {
                riskBar.style.backgroundColor = '#f59e0b'; // Amber
            } else {
                riskBar.style.backgroundColor = '#ef4444'; // Red
            }
        }
        
        // Update Mission Risk Fusion card styling based on risk level
        const riskCard = riskBar?.parentElement?.parentElement;
        if (riskCard) {
            if (d.system.risk_level === 'SAFE') {
                riskCard.className = 'xl:col-span-2 glass p-6 rounded-3xl border-t-2 border-t-emerald-500/50 relative overflow-hidden group';
            } else if (d.system.risk_level === 'CAUTION') {
                riskCard.className = 'xl:col-span-2 glass p-6 rounded-3xl border-t-2 border-t-amber-500/50 relative overflow-hidden group';
            } else {
                riskCard.className = 'xl:col-span-2 glass p-6 rounded-3xl border-t-2 border-t-rose-500/50 relative overflow-hidden group';
            }
        }
        
        // Update risk value text color
        const riskValue = document.getElementById('val-risk');
        if (riskValue) {
            if (d.system.risk_level === 'SAFE') {
                riskValue.className = 'text-6xl font-black mono text-emerald-400 tracking-tighter';
            } else if (d.system.risk_level === 'CAUTION') {
                riskValue.className = 'text-6xl font-black mono text-amber-400 tracking-tighter';
            } else {
                riskValue.className = 'text-6xl font-black mono text-rose-400 tracking-tighter';
            }
        }
        
        // Update ALERT label
        const alertLabel = document.getElementById('val-blocked-label');
        if (alertLabel) {
            if (d.system.risk_level === 'SAFE') {
                alertLabel.className = 'text-[10px] font-black uppercase text-emerald-500 flex items-center gap-1';
                alertLabel.innerText = 'OPERATIONAL';
            } else if (d.system.risk_level === 'CAUTION') {
                alertLabel.className = 'text-[10px] font-black uppercase text-amber-500 flex items-center gap-1';
                alertLabel.innerText = 'WARNING';
            } else {
                alertLabel.className = 'text-[10px] font-black uppercase text-rose-500 flex items-center gap-1';
                alertLabel.innerText = 'ALERT';
            }
        }
        
        // Hall Sensor Tag
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

        // System Readiness Status
        const statusText = document.getElementById('risk-status');
        const readiness = document.getElementById('sys-readiness');
        if (statusText && readiness) {
            if (d.system.risk_level === 'SAFE') {
                readiness.className = "px-8 py-2 glass rounded-2xl border-l-4 border-l-emerald-500 flex items-center gap-6 shadow-xl";
                statusText.className = "font-black text-xl text-emerald-400 uppercase tracking-tighter neon-text";
                statusText.innerText = "SAFE_TO_FLY";
            } else if (d.system.risk_level === 'CAUTION') {
                readiness.className = "px-8 py-2 glass rounded-2xl border-l-4 border-l-amber-500 flex items-center gap-6 shadow-xl";
                statusText.className = "font-black text-xl text-amber-500 uppercase tracking-tighter neon-text";
                statusText.innerText = "CAUTION";
            } else {
                readiness.className = "px-8 py-2 glass rounded-2xl border-l-4 border-l-rose-500 flex items-center gap-6 shadow-xl";
                statusText.className = "font-black text-xl text-rose-500 uppercase tracking-tighter neon-text";
                statusText.innerText = "ABORT";
            }
        }

        // Connectivity Status
        const source = d.system.source || "WIFI";
        const connTag = document.getElementById('conn-tag');
        if (connTag) {
            connTag.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 status-pulse"></span> ${source}_LINK_ACTIVE`;
        }

        // Visual FX - Fan rotation
        const fanIcon = document.getElementById('fan-icon');
        if (fanIcon) {
            if (d.motor.rpm > 500) {
                fanIcon.classList.add('spin-slow');
            } else {
                fanIcon.classList.remove('spin-slow');
            }
        }
        
        // Update Clock
        const clockEl = document.getElementById('clock');
        if (clockEl) {
            clockEl.innerText = new Date().toLocaleTimeString('en-GB', { hour12: false });
        }

        // Chart Update - MPU Accelerometer Data
        history.ax.push(d.mpu.ax);
        history.ay.push(d.mpu.ay);
        history.az.push(d.mpu.az);
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
        const connTag = document.getElementById('conn-tag');
        if (connTag) {
            connTag.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-500"></span> OFFLINE`;
        }
    }
}

// CRITICAL: Faster sync interval for real-time feel
setInterval(sync, 500);  // Update every 500ms (2x per second)
sync();  // Initial sync
addLog("INIT", "AeroGuard v3.0 Mission Control Online");