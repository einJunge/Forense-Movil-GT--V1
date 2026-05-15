import React, { useEffect, useState } from 'react';
import axios from 'axios';
import AndroidApp from './AndroidApp.jsx';
import IOSPanel from './iOSPanel.jsx';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: '' };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error: String(error || '') };
  }
  componentDidCatch(error, info) {
    console.error(error, info);
  }
  render() {
    if (this.state.hasError) return this.props.fallback(this.state.error);
    return this.props.children;
  }
}

function BrandHeader() {
  return (
    <div style={{ background:'#060d14', borderBottom:'2px solid #2563eb', padding:'10px 24px', display:'flex', alignItems:'center', gap:14, boxShadow:'0 2px 20px rgba(37,99,235,0.16)' }}>
      <img id="hs-logo" src="/assets/branding/brand-logo.png" alt="Hacking Seguro GT" width={52} height={52} style={{ borderRadius:8, objectFit:'contain', flexShrink:0 }} onError={(e)=>{ e.currentTarget.style.display='none'; const fb=document.getElementById('hs-logo-fallback'); if (fb) fb.style.display='flex'; }} />
      <div id="hs-logo-fallback" style={{ display:'none', width:52, height:52, background:'#0B0B0B', border:'2px solid #2563eb', borderRadius:8, alignItems:'center', justifyContent:'center', fontFamily:'monospace', fontWeight:900, fontSize:20, flexShrink:0, letterSpacing:-1 }}>
        <span style={{ color:'#fff' }}>H</span><span style={{ color:'#2563eb' }}>S</span>
      </div>
      <div style={{ display:'flex', flexDirection:'column', gap:3 }}>
        <div style={{ display:'flex', alignItems:'center', gap:9 }}>
          <span style={{ fontSize:18, fontWeight:900, color:'#FFFFFF', fontFamily:'monospace', letterSpacing:1, textShadow:'0 0 10px rgba(37,99,235,0.28)' }}>Forense Móvil GT</span>
          <span style={{ background:'#2563eb', color:'#fff', fontSize:10, fontWeight:900, padding:'2px 8px', borderRadius:20, fontFamily:'monospace', letterSpacing:1 }}>V2</span>
        </div>
        <span style={{ fontSize:11, fontFamily:'monospace', opacity:0.9, letterSpacing:0.4 }}><span style={{ color:'#6b7280' }}>Creado por </span><strong style={{ color:'#fff' }}>Marcos Hernández</strong><span style={{ color:'#6b7280' }}> · </span><em style={{ color:'#60a5fa' }}>"Der Designer"</em></span>
      </div>
      <div style={{ flex:1 }} />
      
      {/* BOTÓN DE PAYPAL */}
      <a href="https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=sorayav1616@gmail.com&item_name=Apoyo+al+Proyecto+Forense+GT&currency_code=USD" target="_blank" rel="noreferrer" style={{ textDecoration:'none' }}>
        <button style={{ background:'#ffc439', color:'#003087', border:'none', borderRadius:20, padding:'6px 16px', fontSize:11, fontWeight:900, cursor:'pointer', display:'flex', alignItems:'center', gap:6, boxShadow:'0 4px 12px rgba(255,196,57,0.2)' }}>
          <span style={{ fontSize:14 }}>💙</span> Donar con PayPal
        </button>
      </a>

      <div style={{ fontSize:10, fontFamily:'monospace', textAlign:'right', lineHeight:1.7, marginLeft:12 }}><div style={{ color:'#60a5fa', fontWeight:700, letterSpacing:1 }}>HACKING SEGURO GT</div><div style={{ color:'#4b5563' }}>Aprende · Practica · Protege</div></div>
    </div>
  );
}

