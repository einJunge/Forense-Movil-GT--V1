import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import ShellTab from './ShellTab';
import PortsTab from './PortsTab';

const risk_color = r => ({ critical:'#dc2626', high:'#ea580c', medium:'#ca8a04', low:'#16a34a', clean:'#2563eb', unknown:'#6b7280' }[r] || '#6b7280');
const sev_color  = s => ({ critical:'#dc2626', high:'#ea580c', medium:'#ca8a04', low:'#16a34a' }[s] || '#6b7280');

export default function App({ activeCase=null }) {
  const [tab, setTab]             = useState('devices');
  const [devices, setDevices]     = useState([]);
  const [scans, setScans]         = useState([]);
  const [findings, setFindings]   = useState([]);
  const [events, setEvents]       = useState([]);
  const [adbStatus, setAdbStatus] = useState(null);
  const [loading, setLoading]     = useState(false);
  const [msg, setMsg]             = useState({ text:'', type:'info' });
  const [wifiHost, setWifiHost]   = useState('');
  const [wifiPort, setWifiPort]   = useState(5555);
  const [selScan, setSelScan]     = useState(null);
  const [selDevice, setSelDevice] = useState(null);

  // Forensics state
  const [permissions, setPermissions] = useState(null);
  const [ports, setPorts]             = useState(null);
  const [apps, setApps]               = useState(null);
  const [loadingF, setLoadingF]       = useState('');
  const [backupStatus, setBackupStatus] = useState(null);
  const [backupList, setBackupList] = useState([]);
  const [backupRun, setBackupRun] = useState('');
  const [scanProgress, setScanProgress] = useState(null);
  const [backupProgress, setBackupProgress] = useState(null);

  // Cases state
  const [cases, setCases] = useState([]);

  const notify = (text, type='ok') => setMsg({ text, type });

  const resetCaseView = () => {
    setScans([]);
    setFindings([]);
    setEvents([]);
    setPermissions(null);
    setPorts(null);
    setApps(null);
    setBackupStatus(null);
    setBackupList([]);
    setScanProgress(null);
    setBackupProgress(null);
    setSelScan(null);
  };

  const fetchAll = async () => {
    const caseId = Number(activeCase?.id || 0);
    try { const r = await axios.get('/api/adb/status'); setAdbStatus(r.data); } catch {}
    try {
      const r = await axios.get('/api/adb/discover');
      const devs = r.data.discovered_devices || [];
      setDevices(devs);
      if (devs.length > 0 && !selDevice) setSelDevice(devs[0]);
    } catch {}
    try {
      const r = await axios.get('/api/scans');
      const allScans = Array.isArray(r.data) ? r.data : [];
      const filteredScans = caseId ? allScans.filter(s => Number(s.case_id) === caseId) : [];
      setScans(filteredScans);
      if (selScan && !filteredScans.find(s => s.id === selScan.id)) setSelScan(null);
      const scanIds = new Set(filteredScans.map(s => s.id));
      try {
        const fr = await axios.get('/api/findings');
        const allFindings = Array.isArray(fr.data) ? fr.data : [];
        setFindings(allFindings.filter(f => scanIds.has(f.scan_id)));
      } catch { setFindings([]); }
      try {
        const er = await axios.get('/api/events');
        const allEvents = Array.isArray(er.data) ? er.data : [];
        setEvents(allEvents.filter(ev => scanIds.has(ev.scan_id)));
      } catch { setEvents([]); }
    } catch {
      setScans([]); setFindings([]); setEvents([]);
    }
    try {
      const r = await axios.get('/api/cases');
      setCases(Array.isArray(r.data) ? r.data : []);
    } catch {}
  };

  useEffect(() => { resetCaseView(); fetchAll(); }, [activeCase?.id]);

  useEffect(() => {
    const iv = setInterval(async () => {
      try {
        if (selDevice?.id) {
          const s = await axios.get(`/api/scans/progress/${selDevice.id}`);
          setScanProgress(s.data);
        }
        if (selDevice?.adb_serial) {
          const b = await axios.get(`/api/android/backup/progress/${selDevice.adb_serial}`);
          setBackupProgress(b.data);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(iv);
  }, [selDevice]);

  const startScan = async (deviceId) => {
    setLoading(true); notify('⏳ Escaneando... puede tardar varios minutos.', 'info');
    try {
      await axios.post('/api/scans', { device_id: deviceId }, { timeout: 300000 });
      if (activeCase?.id) {
        setTimeout(async () => {
          try {
            const rs = await axios.get('/api/scans');
            const all = Array.isArray(rs.data) ? rs.data : [];
            const latest = all.filter(s => s.device_id === deviceId).sort((a,b) => b.id - a.id)[0];
            if (latest?.id) await axios.post(`/api/cases/assign-scan/${latest.id}`, { case_id: Number(activeCase.id) });
          } catch {}
        }, 1500);
      }
      notify('✅ Escaneo iniciado.', 'ok');
      setTab('scans');
    } catch(e) { notify('❌ ' + (e.response?.data?.detail || e.message), 'err'); }
    setLoading(false);
  };

  const generateReport = async (scanId) => {
    try {
      await axios.post(`/api/reports/scans/${scanId}/generate`);
      notify('✅ Reporte listo.', 'ok');
    } catch(e) { notify('❌ ' + (e.response?.data?.detail || e.message), 'err'); }
  };

  const connectWifi = async () => {
    if (!wifiHost.trim()) { notify('❌ Ingresa la IP', 'err'); return; }
    try {
      const r = await axios.post('/api/adb/connect-wifi', { host: wifiHost.trim(), port: Number(wifiPort) });
      const ok = r.data?.success ?? r.data?.result?.includes('connected');
      notify('📡 ' + r.data.result, ok ? 'ok' : 'err');
      if (ok) await fetchAll();
    } catch(e) { notify('❌ ' + (e.response?.data?.detail || e.message), 'err'); }
  };

  const loadPermissions = async () => {
    if (!selDevice) return;
    setLoadingF('perms'); setPermissions(null);
    try {
      const r = await axios.get(`/api/forensics/${selDevice.adb_serial}/permissions`, { timeout: 120000 });
      setPermissions(r.data.apps_with_dangerous_permissions || []);
    } catch(e) { notify('❌ Error cargando permisos: ' + (e.response?.data?.detail || e.message), 'err'); }
    setLoadingF('');
  };

  const loadPorts = async () => {
    if (!selDevice) return;
    setLoadingF('ports'); setPorts(null);
    try {
      const r = await axios.get(`/api/forensics/${selDevice.adb_serial}/ports`, { timeout: 30000 });
      setPorts(r.data);
    } catch(e) { notify('❌ Error cargando puertos: ' + (e.response?.data?.detail || e.message), 'err'); }
    setLoadingF('');
  };

  const loadBackupStatus = async () => {
    if (!selDevice) return;
    setBackupRun('status');
    try {
      const r = await axios.get(`/api/android/backup/status/${selDevice.adb_serial}`, { timeout: 60000 });
      setBackupStatus(r.data);
      const l = await axios.get('/api/android/backup/list');
      setBackupList(l.data?.items || []);
    } catch(e) { notify('❌ Error backup Android: ' + (e.response?.data?.detail || e.message), 'err'); }
    setBackupRun('');
  };

  const cancelAndroidBackup = async () => {
    if (!selDevice) return;
    if (!window.confirm('¿Cancelar backup Android en ejecución?')) return;
    try {
      const r = await axios.post(`/api/android/backup/cancel/${selDevice.adb_serial}`);
      alert(r.data?.message || 'Solicitud enviada');
      notify(r.data?.message || 'Solicitud enviada', r.data?.ok ? 'info' : 'err');
    } catch(e) {
      alert(e.response?.data?.detail || e.message);
      notify('❌ ' + (e.response?.data?.detail || e.message), 'err');
    }
  };

  const runAndroidBackup = async (mode) => {
    if (!selDevice) return;
    setBackupRun(mode);
    try {
      await axios.post(`/api/android/backup/${mode}/${selDevice.adb_serial}`, {}, { timeout: 3600000 });
      notify(`✅ Backup ${mode} iniciado`, 'ok');
      await loadBackupStatus();
    } catch(e) { notify('❌ Error ejecutando backup Android: ' + (e.response?.data?.detail || e.message), 'err'); }
    setBackupRun('');
  };

  const loadApps = async () => {
    if (!selDevice) return;
    setLoadingF('apps'); setApps(null);
    try {
      const r = await axios.get(`/api/forensics/${selDevice.adb_serial}/apps`, { timeout: 120000 });
      setApps(r.data.third_party_apps || []);
    } catch(e) { notify('❌ Error cargando apps: ' + (e.response?.data?.detail || e.message), 'err'); }
    setLoadingF('');
  };

  const assignScanToCase = async (scanId, caseId) => {
    if (!caseId) return;
    try {
      const r = await axios.post(`/api/cases/assign-scan/${scanId}`, { case_id: Number(caseId) });
      notify(`✅ Scan ${scanId} asignado a ${r.data.case_name}`, 'ok');
      await fetchAll();
    } catch(e) { notify('❌ Error asignando caso: ' + (e.response?.data?.detail || e.message), 'err'); }
  };

  const S = { background:'#0f172a', minHeight:'100vh', color:'#e2e8f0', fontFamily:'monospace' };
  const card = { background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:16, marginBottom:10 };
  const btn = (color='#2563eb') => ({ background:color, color:'#fff', border:'none', borderRadius:8, padding:'8px 16px', cursor:'pointer', fontWeight:'bold', fontSize:12 });
  const tabStyle = (t) => ({ ...btn(tab===t ? '#2563eb' : '#0f172a'), borderRadius:0, borderBottom: tab===t ? '2px solid #38bdf8' : '2px solid transparent', fontFamily:'monospace' });
  const msgBg = { ok:'#14532d', err:'#7f1d1d', info:'#1e3a5f' };

  const TABS = [
    ['devices','📱 Dispositivos'],
    ['scans','🧪 Escaneos'],
    ['perms','🔐 Permisos'],
    ['ports','🌐 Puertos'],
    ['apps','📦 Aplicaciones'],
    ['backup','💾 Backup'],
    ['shell','💻 Shell'],
    ['findings','⚠️ Hallazgos'],
    ['timeline','📋 Timeline'],
  ];

  return (
    <div style={S}>
      {/* HEADER */}
      <div style={{ background:'#0f172a', borderBottom:'1px solid #1e293b', padding:'12px 24px', display:'flex', alignItems:'center', gap:12 }}>
        <span style={{ fontSize:20 }}>🔍</span>
        <span style={{ fontSize:18, fontWeight:'bold', color:'#38bdf8', letterSpacing:1 }}>ANDROID FORENSICS</span>
        {adbStatus && (
          <span style={{ marginLeft:12, fontSize:11, background: adbStatus.adb_installed ? '#14532d' : '#7f1d1d', color:'#fff', borderRadius:6, padding:'3px 10px' }}>
            {adbStatus.adb_installed ? `✅ ADB (${adbStatus.raw_devices?.length||0} dispositivos)` : '❌ ADB no instalado'}
          </span>
        )}
        {selDevice && (
          <span style={{ marginLeft:8, fontSize:11, background:'#1e3a5f', color:'#93c5fd', borderRadius:6, padding:'3px 10px' }}>
            🎯 {selDevice.manufacturer} {selDevice.model} [{selDevice.adb_serial}]
          </span>
        )}
        <button style={{ ...btn('#0f766e'), marginLeft:'auto', fontSize:11 }} onClick={fetchAll}>🔄 Actualizar</button>
      </div>

      {adbStatus && !adbStatus.adb_installed && (
        <div style={{ background:'#7f1d1d', padding:'8px 24px', fontSize:12 }}>
          ⚠️ Instala ADB: <code style={{background:'#450a0a', padding:'2px 6px', borderRadius:4}}>sudo apt install adb</code>
        </div>
      )}

      {/* NAV */}
      <div style={{ display:'flex', borderBottom:'1px solid #1e293b', background:'#0f172a', flexWrap:'wrap' }}>
        {TABS.map(([k,v]) => <button key={k} style={tabStyle(k)} onClick={() => setTab(k)}>{v}</button>)}
      </div>

      <div style={{ padding:'16px 24px' }}>

        {msg.text && <div style={{ background:msgBg[msg.type]||'#1e293b', borderRadius:8, padding:'10px 14px', marginBottom:14, fontSize:12 }}>{msg.text}</div>}

        {(scanProgress || backupProgress) && <div style={{ display:'grid', gap:10, marginBottom:14 }}>
          {scanProgress && scanProgress.status !== 'idle' && <div style={{ ...card, marginBottom:0 }}>
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}><span style={{ color:'#38bdf8', fontWeight:'bold', fontSize:13 }}>🧪 Estado del escaneo</span><span style={{ fontSize:12 }}>{scanProgress.percent || 0}%</span></div>
            <div style={{ height:12, background:'#0f172a', border:'1px solid #334155', borderRadius:999, overflow:'hidden' }}><div style={{ width:`${scanProgress.percent || 0}%`, height:'100%', background:'#2563eb' }} /></div>
            <div style={{ marginTop:8, fontSize:12, color:'#94a3b8' }}>{scanProgress.stage || 'Sin estado'}</div>
          </div>}
          {backupProgress && backupProgress.status !== 'idle' && <div style={{ ...card, marginBottom:0 }}>
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}><span style={{ color:'#38bdf8', fontWeight:'bold', fontSize:13 }}>💾 Estado del backup</span><span style={{ fontSize:12 }}>{backupProgress.percent || 0}%</span></div>
            <div style={{ height:12, background:'#0f172a', border:'1px solid #334155', borderRadius:999, overflow:'hidden' }}><div style={{ width:`${backupProgress.percent || 0}%`, height:'100%', background:'#0f766e' }} /></div>
            <div style={{ marginTop:8, fontSize:12, color:'#94a3b8' }}>{backupProgress.stage || 'Sin estado'}</div>
            <div style={{ marginTop:6, fontSize:11, color: backupProgress.status === 'cancelled' ? '#fca5a5' : '#94a3b8' }}>Estado: {backupProgress.status || 'idle'}</div>
          </div>}
        </div>}

        {/* ── DISPOSITIVOS ── */}
        {tab === 'devices' && <>
          <h2 style={{ color:'#38bdf8', fontSize:14, marginBottom:12 }}>📱 Dispositivos Conectados</h2>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(300px, 1fr))', gap:12 }}>
            {devices.length === 0
              ? <div style={{ ...card, color:'#64748b', textAlign:'center', padding:32, gridColumn:'1/-1' }}>No se detectaron dispositivos.</div>
              : devices.map((d,i) => (
              <div key={i} style={{ ...card, border: selDevice?.adb_serial === d.adb_serial ? '1px solid #2563eb' : '1px solid #334155' }} onClick={() => setSelDevice(d)}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                  <div>
                    <div style={{ fontWeight:'bold', fontSize:15 }}>{d.manufacturer} {d.model}</div>
                    <div style={{ color:'#94a3b8', fontSize:11, marginTop:2 }}>{d.adb_serial} · Android {d.android_version}</div>
                  </div>
                  <span style={{ background: d.connection_type==='usb' ? '#1e3a5f' : '#3f6212', color:'#fff', fontSize:9, padding:'2px 6px', borderRadius:4 }}>
                    {(d.connection_type || 'unknown').toUpperCase()}
                  </span>
                </div>
                <div style={{ marginTop:12, display:'flex', gap:8 }}>
                  <button style={btn('#2563eb')} onClick={(e) => { e.stopPropagation(); startScan(d.id); }}>🧪 Escanear</button>
                  <button style={btn('#334155')} onClick={(e) => { e.stopPropagation(); setSelDevice(d); setTab('shell'); }}>💻 Shell</button>
                </div>
              </div>
            ))}
          </div>

          <div style={{ ...card, marginTop:20 }}>
            <h3 style={{ fontSize:13, color:'#38bdf8', marginBottom:10 }}>📡 Conectar por WiFi (ADB over IP)</h3>
            <div style={{ display:'flex', gap:8 }}>
              <input value={wifiHost} onChange={e=>setWifiHost(e.target.value)} placeholder="192.168.1.X" style={{ flex:2, background:'#0f172a', border:'1px solid #334155', borderRadius:6, padding:'8px 12px', color:'#fff', fontSize:13 }} />
              <input value={wifiPort} onChange={e=>setWifiPort(e.target.value)} type="number" style={{ flex:1, background:'#0f172a', border:'1px solid #334155', borderRadius:6, padding:'8px 12px', color:'#fff', fontSize:13 }} />
              <button style={btn('#0f766e')} onClick={connectWifi}>Conectar</button>
            </div>
          </div>
        </>}

        {/* ── ESCANEOS ── */}
        {tab === 'scans' && <>
          <h2 style={{ color:'#38bdf8', fontSize:14, marginBottom:12 }}>🧪 Historial de Escaneos</h2>
          {scans.length === 0
            ? <div style={{ ...card, color:'#64748b', textAlign:'center', padding:32 }}>No hay escaneos para este caso.</div>
            : scans.map((s,i) => (
              <div key={i} style={card}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <div>
                    <div style={{ fontWeight:'bold', fontSize:14 }}>Scan #{s.id} — {new Date(s.created_at).toLocaleString()}</div>
                    <div style={{ color:'#94a3b8', fontSize:11, marginTop:2 }}>Dispositivo ID: {s.device_id}</div>
                  </div>
                  <div style={{ textAlign:'right', display:'flex', flexDirection:'column', gap:4, alignItems:'flex-end' }}>
                    <span style={{ background:risk_color(s.risk_level), color:'#fff', borderRadius:6, padding:'2px 8px', fontSize:11 }}>{(s.risk_level||'unknown').toUpperCase()}</span>
                    <span style={{ color:'#94a3b8', fontSize:11 }}>{s.status}</span>
                  </div>
                  <div style={{ display:'flex', gap:6 }}>
                    <button style={btn('#334155')} onClick={() => { setSelScan(s.id); setTab('findings'); }}>🔍 Hallazgos</button>
                    <button style={btn('#0f766e')} onClick={() => generateReport(s.id)}>📄 Procesar</button>
                  </div>
                </div>
              </div>
            ))
          }
        </>}

        {/* ── PERMISOS ── */}
        {tab === 'perms' && <>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
            <h2 style={{ color:'#38bdf8', fontSize:14, margin:0 }}>🔐 Análisis de Permisos</h2>
            <button style={btn('#2563eb')} onClick={loadPermissions} disabled={loadingF==='perms'}>{loadingF==='perms' ? '⏳ Cargando...' : 'Cargar Permisos'}</button>
          </div>
          {!selDevice
            ? <div style={{ ...card, color:'#f87171', textAlign:'center', padding:32 }}>Selecciona un dispositivo en la pestaña 📱 Dispositivos.</div>
            : !permissions
              ? <div style={{ ...card, color:'#64748b', textAlign:'center', padding:32 }}>Haz clic en "Cargar Permisos" para analizar el dispositivo.</div>
              : (
                <div style={{ display:'grid', gap:10 }}>
                  {permissions.map((p,i) => (
                    <div key={i} style={card}>
                      <div style={{ fontWeight:'bold', color:'#f1f5f9' }}>{p.package}</div>
                      <div style={{ fontSize:10, color:'#64748b', marginTop:2 }}>{p.total} permiso(s) peligroso(s)</div>
                      <div style={{ display:'flex', flexWrap:'wrap', gap:4, marginTop:8 }}>
                        {(p.dangerous_permissions||[]).map((pr,pi) => (
                          <span key={pi} style={{ fontSize:10, background: pr.granted ? '#450a0a' : '#1e293b', color: pr.granted ? '#fca5a5' : '#64748b', padding:'2px 6px', borderRadius:4, border: pr.granted ? '1px solid #dc2626' : '1px solid #334155' }}>
                            {pr.permission}{pr.granted ? ' ✓' : ''}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )
          }
        </>}

        {/* ── PUERTOS — usa el componente PortsTab con las props correctas ── */}
        {tab === 'ports' && (
          <PortsTab
            ports={ports}
            loadPorts={loadPorts}
            loadingF={loadingF}
            selDevice={selDevice}
          />
        )}

        {/* ── APLICACIONES ── */}
        {tab === 'apps' && <>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
            <h2 style={{ color:'#38bdf8', fontSize:14, margin:0 }}>📦 Aplicaciones Instaladas</h2>
            <button style={btn('#2563eb')} onClick={loadApps} disabled={loadingF==='apps'}>{loadingF==='apps' ? '⏳ Cargando...' : 'Listar Apps'}</button>
          </div>
          {!selDevice
            ? <div style={{ ...card, color:'#f87171', textAlign:'center', padding:32 }}>Selecciona un dispositivo en la pestaña 📱 Dispositivos.</div>
            : !apps
              ? <div style={{ ...card, color:'#64748b', textAlign:'center', padding:32 }}>Haz clic en "Listar Apps" para obtener el inventario.</div>
              : (
                <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(280px, 1fr))', gap:10 }}>
                  {apps.map((a,i) => (
                    <div key={i} style={{ ...card, padding:12 }}>
                      <div style={{ fontWeight:'bold', fontSize:12, color:'#38bdf8', wordBreak:'break-all' }}>{a.package}</div>
                      <div style={{ color:'#94a3b8', fontSize:10, marginTop:4 }}>Versión: {a.version || 'N/D'}</div>
                      <div style={{ color:'#64748b', fontSize:10, marginTop:2, wordBreak:'break-all' }}>APK: {a.apk_path || 'N/D'}</div>
                    </div>
                  ))}
                </div>
              )
          }
        </>}

        {/* ── SHELL — usa el componente ShellTab con la prop correcta ── */}
        {tab === 'shell' && (
          <ShellTab selDevice={selDevice} />
        )}

        {/* ── BACKUP ── */}
        {tab === 'backup' && <>
          <h2 style={{ color:'#38bdf8', fontSize:14, marginBottom:12 }}>💾 Backup Android</h2>
          {!selDevice ? (
            <div style={{ ...card, color:'#f87171', textAlign:'center', padding:32 }}>Selecciona un dispositivo en la pestaña 📱 Dispositivos.</div>
          ) : (<>
            <div style={{ ...card }}>
              <div style={{ fontSize:13, color:'#38bdf8', fontWeight:'bold', marginBottom:8 }}>Modo dual</div>
              <div style={{ fontSize:12, color:'#94a3b8', marginBottom:12 }}>
                Backup básico usando lo que ADB permite sin root, y backup avanzado solo si el equipo expone root por <code>su</code>.
              </div>
              <div style={{ display:'flex', gap:8, flexWrap:'wrap', marginBottom:12 }}>
                <button style={btn('#334155')} onClick={loadBackupStatus} disabled={backupRun==='status'}>
                  {backupRun==='status' ? '⏳ Cargando...' : 'Estado'}
                </button>
                <button style={btn('#0f766e')} onClick={() => runAndroidBackup('basic')} disabled={backupRun==='basic'}>
                  {backupRun==='basic' ? '⏳ Ejecutando...' : 'Backup básico'}
                </button>
                <button style={btn('#7c3aed')} onClick={() => runAndroidBackup('advanced')} disabled={backupRun==='advanced' || !backupStatus?.root_available}>
                  {backupRun==='advanced' ? '⏳ Ejecutando...' : 'Backup avanzado root'}
                </button>
                <button style={btn('#b91c1c')} onClick={cancelAndroidBackup}>Cancelar</button>
              </div>
              <div style={{ fontSize:11, color:'#94a3b8' }}>
                Básico: DCIM, Pictures, Movies, Download, Documents, WhatsApp, Android/media y listado de paquetes. Avanzado: rutas root y artefactos del sistema si <code>su -c</code> responde como uid=0.
              </div>
            </div>

            <div style={{ ...card }}>
              <div style={{ fontSize:13, color:'#38bdf8', fontWeight:'bold', marginBottom:8 }}>Estado actual</div>
              {!backupStatus
                ? <div style={{ color:'#94a3b8', fontSize:12 }}>Haz clic en "Estado" para cargar.</div>
                : <>
                  <div style={{ fontSize:12, marginBottom:6 }}>ADB: <span style={{ color:'#93c5fd' }}>{backupStatus.adb_state}</span></div>
                  <div style={{ fontSize:12, marginBottom:6 }}>Root disponible: <span style={{ color: backupStatus.root_available ? '#86efac' : '#fca5a5' }}>{String(backupStatus.root_available)}</span></div>
                  <div style={{ fontSize:12, marginBottom:6 }}>Modo seguro: <span style={{ color:'#cbd5e1' }}>{String(backupStatus.safe_mode)}</span></div>
                  <div style={{ fontSize:12, color:'#94a3b8' }}>Directorio: {backupStatus.backup_root}</div>
                </>
              }
            </div>

            <div style={{ ...card }}>
              <div style={{ fontSize:13, color:'#38bdf8', fontWeight:'bold', marginBottom:8 }}>Respaldos generados</div>
              {backupList.length === 0
                ? <div style={{ color:'#94a3b8', fontSize:12 }}>No hay respaldos Android todavía.</div>
                : backupList.map((b,i) => (
                  <div key={i} style={{ background:'#0f172a', border:'1px solid #334155', borderRadius:8, padding:10, marginBottom:8 }}>
                    <div style={{ fontSize:12, color:'#e2e8f0' }}>Serial: {b.serial}</div>
                    <div style={{ fontSize:11, color:'#94a3b8' }}>Ruta: {b.path}</div>
                    <div style={{ fontSize:11, color:'#94a3b8' }}>Basic: {String(b.has_basic)} | Advanced: {String(b.has_advanced)}</div>
                  </div>
                ))
              }
            </div>
          </>)}
        </>}

        {/* ── HALLAZGOS ── */}
        {tab === 'findings' && <>
          <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:12 }}>
            <h2 style={{ color:'#38bdf8', fontSize:14, margin:0 }}>⚠️ Hallazgos</h2>
            {selScan && <><span style={{ fontSize:11, color:'#94a3b8' }}>Scan #{selScan}</span>
              <button style={{ ...btn('#334155'), padding:'4px 8px', fontSize:11 }} onClick={() => setSelScan(null)}>Ver todos</button></>}
          </div>
          {(selScan ? findings.filter(f => f.scan_id===selScan) : findings).length === 0
            ? <div style={{ ...card, color:'#64748b', textAlign:'center', padding:32 }}>Sin hallazgos.</div>
            : (selScan ? findings.filter(f => f.scan_id===selScan) : findings).map((f,i) => (
              <div key={i} style={card}>
                <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:6 }}>
                  <span style={{ background:sev_color(f.severity), color:'#fff', borderRadius:6, padding:'2px 8px', fontSize:11 }}>{(f.severity||'?').toUpperCase()}</span>
                  <span style={{ fontWeight:'bold', color:'#f1f5f9', fontSize:13 }}>{f.category}</span>
                  <span style={{ color:'#64748b', fontSize:11 }}>via {f.tool}</span>
                </div>
                <div style={{ color:'#cbd5e1', fontSize:12, fontFamily:'monospace' }}>{f.evidence}</div>
              </div>
            ))
          }
        </>}

        {/* ── TIMELINE ── */}
        {tab === 'timeline' && <>
          <h2 style={{ color:'#38bdf8', fontSize:14, marginBottom:12 }}>📋 Línea de Tiempo</h2>
          {events.length === 0
            ? <div style={{ ...card, color:'#64748b', textAlign:'center', padding:32 }}>Sin eventos.</div>
            : [...events].reverse().map((e,i) => (
              <div key={i} style={{ display:'flex', gap:12, alignItems:'flex-start', marginBottom:6 }}>
                <span style={{ color:'#475569', fontSize:11, minWidth:65 }}>{new Date(e.timestamp).toLocaleTimeString()}</span>
                <span style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:6, padding:'2px 8px', fontSize:11, color:'#38bdf8', minWidth:55, textAlign:'center' }}>{e.source}</span>
                <span style={{ color:'#e2e8f0', fontSize:12, fontFamily:'monospace' }}>{e.message}</span>
              </div>
            ))
          }
        </>}
      </div>
    </div>
  );
}
