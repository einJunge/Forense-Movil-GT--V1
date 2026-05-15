import React, { useRef, useEffect, useState } from 'react';
import axios from 'axios';

const COMMAND_GROUPS = [
  {
    label: '📋 Sistema',
    color: '#1e3a5f',
    cmds: [
      { label: 'Info del sistema',   cmd: 'uname -a' },
      { label: 'Usuario actual',     cmd: 'id' },
      { label: 'Versión Android',    cmd: 'getprop ro.build.version.release' },
      { label: 'Modelo',             cmd: 'getprop ro.product.model' },
      { label: 'CPU info',           cmd: 'cat /proc/cpuinfo | head -20' },
      { label: 'Memoria RAM',        cmd: 'cat /proc/meminfo | head -10' },
      { label: 'Espacio disco',      cmd: 'df -h' },
      { label: 'Uptime',             cmd: 'uptime' },
      { label: 'Variables de entorno', cmd: 'env' },
    ]
  },
  {
    label: '📦 Apps & Paquetes',
    color: '#1e3a5f',
    cmds: [
      { label: 'Listar apps terceros',   cmd: 'pm list packages -3' },
      { label: 'Listar apps sistema',    cmd: 'pm list packages -s' },
      { label: 'Apps deshabilitadas',    cmd: 'pm list packages -d' },
      { label: 'Abrir app (editar pkg)', cmd: 'am start -n com.paquete/.MainActivity' },
      { label: 'Forzar cierre app',      cmd: 'am force-stop com.paquete' },
      { label: 'Instalar APK',           cmd: 'pm install /sdcard/app.apk' },
      { label: 'Desinstalar app',        cmd: 'pm uninstall com.paquete' },
      { label: 'Info de una app',        cmd: 'dumpsys package com.paquete' },
    ]
  },
  {
    label: '🌐 Red',
    color: '#1e3a5f',
    cmds: [
      { label: 'IPs del dispositivo',   cmd: 'ip addr show' },
      { label: 'Tabla de rutas',        cmd: 'ip route' },
      { label: 'Puertos en escucha',    cmd: 'cat /proc/net/tcp' },
      { label: 'Conexiones activas',    cmd: 'ss -tp 2>/dev/null || netstat -tp 2>/dev/null' },
      { label: 'DNS configurado',       cmd: 'getprop net.dns1 && getprop net.dns2' },
      { label: 'WiFi conectado a',      cmd: 'getprop dhcp.wlan0.dns1' },
      { label: 'Ping a Google',         cmd: 'ping -c 3 8.8.8.8' },
    ]
  },
  {
    label: '📁 Archivos',
    color: '#1e3a5f',
    cmds: [
      { label: 'Listar /sdcard/',            cmd: 'ls -la /sdcard/' },
      { label: 'Listar /sdcard/DCIM/',       cmd: 'ls -la /sdcard/DCIM/Camera/' },
      { label: 'Listar /sdcard/Download/',   cmd: 'ls -la /sdcard/Download/' },
      { label: 'Listar /sdcard/WhatsApp/',   cmd: 'ls -la /sdcard/WhatsApp/Media/' },
      { label: 'Buscar APKs en sdcard',      cmd: 'find /sdcard -name "*.apk" 2>/dev/null' },
      { label: 'Archivos recientes',         cmd: 'find /sdcard -newer /sdcard/Android -type f 2>/dev/null | head -20' },
      { label: 'Tamaño carpetas',            cmd: 'du -sh /sdcard/*' },
    ]
  },
  {
    label: '📸 Cámara & Media',
    color: '#3b0764',
    cmds: [
      { label: 'Tomar foto (cámara trasera)',  cmd: 'am start -a android.media.action.IMAGE_CAPTURE' },
      { label: 'Foto silenciosa (screencap)', cmd: 'screencap -p /sdcard/captura_$(date +%s).png' },
      { label: 'Grabar pantalla 10s',         cmd: 'screenrecord --time-limit 10 /sdcard/grabacion_$(date +%s).mp4' },
      { label: 'Ver fotos en DCIM',           cmd: 'ls -lht /sdcard/DCIM/Camera/ | head -20' },
      { label: 'Sacar última foto',           cmd: 'ls -t /sdcard/DCIM/Camera/*.jpg 2>/dev/null | head -1' },
      { label: 'Reproducir audio',            cmd: 'am start -a android.intent.action.VIEW -d file:///sdcard/audio.mp3' },
    ]
  },
  {
    label: '💬 Mensajes & Contactos',
    color: '#3b0764',
    cmds: [
      { label: 'Exportar SMS (DB)',      cmd: 'cp /data/data/com.android.providers.telephony/databases/mmssms.db /sdcard/ 2>/dev/null && echo OK' },
      { label: 'Exportar contactos DB', cmd: 'cp /data/data/com.android.providers.contacts/databases/contacts2.db /sdcard/ 2>/dev/null && echo OK' },
      { label: 'Ver llamadas recientes', cmd: 'content query --uri content://call_log/calls --projection number,date,duration,type | head -30' },
      { label: 'Enviar SMS (prueba)',    cmd: 'am start -a android.intent.action.SENDTO -d smsto:+50212345678 --es sms_body "Test"' },
    ]
  },
  {
    label: '⚙️ Procesos',
    color: '#1e293b',
    cmds: [
      { label: 'Todos los procesos',   cmd: 'ps -A' },
      { label: 'Procesos por CPU',     cmd: 'top -n 1 -b' },
      { label: 'Matar proceso (PID)',  cmd: 'kill -9 PID_AQUI' },
      { label: 'Detalles proceso PID', cmd: 'cat /proc/PID_AQUI/cmdline' },
      { label: 'Servicios corriendo',  cmd: 'dumpsys activity services | head -40' },
      { label: 'Broadcasts registrados', cmd: 'dumpsys activity broadcasts | head -40' },
    ]
  },
  {
    label: '🔐 Seguridad & Root',
    color: '#450a0a',
    cmds: [
      { label: 'Verificar root',           cmd: 'su -c id 2>/dev/null || echo "Sin root"' },
      { label: 'Binarios root instalados', cmd: 'which su; which busybox; ls /system/xbin/ 2>/dev/null' },
      { label: 'SELinux estado',           cmd: 'getenforce 2>/dev/null || sestatus 2>/dev/null' },
      { label: 'Cuentas en sistema',       cmd: 'cat /data/system/accounts.db 2>/dev/null || content query --uri content://com.android.contacts/accounts' },
      { label: 'Permisos peligrosos app',  cmd: 'dumpsys package com.paquete | grep -A2 "dangerous"' },
      { label: 'Historial ADB',            cmd: 'cat /data/misc/adb/adb_keys 2>/dev/null' },
      { label: 'Claves ADB autorizadas',   cmd: 'cat /data/misc/adb/adb_keys' },
    ]
  },
  {
    label: '📲 Intent & UI',
    color: '#1e293b',
    cmds: [
      { label: 'Abrir URL en navegador',    cmd: 'am start -a android.intent.action.VIEW -d https://google.com' },
      { label: 'Abrir configuración WiFi',  cmd: 'am start -a android.settings.WIFI_SETTINGS' },
      { label: 'Abrir configuración dev',   cmd: 'am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS' },
      { label: 'Captura de pantalla',       cmd: 'screencap -p /sdcard/screen_$(date +%s).png && echo Guardado' },
      { label: 'Bloquear pantalla',         cmd: 'input keyevent 26' },
      { label: 'Desbloquear pantalla',      cmd: 'input keyevent 82' },
      { label: 'Simular tap (x,y)',         cmd: 'input tap 500 800' },
      { label: 'Escribir texto',            cmd: 'input text "Hola mundo"' },
      { label: 'Botón Back',               cmd: 'input keyevent 4' },
      { label: 'Botón Home',               cmd: 'input keyevent 3' },
    ]
  },
];