function Footer() {
  return (
    <div style={{ background:'#060d14', borderTop:'1px solid #1e293b', padding:'20px 24px', textAlign:'center', display:'flex', flexDirection:'column', alignItems:'center', gap:10 }}>
      <div style={{ display:'flex', alignItems:'center', gap:12 }}>
        <a href="https://www.facebook.com/hackingseguro502" target="_blank" rel="noreferrer" style={{ color:'#1877F2', textDecoration:'none', display:'flex', alignItems:'center', gap:8, fontSize:14, fontWeight:700 }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
          Sigue a Hacking Seguro 502
        </a>
      </div>
      <div style={{ color:'#4b5563', fontSize:11, fontFamily:'monospace' }}>
        © 2024 Forense Móvil GT · Herramienta de Análisis Técnico Forense · Guatemala
      </div>
    </div>
  );
}

function Dashboard({ activeCase }) {
  const [stats, setStats] = useState({ scans:0, findings:0, events:0, audit:[] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [sc, fi, ev, au] = await Promise.all([
          axios.get('/api/scans'),
          axios.get('/api/findings'),
          axios.get('/api/events'),
          axios.get(`/api/reports/cases/${activeCase.id}/audit`)
        ]);
        const caseScans = sc.data.filter(s => s.case_id === activeCase.id);
        const scanIds = new Set(caseScans.map(s => s.id));
        setStats({
          scans: caseScans.length,
          findings: fi.data.filter(f => scanIds.has(f.scan_id)).length,
          events: ev.data.filter(e => scanIds.has(e.scan_id)).length,
          audit: au.data
        });
      } catch (e) {}
      setLoading(false);
    };
    load();
  }, [activeCase.id]);

  const card = { background:'#111827', border:'1px solid #1e293b', borderRadius:16, padding:20 };
  const statBox = (label, val, color) => (
    <div style={{ ...card, flex:1, textAlign:'center', borderTop:`4px solid ${color}` }}>
      <div style={{ fontSize:12, color:'#94a3b8', textTransform:'uppercase', letterSpacing:1 }}>{label}</div>
      <div style={{ fontSize:32, fontWeight:900, color:'#fff', marginTop:8 }}>{val}</div>
    </div>
  );

  return (
    <div style={{ padding:24, display:'grid', gap:20 }}>
      <div style={{ display:'flex', gap:16 }}>
        {statBox('Escaneos', stats.scans, '#2563eb')}
        {statBox('Hallazgos', stats.findings, '#dc2626')}
        {statBox('Eventos', stats.events, '#0f766e')}
      </div>
      
      <div style={{ ...card }}>
        <div style={{ fontWeight:800, color:'#38bdf8', marginBottom:16, display:'flex', justifyContent:'space-between' }}>
          <span>📜 Cadena de Custodia (Auditoría Inmutable)</span>
          <span style={{ fontSize:10, color:'#94a3b8' }}>Verificación SHA-256 Activa</span>
        </div>
        <div style={{ maxHeight:300, overflow:'auto', fontSize:12 }}>
          {stats.audit.length === 0 ? <div style={{ color:'#4b5563' }}>Sin registros de auditoría.</div> : (
            <table style={{ width:'100%', borderCollapse:'collapse' }}>
              <thead>
                <tr style={{ textAlign:'left', borderBottom:'1px solid #334155', color:'#94a3b8' }}>
                  <th style={{ padding:8 }}>Fecha</th>
                  <th style={{ padding:8 }}>Acción</th>
                  <th style={{ padding:8 }}>Investigador</th>
                  <th style={{ padding:8 }}>Hash Integridad</th>
                </tr>
              </thead>
              <tbody>
                {stats.audit.map((a,i) => (
                  <tr key={i} style={{ borderBottom:'1px solid #1e293b' }}>
                    <td style={{ padding:8, color:'#cbd5e1' }}>{new Date(a.timestamp).toLocaleString()}</td>
                    <td style={{ padding:8 }}><span style={{ background:'#1e3a5f', color:'#93c5fd', padding:'2px 6px', borderRadius:4 }}>{a.action}</span></td>
                    <td style={{ padding:8, color:'#cbd5e1' }}>{a.investigator}</td>
                    <td style={{ padding:8, color:'#64748b', fontFamily:'monospace' }}>{a.hash.substring(0,16)}...</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function CaseGate({ onSelectCase }) {
  const [cases, setCases] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [form, setForm] = useState({ name:'', investigator:'', description:'', status:'open' });

  const shell = { background:'#0f172a', minHeight:'calc(100vh - 76px)', color:'#e2e8f0', fontFamily:'monospace', padding:'24px', boxSizing:'border-box' };
  const card = { background:'#111827', border:'1px solid #1f2937', borderRadius:16, padding:'20px', maxWidth:980, margin:'0 auto 18px auto', boxSizing:'border-box', overflow:'hidden' };
  const input = { width:'100%', maxWidth:'100%', background:'#0b1220', color:'#fff', border:'1px solid #334155', borderRadius:10, padding:'11px 12px', outline:'none', boxSizing:'border-box' };
  const panel = { background:'#0b1220', border:'1px solid #334155', borderRadius:12, padding:16, boxSizing:'border-box', minWidth:0 };
  const btn = (color='#2563eb', text='#fff') => ({ background:color, color:text, border:'1px solid '+color, borderRadius:10, padding:'10px 14px', cursor:'pointer', fontWeight:800, fontFamily:'monospace', boxSizing:'border-box', minHeight:42, whiteSpace:'nowrap' });

  const loadCases = async () => {
    try {
      const r = await axios.get('/api/cases');
      const list = Array.isArray(r.data) ? r.data : [];
      setCases(list);
      if (!selectedCaseId && list.length) setSelectedCaseId(String(list[0].id));
    } catch (e) {
      setMsg('❌ No se pudieron cargar los casos');
    }
  };

  useEffect(() => { loadCases(); }, []);

  const createCase = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return setMsg('❌ Debes ingresar el nombre del caso');
    setLoading(true);
    try {
      const r = await axios.post('/api/cases', { name:form.name.trim(), investigator:form.investigator.trim(), description:form.description.trim(), status:form.status || 'open' });
      const created = r.data;
      setMsg(`✅ Caso creado: ${created.name}`);
      setForm({ name:'', investigator:'', description:'', status:'open' });
      await loadCases();
      setSelectedCaseId(String(created.id));
    } catch (e) {
      setMsg('❌ ' + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const enterCase = () => {
    const current = cases.find(c => String(c.id) === String(selectedCaseId));
    if (!current) return setMsg('❌ Debes seleccionar o crear un caso');
    onSelectCase(current);
  };

  return (
    <div style={shell}>
      <div style={{ ...card, border:'1px solid #2563eb' }}>
        <div style={{ fontSize:18, fontWeight:900, color:'#fff', marginBottom:8 }}>🗂️ Gestión de casos</div>
        <div style={{ fontSize:12, color:'#94a3b8', marginBottom:14 }}>Antes de usar Android o iOS, debes crear o seleccionar un caso. Todo el trabajo quedará vinculado al expediente elegido.</div>
        {msg ? <div style={{ background:'#0b1220', border:'1px solid #334155', color:'#cbd5e1', padding:'10px 12px', borderRadius:10, marginBottom:12 }}>{msg}</div> : null}
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(320px, 1fr))', gap:18, alignItems:'start' }}>
          <form onSubmit={createCase} style={{ ...panel, display:'grid', gap:10 }}>
            <div style={{ color:'#93c5fd', fontSize:13, fontWeight:700 }}>Crear caso nuevo</div>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name:e.target.value }))} placeholder="Nombre del caso" style={input} />
            <input value={form.investigator} onChange={e => setForm(f => ({ ...f, investigator:e.target.value }))} placeholder="Investigador responsable" style={input} />
            <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description:e.target.value }))} placeholder="Descripción del caso" rows={4} style={{ ...input, resize:'vertical' }} />
            <select value={form.status} onChange={e => setForm(f => ({ ...f, status:e.target.value }))} style={input}>
              <option value="open">Abierto</option>
              <option value="in_progress">En progreso</option>
              <option value="closed">Cerrado</option>
            </select>
            <div style={{ display:'flex', gap:8, flexWrap:'wrap', alignItems:'stretch' }}>
              <button type="submit" disabled={loading} style={{ ...btn('#2563eb','#fff'), flex:'1 1 220px' }}>{loading ? '⏳ Guardando...' : '💾 Crear caso'}</button>
              <button type="button" onClick={loadCases} style={{ ...btn('#0f766e','#fff'), flex:'1 1 180px' }}>🔄 Actualizar</button>
            </div>
          </form>
          <div style={{ ...panel, display:'grid', gap:10 }}>
            <div style={{ color:'#93c5fd', fontSize:13, fontWeight:700 }}>Seleccionar caso existente</div>
            <select value={selectedCaseId} onChange={e => setSelectedCaseId(e.target.value)} style={input}>
              <option value="">Selecciona un caso...</option>
              {cases.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <button type="button" onClick={enterCase} style={{ ...btn('#2563eb','#fff'), width:'100%' }}>🚀 Entrar a la herramienta</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState('dashboard'); // 'dashboard', 'android', 'ios'
  const [activeCase, setActiveCase] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportMsg, setReportMsg] = useState('');
  const [showTemplates, setShowTemplates] = useState(false);

  const S = { background:'#0f172a', minHeight:'100vh', color:'#e2e8f0', fontFamily:'monospace', display:'flex', flexDirection:'column' };
  const btn = (active) => ({ background: active ? '#2563eb' : '#0f172a', color: '#fff', border: active ? '1px solid #2563eb' : '1px solid #1e293b', borderRadius:8, padding:'8px 16px', cursor:'pointer', fontWeight:'bold', fontSize:12, transition:'all 0.18s ease' });

  const generatePericial = async (template = 'full') => {
    if (!activeCase?.id) return;
    setReportLoading(true);
    setReportMsg(`⏳ Generando ${template}...`);
    setShowTemplates(false);
    try {
      await axios.post(`/api/reports/cases/${activeCase.id}/pericial`, { 
        template,
        device_type: 'mobile'
      });
      setReportMsg('✅ Listo');
      setTimeout(() => {
        window.open(`/api/reports/cases/${activeCase.id}/pericial/latest-pdf`, '_blank');
        setReportMsg('');
      }, 1500);
    } catch (e) {
      setReportMsg('❌ Error');
      setTimeout(() => setReportMsg(''), 3000);
    }
    setReportLoading(false);
  };

  return (
    <div style={S}>
      <BrandHeader />
      <div style={{ flex:1 }}>
        {!activeCase ? (
          <CaseGate onSelectCase={setActiveCase} />
        ) : (
          <>
            <div style={{ padding:'8px 24px', borderBottom:'1px solid #1e293b', background:'#111827', display:'flex', gap:8, flexWrap:'wrap', alignItems:'center' }}>
              <button style={btn(view === 'dashboard')} onClick={() => setView('dashboard')}>📊 Dashboard</button>
              <button style={btn(view === 'android')} onClick={() => setView('android')}>🤖 Android</button>
              <button style={btn(view === 'ios')} onClick={() => setView('ios')}>🍎 iOS</button>
              
              <div style={{ display:'flex', alignItems:'center', gap:8, marginLeft:12, borderLeft:'1px solid #1e293b', paddingLeft:12 }}>
                <span style={{ fontSize:11, color:'#94a3b8' }}>Caso:</span>
                <span style={{ fontSize:11, background:'#1e3a5f', color:'#93c5fd', borderRadius:6, padding:'3px 10px', fontWeight:'bold' }}>🗂️ {activeCase.name}</span>
              </div>

              <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:8, position:'relative' }}>
                {reportMsg && <span style={{ fontSize:10, color:'#94a3b8' }}>{reportMsg}</span>}
                
                <button 
                  onClick={() => setShowTemplates(!showTemplates)}
                  disabled={reportLoading}
                  style={{ background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontWeight: 'bold', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, boxShadow: '0 0 15px rgba(124, 58, 237, 0.3)' }}
                >
                  📄 Informe Pericial ▾
                </button>

                {showTemplates && (
                  <div style={{ position:'absolute', top:'100%', right:0, marginTop:8, background:'#111827', border:'1px solid #334155', borderRadius:8, padding:8, zIndex:100, display:'grid', gap:4, width:200 }}>
                    <button onClick={() => generatePericial('full')} style={{ ...btn(false), textAlign:'left' }}>📑 Informe Completo</button>
                    <button onClick={() => generatePericial('executive')} style={{ ...btn(false), textAlign:'left' }}>👔 Resumen Ejecutivo</button>
                    <button onClick={() => generatePericial('technical')} style={{ ...btn(false), textAlign:'left' }}>🛠️ Reporte Técnico</button>
                  </div>
                )}

                <button style={{ ...btn(false) }} onClick={() => setActiveCase(null)}>↩ Salir</button>
              </div>
            </div>

            {view === 'dashboard' && <Dashboard activeCase={activeCase} />}
            {view === 'android' && <AndroidApp activeCase={activeCase} />}
            {view === 'ios' && (
              <ErrorBoundary fallback={(error) => <div style={{ padding:24 }}><div style={{ background:'#111827', border:'1px solid #334155', borderRadius:16, padding:20 }}>Error iOS: {error}</div></div>}>
                <IOSPanel activeCase={activeCase} />
              </ErrorBoundary>
            )}
          </>
        )}
      </div>
      <Footer />
    </div>
  );
}
