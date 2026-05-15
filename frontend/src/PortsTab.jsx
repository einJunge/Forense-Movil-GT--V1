import React from 'react';

export default function PortsTab({ ports, loadPorts, loadingF, selDevice }) {
  return <>
    <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:14 }}>
      <h2 style={{ color:'#38bdf8', fontSize:14, margin:0 }}>🌐 Puertos de Red Abiertos</h2>
      {selDevice && <span style={{ fontSize:11, color:'#64748b' }}>{selDevice.adb_serial}</span>}
      <button
        style={{ background:'#2563eb', color:'#fff', border:'none', borderRadius:8, padding:'8px 16px', cursor:'pointer', fontWeight:'bold', fontSize:12 }}
        onClick={loadPorts} disabled={loadingF==='ports'}>
        {loadingF==='ports' ? '⏳ Escaneando...' : '🔍 Escanear puertos'}
      </button>
    </div>

    {!ports
      ? <div style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:24, color:'#64748b', textAlign:'center' }}>
          Haz clic en "Escanear puertos" para ver conexiones activas.
        </div>
      : <>
        {ports.suspicious_ports.length > 0
          ? ports.suspicious_ports.map((sp, i) => (
            <div key={i} style={{ background:'#450a0a', border:'1px solid #dc2626', borderRadius:10, padding:16, marginBottom:12 }}>
              <div style={{ color:'#fca5a5', fontWeight:'bold', fontSize:14, marginBottom:8 }}>
                🔴 Puerto {sp.port} — {sp.reason}
              </div>
              <div style={{ color:'#94a3b8', fontSize:11, fontFamily:'monospace', marginBottom:12 }}>{sp.raw_line}</div>

              {sp.processes && sp.processes.map((proc, j) => (
                <div key={j} style={{ background:'#1e293b', borderRadius:8, padding:12, marginBottom:8 }}>
                  <div style={{ display:'flex', flexWrap:'wrap', gap:16, fontSize:12 }}>
                    <span>🔑 UID: <b style={{color:'#fbbf24'}}>{proc.uid || 'N/A'}</b></span>
                    <span>⚙️ PID: <b style={{color:'#60a5fa'}}>{proc.pid || 'N/A'}</b></span>
                    <span>📛 Proceso: <b style={{color:'#f87171'}}>{proc.process_name || 'Desconocido'}</b></span>
                  </div>
                  {proc.cmdline && (
                    <div style={{ marginTop:8, color:'#94a3b8', fontSize:11, fontFamily:'monospace', background:'#0f172a', borderRadius:6, padding:'6px 10px' }}>
                      $ {proc.cmdline}
                    </div>
                  )}
                  {proc.packages && proc.packages.length > 0 && (
                    <div style={{ marginTop:8 }}>
                      <div style={{ color:'#64748b', fontSize:11, marginBottom:4 }}>📦 App(s) asociadas al UID:</div>
                      {proc.packages.map((pkg, k) => (
                        <span key={k} style={{ background:'#7f1d1d', color:'#fca5a5', borderRadius:6, padding:'2px 10px', fontSize:11, marginRight:6, display:'inline-block', marginBottom:4 }}>
                          {pkg}
                        </span>
                      ))}
                    </div>
                  )}
                  {(!proc.packages || proc.packages.length === 0) && (
                    <div style={{ marginTop:6, fontSize:11, color:'#64748b' }}>
                      ⚠️ No se encontró paquete asociado — puede ser un proceso del sistema o root.
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))
          : <div style={{ background:'#0f172a', border:'1px solid #2563eb', borderRadius:10, padding:16, marginBottom:12, color:'#93c5fd' }}>
              ✅ No se detectaron puertos sospechosos.
            </div>
        }

        <div style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:16 }}>
          <div style={{ color:'#64748b', fontSize:11, marginBottom:8 }}>Conexiones activas ({ports.all_connections?.length || 0}):</div>
          <div style={{ maxHeight:250, overflowY:'auto' }}>
            <table style={{ width:'100%', fontSize:11, borderCollapse:'collapse' }}>
              <thead>
                <tr style={{ color:'#475569', borderBottom:'1px solid #334155' }}>
                  <th style={{textAlign:'left', padding:'4px 8px'}}>Puerto Local</th>
                  <th style={{textAlign:'left', padding:'4px 8px'}}>Puerto Remoto</th>
                  <th style={{textAlign:'left', padding:'4px 8px'}}>Estado</th>
                  <th style={{textAlign:'left', padding:'4px 8px'}}>UID</th>
                </tr>
              </thead>
              <tbody>
                {(ports.all_connections||[]).map((c,i) => (
                  <tr key={i} style={{ borderBottom:'1px solid #1e293b', color:'#94a3b8' }}>
                    <td style={{padding:'3px 8px'}}>{c.local_port}</td>
                    <td style={{padding:'3px 8px'}}>{c.remote_port}</td>
                    <td style={{padding:'3px 8px', color: c.state==='ESTABLISHED'?'#4ade80': c.state==='LISTEN'?'#60a5fa':'#94a3b8'}}>{c.state}</td>
                    <td style={{padding:'3px 8px'}}>{c.uid}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </>
    }
  </>;
}