export default function ShellTab({ selDevice }) {
  const [history, setHistory] = useState([
    { type:'info', text:'# Shell ADB — Forense Móvil GT v2.1'},
    { type:'info', text:'# Selecciona comandos del panel o escribe abajo'},
  ]);
  const [cmd, setCmd]               = useState('');
  const [cmdHistory, setCmdHistory] = useState([]);
  const [histIdx, setHistIdx]       = useState(-1);
  const [openGroup, setOpenGroup]   = useState(null);
  const shellRef = useRef(null);

  useEffect(() => { if (shellRef.current) shellRef.current.scrollTop = shellRef.current.scrollHeight; }, [history]);

  const run = async (command) => {
    if (!command.trim() || !selDevice) return;
    setHistory(h => [...h, { type:'cmd', text:`$ ${command}` }]);
    setCmdHistory(h => [command, ...h.filter(c => c !== command)].slice(0, 50));
    setHistIdx(-1);
    setCmd('');
    try {
      const r = await axios.post('/api/forensics/shell', { serial: selDevice.adb_serial, command }, { timeout: 30000 });
      const out = r.data.output || '(sin output)';
      setHistory(h => [...h, { type:'out', text: out }]);
    } catch(e) {
      setHistory(h => [...h, { type:'err', text: '❌ ' + (e.response?.data?.detail || e.message) }]);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter') { run(cmd); }
    if (e.key === 'ArrowUp') {
      const idx = Math.min(histIdx + 1, cmdHistory.length - 1);
      setHistIdx(idx); setCmd(cmdHistory[idx] || '');
    }
    if (e.key === 'ArrowDown') {
      const idx = Math.max(histIdx - 1, -1);
      setHistIdx(idx); setCmd(idx === -1 ? '' : cmdHistory[idx] || '');
    }
  };

  const S = {
    card: { background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:12, marginBottom:8 },
    btn:  (c='#2563eb') => ({ background:c, color:'#fff', border:'none', borderRadius:8, padding:'7px 14px', cursor:'pointer', fontWeight:'bold', fontSize:12 }),
    tag:  (c='#1e293b') => ({ background:c, color:'#94a3b8', border:'1px solid #334155', borderRadius:6, padding:'4px 10px', fontSize:11, cursor:'pointer', whiteSpace:'nowrap' }),
  };

  if (!selDevice) return (
    <div style={{ ...S.card, color:'#64748b', padding:32, textAlign:'center' }}>
      Selecciona un dispositivo en la pestaña 📱 Dispositivos.
    </div>
  );

  return (
    <div style={{ display:'flex', gap:16, height:'calc(100vh - 160px)' }}>

      {/* ── PANEL LATERAL DE COMANDOS ── */}
      <div style={{ width:260, overflowY:'auto', flexShrink:0 }}>
        {COMMAND_GROUPS.map((group, gi) => (
          <div key={gi} style={{ marginBottom:6 }}>
            <div
              onClick={() => setOpenGroup(openGroup === gi ? null : gi)}
              style={{ background: group.color, border:'1px solid #334155', borderRadius:8, padding:'8px 12px', cursor:'pointer', display:'flex', justifyContent:'space-between', alignItems:'center', fontSize:13, fontWeight:'bold', color:'#e2e8f0', userSelect:'none' }}>
              {group.label}
              <span style={{ color:'#64748b', fontSize:10 }}>{openGroup === gi ? '▲' : '▼'}</span>
            </div>
            {openGroup === gi && (
              <div style={{ background:'#0f172a', border:'1px solid #1e293b', borderRadius:'0 0 8px 8px', overflow:'hidden' }}>
                {group.cmds.map((c, ci) => (
                  <div key={ci}
                    onClick={() => setCmd(c.cmd)}
                    onDoubleClick={() => run(c.cmd)}
                    style={{ padding:'7px 14px', cursor:'pointer', fontSize:12, color:'#94a3b8', borderBottom:'1px solid #0f172a', display:'flex', justifyContent:'space-between', alignItems:'center' }}
                    onMouseEnter={e => e.currentTarget.style.background='#1e293b'}
                    onMouseLeave={e => e.currentTarget.style.background='transparent'}>
                    <span>{c.label}</span>
                    <span style={{ color:'#475569', fontSize:10 }}>▶</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ── TERMINAL ── */}
      <div style={{ flex:1, display:'flex', flexDirection:'column', minWidth:0 }}>
        {/* Device info bar */}
        <div style={{ background:'#0f172a', border:'1px solid #1e293b', borderRadius:'8px 8px 0 0', padding:'6px 14px', display:'flex', gap:16, fontSize:11 }}>
          <span style={{ color:'#4ade80' }}>● {selDevice.adb_serial}</span>
          <span style={{ color:'#64748b' }}>{selDevice.manufacturer} {selDevice.model}</span>
          <span style={{ color:'#64748b' }}>Android {selDevice.android_version}</span>
          <span style={{ color: selDevice.root_status ? '#f87171':'#64748b' }}>
            {selDevice.root_status ? '⚠️ ROOTED' : 'No root'}
          </span>
          <span style={{ marginLeft:'auto', color:'#334155', fontSize:10 }}>Click = editar | Doble click = ejecutar directo</span>
        </div>

        {/* Output */}
        <div ref={shellRef} style={{ flex:1, background:'#000', border:'1px solid #1e293b', padding:14, overflowY:'auto', fontFamily:'monospace', fontSize:13, lineHeight:1.6 }}>
          {history.map((h, i) => (
            <div key={i} style={{ marginBottom:2, color: h.type==='cmd' ? '#38bdf8' : h.type==='err' ? '#f87171' : h.type==='info' ? '#475569' : '#e2e8f0', whiteSpace:'pre-wrap', wordBreak:'break-all' }}>
              {h.text}
            </div>
          ))}
        </div>

        {/* Input */}
        <div style={{ background:'#0f172a', border:'1px solid #1e293b', borderRadius:'0 0 8px 8px', padding:'8px 12px', display:'flex', gap:8, alignItems:'center' }}>
          <span style={{ color:'#38bdf8', fontFamily:'monospace', fontSize:14 }}>$</span>
          <input
            value={cmd}
            onChange={e => setCmd(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Escribe un comando o selecciona del panel... (↑↓ historial)"
            autoFocus
            style={{ flex:1, background:'transparent', border:'none', outline:'none', color:'#e2e8f0', fontSize:13, fontFamily:'monospace' }}/>
          <button style={S.btn()} onClick={() => run(cmd)}>Ejecutar ↵</button>
          <button style={S.btn('#334155')} onClick={() => setHistory(h => h.filter(x => x.type==='info'))}>Limpiar</button>
        </div>
      </div>
    </div>
  );
}
