import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';

export default function IOSPanel({ activeCase=null }) {
  const [devices, setDevices] = useState([]);
  const [selected, setSelected] = useState('');
  const [msg, setMsg] = useState('');
  const [tab, setTab] = useState('live');
  const [backups, setBackups] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [messages, setMessages] = useState([]);
  const [sqliteItems, setSqliteItems] = useState([]);
  const [plistView, setPlistView] = useState('');
  const [manifestData, setManifestData] = useState(null);
  const [exportsList, setExportsList] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState('');
  const [progress, setProgress] = useState(null);

  const resetCaseView = () => {
    setSelected('');
    setBackups([]);
    setPhotos([]);
    setMessages([]);
    setSqliteItems([]);
    setPlistView('');
    setManifestData(null);
    setExportsList([]);
    setStatus(null);
    setMsg('');
    setProgress(null);
    setTab('live');
  };

  const nav = [
    ['live','En vivo'],
    ['backups','Respaldos'],
    ['selective','Selectivo'],
    ['photos','Fotos'],
    ['messages','Mensajes'],
    ['sqlite','SQLite'],
    ['plist','Plist'],
    ['reports','Estado']
  ];

  const card = { background:'#0f172a', border:'1px solid #334155', borderRadius:14, padding:16 };
  const btn = (active=false, color='#334155') => ({ background: color, color:'#fff', border:'1px solid #334155', borderRadius:12, padding:'10px 12px', cursor:'pointer', fontWeight:800, opacity: active ? 1 : 0.96 });
  const safe = async (fn, fallback=null) => { try { return await fn(); } catch { return fallback; } };

  const load = async () => {
    setLoading('load');
    const st = await safe(() => axios.get('/api/ios/status'));
    if (st?.data) setStatus(st.data);
    const r = await safe(() => axios.get('/api/ios/devices'));
    const devs = r?.data?.devices || [];
    setDevices(devs);
    if (!selected && devs.length) setSelected(devs[0]);
    const b = await safe(() => axios.get('/api/ios/backup/list'));
    setBackups(b?.data?.backups || []);
    const ex = await safe(() => axios.get('/api/ios/export/list'));
    setExportsList(ex?.data?.exports || []);
    setLoading('');
    setMsg(devs.length ? 'iOS listo' : 'Sin dispositivo iOS detectado');
  };

  const pair = async () => {
    if (!selected) return setMsg('Selecciona un dispositivo');
    setLoading('pair');
    const r = await safe(() => axios.post(`/api/ios/pair/${selected}`));
    setMsg(r?.data?.stderr || r?.data?.stdout || 'Pair ejecutado');
    setLoading('');
  };

  const cancelBackup = async () => {
    if (!selected) return;
    if (!window.confirm('¿Cancelar backup iOS en ejecución?')) return;
    const r = await safe(() => axios.post(`/api/ios/cancel/${selected}`));
    alert(r?.data?.message || 'Solicitud enviada');
    setMsg(r?.data?.message || 'Solicitud enviada');
  };

  const backup = async () => {
    if (!selected) return setMsg('Selecciona un dispositivo');
    setLoading('backup');
    const r = await safe(() => axios.post(`/api/ios/backup/${selected}`));
    setMsg(r?.data?.stderr || r?.data?.stdout || 'Backup ejecutado');
    setLoading('');
    await load();
  };

  const selectiveBackup = async (category) => {
    if (!selected) return setMsg('Selecciona un dispositivo');
    setLoading(category);
    const r = await safe(() => axios.post(`/api/ios/backup/selective/${selected}`, null, { params: { category } }));
    setMsg(`Exportación ${category}: ${r?.data?.count || 0} archivos`);
    setLoading('');
    await load();
  };

  const loadArtifacts = async (kind) => {
    if (!backups[0]) return setMsg('Primero crea o detecta un respaldo');
    setLoading(kind);
    const map = { photos: setPhotos, messages: setMessages, sqlite: setSqliteItems };
    const r = await safe(() => axios.get(`/api/ios/${kind}`, { params: { backup_path: backups[0].path } }));
    map[kind](r?.data?.items || []);
    setLoading('');
  };

  const loadPlist = async () => {
    if (!backups[0]) return setMsg('Primero crea o detecta un respaldo');
    setLoading('plist');
    const r = await safe(() => axios.get('/api/ios/plist', { params: { backup_path: backups[0].path } }));
    setPlistView(r?.data ? JSON.stringify(r.data, null, 2) : 'Sin contenido plist cargado.');
    setLoading('');
  };

  const loadManifest = async () => {
    if (!backups[0]) return setMsg('Primero crea o detecta un respaldo');
    setLoading('manifest');
    const r = await safe(() => axios.get('/api/ios/manifest', { params: { backup_path: backups[0].path } }));
    setManifestData(r?.data || null);
    setLoading('');
  };

  useEffect(() => { resetCaseView(); load(); }, [activeCase?.id]);

  useEffect(() => {
    const iv = setInterval(async () => {
      try {
        if (selected) {
          const r = await axios.get(`/api/ios/progress/${selected}`);
          setProgress(r.data);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(iv);
  }, [selected]);

  const selectedLabel = useMemo(() => selected ? String(selected) : 'Ninguno', [selected]);

  return (
    <div style={{ padding:24, color:'#e2e8f0', background:'#0b1220', minHeight:'calc(100vh - 60px)' }}>
      <div style={{ maxWidth:1180, margin:'0 auto', display:'grid', gap:16 }}>
        <div style={{ background:'#111827', border:'1px solid #334155', borderRadius:16, padding:20 }}>
          <div style={{ fontSize:28, fontWeight:900, color:'#38bdf8' }}>Panel iOS</div>
          <div style={{ marginTop:8, color:'#94a3b8' }}>Funciones iOS conectadas al backend: pairing, backup, extracción y reportes.</div>
          <div style={{ marginTop:12, display:'flex', gap:8, flexWrap:'wrap' }}>
            <button onClick={load} style={btn(false,'#1f2937')}>Recargar</button>
            <button onClick={pair} style={btn(false,'#2563eb')} disabled={!selected}>Pair</button>
            <button onClick={backup} style={btn(false,'#7c3aed')} disabled={!selected}>Backup</button>
            <button onClick={cancelBackup} style={btn(false,'#b91c1c')} disabled={!selected}>Cancelar</button>
          </div>
        </div>

        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(240px,1fr))', gap:12 }}>
          <div style={card}><div style={{ fontSize:12, color:'#94a3b8' }}>Dispositivos</div><div style={{ fontSize:24, fontWeight:900 }}>{devices.length}</div></div>
          <div style={card}><div style={{ fontSize:12, color:'#94a3b8' }}>Respaldos</div><div style={{ fontSize:24, fontWeight:900 }}>{backups.length}</div></div>
          <div style={card}><div style={{ fontSize:12, color:'#94a3b8' }}>Exportaciones</div><div style={{ fontSize:24, fontWeight:900 }}>{exportsList.length}</div></div>
          <div style={card}><div style={{ fontSize:12, color:'#94a3b8' }}>Seleccionado</div><div style={{ fontSize:18, fontWeight:800, overflow:'hidden', textOverflow:'ellipsis' }}>{selectedLabel}</div></div>
        </div>

        <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
          {nav.map(([k,l]) => <button key={k} onClick={() => setTab(k)} style={btn(tab===k, tab===k ? '#2563eb' : '#1f2937')}>{l}</button>)}
        </div>

        {msg && <div style={{ background:'#111827', border:'1px solid #334155', borderRadius:12, padding:12, color:'#cbd5e1' }}>{msg}{loading ? ` · cargando ${loading}` : ''}</div>}

        {progress && progress.status !== 'idle' && <div style={{ background:'#111827', border:'1px solid #334155', borderRadius:12, padding:12, color:'#cbd5e1' }}>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}><span style={{ color:'#38bdf8', fontWeight:800 }}>⏳ Progreso iOS</span><span style={{ fontSize:12 }}>{progress.percent || 0}%</span></div>
          <div style={{ height:12, background:'#0f172a', border:'1px solid #334155', borderRadius:999, overflow:'hidden' }}><div style={{ width:`${progress.percent || 0}%`, height:'100%', background:'#7c3aed' }} /></div>
          <div style={{ marginTop:8, color:'#94a3b8', fontSize:12 }}>{progress.stage || 'Sin estado'}</div>
          <div style={{ marginTop:6, fontSize:11, color: progress.status === 'cancelled' ? '#fca5a5' : '#94a3b8' }}>Estado: {progress.status || 'idle'}</div>
        </div>}

        {tab === 'live' && (
          <div style={{ display:'grid', gap:12 }}>
            <div style={card}>
              <div style={{ fontWeight:800, color:'#38bdf8', marginBottom:8 }}>Dispositivos detectados</div>
              <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
                {devices.length===0 ? <div style={{ color:'#94a3b8' }}>No hay iPhone detectado.</div> : devices.map((d,i)=><button key={i} onClick={() => setSelected(d)} style={btn(selected===d, selected===d ? '#0f766e' : '#334155')}>{d}</button>)}
              </div>
            </div>
            <div style={card}>
              <div style={{ fontWeight:800, color:'#38bdf8', marginBottom:8 }}>Estado de herramientas</div>
              <div style={{ color:'#94a3b8', fontSize:13 }}>idevice_id: {status?.tools?.idevice_id || 'No encontrado'}</div>
              <div style={{ color:'#94a3b8', fontSize:13 }}>ideviceinfo: {status?.tools?.ideviceinfo || 'No encontrado'}</div>
              <div style={{ color:'#94a3b8', fontSize:13 }}>idevicepair: {status?.tools?.idevicepair || 'No encontrado'}</div>
              <div style={{ color:'#94a3b8', fontSize:13 }}>idevicebackup2: {status?.tools?.idevicebackup2 || 'No encontrado'}</div>
            </div>
          </div>
        )}

        {tab === 'backups' && (
          <div style={{ display:'grid', gap:10 }}>
            <div style={{ color:'#94a3b8' }}>Respaldos detectados: {backups.length}</div>
            <div style={{ display:'grid', gap:8 }}>
              {backups.length===0 ? <div style={{ color:'#94a3b8' }}>No hay respaldos todavía.</div> : backups.map((b,i)=><div key={i} style={card}><div><b>{b.name}</b> — {b.path}</div><div style={{ fontSize:12, color:'#94a3b8', marginTop:6 }}>Info.plist: {String(!!b.has_info_plist)} | Manifest.db: {String(!!b.has_manifest_db)} | Manifest.plist: {String(!!b.has_manifest_plist)} | Status.plist: {String(!!b.has_status_plist)}</div></div>)}
            </div>
            <button onClick={loadManifest} style={btn(false,'#2563eb')}>Cargar manifest</button>
            {manifestData && <pre style={{ whiteSpace:'pre-wrap', background:'#0b1220', border:'1px solid #334155', borderRadius:12, padding:12, minHeight:220, overflow:'auto' }}>{JSON.stringify(manifestData, null, 2)}</pre>}
          </div>
        )}

        {tab === 'selective' && (
          <div style={{ display:'grid', gap:12 }}>
            <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
              <button style={btn(false,'#0f766e')} onClick={() => selectiveBackup('photos')}>Exportar fotos</button>
              <button style={btn(false,'#7c3aed')} onClick={() => selectiveBackup('messages')}>Exportar mensajes</button>
              <button style={btn(false,'#1d4ed8')} onClick={() => selectiveBackup('sqlite')}>Exportar SQLite</button>
              <button style={btn(false,'#b45309')} onClick={() => selectiveBackup('plist')}>Exportar plist</button>
            </div>
            <div style={card}>
              <div style={{fontWeight:800, marginBottom:8}}>Exportaciones generadas</div>
              {(exportsList || []).length === 0 ? <div style={{opacity:.8}}>Sin exportaciones aún</div> : <div style={{display:'grid', gap:6}}>{exportsList.map((x,i)=><div key={i} style={{fontSize:13}}>{x.name} — {x.has_zip ? x.zip_path : x.path}</div>)}</div>}
            </div>
          </div>
        )}

        {tab === 'photos' && <div style={{ display:'grid', gap:10 }}><button onClick={() => loadArtifacts('photos')} style={btn(false,'#0f766e')}>Cargar fotos</button><div style={{ display:'grid', gap:8 }}>{photos.length===0 ? <div style={{ color:'#94a3b8' }}>Sin fotos cargadas.</div> : photos.map((x,i)=><div key={i} style={card}>{x.path || x.name || JSON.stringify(x)}</div>)}</div></div>}
        {tab === 'messages' && <div style={{ display:'grid', gap:10 }}><button onClick={() => loadArtifacts('messages')} style={btn(false,'#0f766e')}>Cargar mensajes</button><div style={{ display:'grid', gap:8 }}>{messages.length===0 ? <div style={{ color:'#94a3b8' }}>Sin mensajes cargados.</div> : messages.map((x,i)=><div key={i} style={card}>{x.text || x.body || x.path || JSON.stringify(x)}</div>)}</div></div>}
        {tab === 'sqlite' && <div style={{ display:'grid', gap:10 }}><button onClick={() => loadArtifacts('sqlite')} style={btn(false,'#0f766e')}>Cargar SQLite</button><div style={{ display:'grid', gap:8 }}>{sqliteItems.length===0 ? <div style={{ color:'#94a3b8' }}>Sin bases encontradas.</div> : sqliteItems.map((x,i)=><div key={i} style={card}>{x.path || x.real_path || JSON.stringify(x)}</div>)}</div></div>}
        {tab === 'plist' && <div style={{ display:'grid', gap:10 }}><button onClick={loadPlist} style={btn(false,'#2563eb')}>Cargar plist</button><pre style={{ whiteSpace:'pre-wrap', background:'#0b1220', border:'1px solid #334155', borderRadius:12, padding:12, minHeight:220, overflow:'auto' }}>{plistView || 'Sin contenido plist cargado.'}</pre></div>}
        {tab === 'reports' && <div style={{ display:'grid', gap:10 }}><div style={card}><div style={{ fontWeight:800, marginBottom:8 }}>Estado del módulo iOS</div><div style={{ color:'#94a3b8', fontSize:12 }}>Dispositivos: {devices.length}</div><div style={{ color:'#94a3b8', fontSize:12 }}>Respaldos: {backups.length}</div><div style={{ color:'#94a3b8', fontSize:12 }}>Exportaciones: {exportsList.length}</div></div></div>}
      </div>
    </div>
  );
}
