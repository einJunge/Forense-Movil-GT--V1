"""
report_service.py  —  Forense Móvil GT
Generador de informes periciales nivel experto forense.
"""

import os, json, hashlib, platform
from datetime import datetime
from collections import Counter

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from sqlalchemy.orm import Session
from app.db.models import Scan, Finding, Event, Device, Artifact, Case

# ─────────────────────────────── PALETA ────────────────────────────────────────
C_NAVY      = colors.HexColor('#0f172a')
C_BLUE      = colors.HexColor('#1d4ed8')
C_BLUE_LT   = colors.HexColor('#3b82f6')
C_SLATE     = colors.HexColor('#334155')
C_SLATE_LT  = colors.HexColor('#64748b')
C_WHITE     = colors.white
C_OFF_WHITE = colors.HexColor('#f8fafc')
C_CRITICAL  = colors.HexColor('#dc2626')
C_HIGH      = colors.HexColor('#ea580c')
C_MEDIUM    = colors.HexColor('#ca8a04')
C_LOW       = colors.HexColor('#16a34a')
C_CLEAN     = colors.HexColor('#2563eb')
C_BORDER    = colors.HexColor('#cbd5e1')
C_ROW_ALT   = colors.HexColor('#f1f5f9')

SEV_COLOR = {
    'critical': C_CRITICAL, 'high': C_HIGH,
    'medium': C_MEDIUM,     'low': C_LOW,
    'clean': C_CLEAN,       'unknown': C_SLATE_LT,
}

RISK_LABEL = {
    'critical': '🔴 CRÍTICO',  'high':    '🟠 ALTO',
    'medium':   '🟡 MEDIO',    'low':     '🟢 BAJO',
    'clean':    '✅ LIMPIO',   'unknown': '⚪ DESCONOCIDO',
}

# ─────────────────────────────── ESTILOS ───────────────────────────────────────
def build_styles():
    s = getSampleStyleSheet()

    def add(name, **kw):
        s.add(ParagraphStyle(name=name, **kw))

    add('FMTitle',
        fontName='Helvetica-Bold', fontSize=22, leading=28,
        textColor=C_WHITE, alignment=TA_CENTER, spaceAfter=4)

    add('FMSubtitle',
        fontName='Helvetica', fontSize=11, leading=14,
        textColor=colors.HexColor('#93c5fd'), alignment=TA_CENTER, spaceAfter=2)

    add('FMLabel',
        fontName='Helvetica-Bold', fontSize=7, leading=9,
        textColor=C_SLATE_LT, spaceBefore=0, spaceAfter=0)

    add('FMValue',
        fontName='Helvetica', fontSize=9, leading=12,
        textColor=C_NAVY, spaceBefore=0, spaceAfter=0)

    add('FMH1',
        fontName='Helvetica-Bold', fontSize=13, leading=16,
        textColor=C_BLUE, spaceBefore=16, spaceAfter=6,
        borderPad=0)

    add('FMH2',
        fontName='Helvetica-Bold', fontSize=10, leading=13,
        textColor=C_NAVY, spaceBefore=10, spaceAfter=4)

    add('FMBody',
        fontName='Helvetica', fontSize=9, leading=13,
        textColor=C_NAVY, alignment=TA_JUSTIFY, spaceAfter=4)

    add('FMBodyBold',
        fontName='Helvetica-Bold', fontSize=9, leading=13,
        textColor=C_NAVY, spaceAfter=4)

    add('FMSmall',
        fontName='Helvetica', fontSize=7.5, leading=10,
        textColor=C_SLATE, spaceAfter=2)

    add('FMCode',
        fontName='Courier', fontSize=7.5, leading=10,
        textColor=colors.HexColor('#1e3a5f'),
        backColor=colors.HexColor('#f0f9ff'),
        spaceAfter=2, spaceBefore=2,
        leftIndent=6, rightIndent=6)

    add('FMBullet',
        fontName='Helvetica', fontSize=8.5, leading=12,
        textColor=C_NAVY, leftIndent=12, spaceAfter=2)

    add('FMSeverity',
        fontName='Helvetica-Bold', fontSize=8, leading=10,
        alignment=TA_CENTER)

    add('FMFooter',
        fontName='Helvetica', fontSize=7, leading=9,
        textColor=C_SLATE_LT, alignment=TA_CENTER)

    add('FMPageNum',
        fontName='Helvetica', fontSize=7.5, leading=9,
        textColor=C_SLATE_LT, alignment=TA_RIGHT)

    return s


# ─────────────────────────────── HELPERS ───────────────────────────────────────
def sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for c in iter(lambda: f.read(8192), b''): h.update(c)
        return h.hexdigest()
    except Exception:
        return 'N/D'


def ts(dt):
    """Formatea datetime a string legible."""
    if not dt:
        return 'N/D'
    if isinstance(dt, str):
        return dt[:19].replace('T', ' ')
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def dur(start, end):
    """Duración entre dos datetime."""
    if not start or not end:
        return 'N/D'
    try:
        delta = (end - start).total_seconds()
        m, s = divmod(int(delta), 60)
        return f'{m}m {s}s'
    except Exception:
        return 'N/D'


def hr(story, color=C_BORDER, thickness=0.5, space=6):
    story.append(Spacer(1, space))
    story.append(HRFlowable(width='100%', thickness=thickness, color=color, spaceAfter=space))


def section_header(story, number, title, styles):
    """Encabezado de sección con línea de color."""
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width='100%', thickness=2, color=C_BLUE, spaceAfter=4))
    story.append(Paragraph(f'{number}. {title.upper()}', styles['FMH1']))


def info_grid(data_pairs, col_width=None):
    """
    Tabla de 2 columnas (label | valor) para metadatos.
    data_pairs = [(label, value), ...]
    """
    rows = []
    for label, value in data_pairs:
        rows.append([
            Paragraph(str(label).upper(), _STYLES['FMLabel']),
            Paragraph(str(value) if value else 'N/D', _STYLES['FMValue']),
        ])
    t = Table(rows, colWidths=[col_width or 4*cm, None])
    t.setStyle(TableStyle([
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('TOPPADDING',  (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING',(0,0), (-1,-1), 4),
    ]))
    return t


def severity_badge(sev):
    color = SEV_COLOR.get((sev or '').lower(), C_SLATE_LT)
    label = (sev or 'N/D').upper()
    p = Paragraph(label, ParagraphStyle(
        'badge', fontName='Helvetica-Bold', fontSize=7,
        textColor=C_WHITE, alignment=TA_CENTER))
    t = Table([[p]], colWidths=[1.8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), color),
        ('ROUNDEDCORNERS', [3,3,3,3]),
        ('TOPPADDING',    (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ('RIGHTPADDING',  (0,0), (-1,-1), 4),
    ]))
    return t


def risk_box(risk, styles):
    """Cuadro grande de nivel de riesgo."""
    color = SEV_COLOR.get((risk or 'unknown').lower(), C_SLATE_LT)
    label = RISK_LABEL.get((risk or 'unknown').lower(), risk.upper())
    p = Paragraph(label, ParagraphStyle(
        'riskbox', fontName='Helvetica-Bold', fontSize=16,
        textColor=C_WHITE, alignment=TA_CENTER))
    t = Table([[p]], colWidths=[5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), color),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ('RIGHTPADDING',  (0,0), (-1,-1), 16),
        ('ROUNDEDCORNERS', [4,4,4,4]),
    ]))
    return t


def findings_table(findings_list, styles, show_scan_col=False):
    """Tabla de hallazgos completa con colores por severidad."""
    SEV_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    sorted_f = sorted(findings_list,
                      key=lambda x: SEV_ORDER.get((x.get('severity') or x.get('sev') or '').lower(), 9))

    header = ['#', 'SEV', 'CATEGORÍA', 'HERRAMIENTA', 'EVIDENCIA']
    col_w  = [0.6*cm, 1.8*cm, 3.2*cm, 2.5*cm, None]
    if show_scan_col:
        header.insert(1, 'SCAN')
        col_w.insert(1, 1.2*cm)

    rows = [header]
    for i, f in enumerate(sorted_f, 1):
        sev  = (f.get('severity') or f.get('sev') or 'unknown').lower()
        cat  = f.get('category', 'N/D')
        tool = f.get('tool', 'N/D')
        ev   = (f.get('evidence', '') or '')[:180]
        row  = [str(i), severity_badge(sev), cat, tool,
                Paragraph(ev, styles['FMSmall'])]
        if show_scan_col:
            row.insert(1, str(f.get('scan_id', '')))
        rows.append(row)

    t = Table(rows, colWidths=col_w, repeatRows=1)
    style_cmds = [
        # encabezado
        ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
        ('TEXTCOLOR',     (0,0), (-1,0), C_WHITE),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0), 7.5),
        ('ALIGN',         (0,0), (-1,0), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,0), 5),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
        # celdas
        ('FONTSIZE',      (0,1), (-1,-1), 8),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 5),
        ('RIGHTPADDING',  (0,0), (-1,-1), 5),
        ('GRID',          (0,0), (-1,-1), 0.3, C_BORDER),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_ROW_ALT]),
        # columna #
        ('ALIGN',         (0,1), (0,-1), 'CENTER'),
        # columna evidencia
        ('ALIGN',         (-1,0), (-1,-1), 'LEFT'),
    ]
    # colorear filas críticas
    for i, f in enumerate(sorted_f, 1):
        sev = (f.get('severity') or '').lower()
        if sev == 'critical':
            style_cmds.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#fff1f2')))
        elif sev == 'high':
            style_cmds.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor('#fff7ed')))

    t.setStyle(TableStyle(style_cmds))
    return t


def events_table(events_list, styles):
    """Timeline de eventos formateada."""
    header = ['TIMESTAMP', 'FUENTE', 'MENSAJE']
    rows = [header]
    for e in events_list[:200]:
        rows.append([
            Paragraph(ts(e.get('timestamp','')), styles['FMSmall']),
            Paragraph(str(e.get('source','')), styles['FMSmall']),
            Paragraph(str(e.get('message',''))[:200], styles['FMSmall']),
        ])
    t = Table(rows, colWidths=[3.5*cm, 2.2*cm, None], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), C_SLATE),
        ('TEXTCOLOR',     (0,0), (-1,0), C_WHITE),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 7.5),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING',   (0,0), (-1,-1), 5),
        ('GRID',          (0,0), (-1,-1), 0.3, C_BORDER),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_ROW_ALT]),
    ]))
    return t


def stat_cards(stats, styles):
    """Fila de tarjetas de estadísticas: [(label, value, color), ...]"""
    cells = []
    for label, value, color in stats:
        inner = Table([
            [Paragraph(str(value), ParagraphStyle('sv', fontName='Helvetica-Bold',
             fontSize=22, textColor=color, alignment=TA_CENTER))],
            [Paragraph(label, ParagraphStyle('sl', fontName='Helvetica',
             fontSize=8, textColor=C_SLATE, alignment=TA_CENTER))],
        ], colWidths=[3.5*cm])
        inner.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), C_OFF_WHITE),
            ('BOX',        (0,0), (-1,-1), 1, C_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING',(0,0),(-1,-1),8),
        ]))
        cells.append(inner)
    t = Table([cells], colWidths=[3.5*cm] * len(cells))
    t.setStyle(TableStyle([
        ('ALIGN',  (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    return t


# ────────────────────── PORTADA + HEADER/FOOTER ────────────────────────────────
def cover_page(story, doc_meta, styles):
    """Portada completa del informe."""
    # Bloque de color superior
    cover_data = [[Paragraph('FORENSE MÓVIL GT', styles['FMTitle'])]]
    cover_t = Table(cover_data, colWidths=[doc_meta['page_w'] - 4*cm])
    cover_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 28),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 20),
        ('RIGHTPADDING',  (0,0), (-1,-1), 20),
    ]))
    story.append(cover_t)

    sub_data = [[Paragraph(doc_meta.get('report_type_label', 'INFORME TÉCNICO PERICIAL'),
                           styles['FMSubtitle'])]]
    sub_t = Table(sub_data, colWidths=[doc_meta['page_w'] - 4*cm])
    sub_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BLUE),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(sub_t)
    story.append(Spacer(1, 20))

    # Datos del caso
    case_rows = doc_meta.get('cover_rows', [])
    for label, value in case_rows:
        row_t = Table([
            [Paragraph(label.upper(), styles['FMLabel']),
             Paragraph(str(value) if value else 'N/D', styles['FMValue'])],
        ], colWidths=[4*cm, doc_meta['page_w'] - 8.5*cm])
        row_t.setStyle(TableStyle([
            ('TOPPADDING',    (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING',   (0,0), (-1,-1), 10),
            ('LINEBELOW',     (0,0), (-1,-1), 0.3, C_BORDER),
        ]))
        story.append(row_t)

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width='100%', thickness=1.5, color=C_BLUE))
    story.append(Spacer(1, 10))

    # Advertencia legal
    legal = (
        'Este documento contiene información técnica de carácter pericial generada mediante '
        'análisis forense digital. Su contenido es de uso exclusivo para el caso indicado y '
        'destinado a las autoridades o personas autorizadas. La reproducción o distribución '
        'no autorizada de este informe puede constituir una violación legal.'
    )
    story.append(Paragraph(legal, styles['FMSmall']))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f'Generado el {ts(datetime.utcnow())} UTC  ·  Forense Móvil GT v2.1  ·  '
        f'Sistema: {platform.system()} {platform.release()}',
        styles['FMSmall']))
    story.append(PageBreak())


# ────────────────────── INFORME DE SCAN INDIVIDUAL ────────────────────────────
def generate_report(db: Session, scan: Scan):
    os.makedirs('/var/reports', exist_ok=True)
    device   = db.query(Device).filter(Device.id == scan.device_id).first()
    findings = db.query(Finding).filter(Finding.scan_id == scan.id).all()
    events   = db.query(Event).filter(Event.scan_id == scan.id).all()
    artifacts= db.query(Artifact).filter(Artifact.scan_id == scan.id).all()
    case_obj = (db.query(Case).filter(Case.id == scan.case_id).first()
                if scan.case_id else None)

    json_path = f'/var/reports/scan_{scan.id}.json'
    pdf_path  = f'/var/reports/scan_{scan.id}.pdf'

    # ── JSON ──────────────────────────────────────────────────────────────────
    sev_counts = Counter(f.severity for f in findings)
    data = {
        'report_version': '2.1',
        'tool': 'Forense Móvil GT',
        'scan_id': scan.id,
        'generated_at': datetime.utcnow().isoformat(),
        'case': {'id': case_obj.id, 'name': case_obj.name,
                 'investigator': case_obj.investigator} if case_obj else None,
        'device': {
            'serial':           device.adb_serial if device else 'N/A',
            'model':            device.model if device else 'N/A',
            'manufacturer':     device.manufacturer if device else 'N/A',
            'android_version':  device.android_version if device else 'N/A',
            'sdk_version':      device.sdk_version if device else 'N/A',
            'root_status':      device.root_status if device else False,
            'connection_type':  device.connect_type if device else 'N/A',
        },
        'scan': {
            'status':       scan.status,
            'risk_level':   scan.risk_level,
            'started_at':   scan.started_at.isoformat() if scan.started_at else None,
            'finished_at':  scan.finished_at.isoformat() if scan.finished_at else None,
            'duration_s':   (scan.finished_at - scan.started_at).total_seconds()
                            if scan.started_at and scan.finished_at else None,
        },
        'summary': {
            'total_findings':    len(findings),
            'by_severity':       dict(sev_counts),
            'total_events':      len(events),
            'total_artifacts':   len(artifacts),
        },
        'findings': [{'id': f.id, 'category': f.category, 'severity': f.severity,
                      'tool': f.tool, 'evidence': f.evidence,
                      'created_at': f.created_at.isoformat() if f.created_at else None}
                     for f in findings],
        'events':   [{'id': e.id, 'timestamp': e.timestamp.isoformat(),
                      'source': e.source, 'message': e.message} for e in events],
        'artifacts':[{'id': a.id, 'category': a.category, 'subcategory': a.subcategory,
                      'source_path': a.source_path, 'size': a.size,
                      'sha256': a.sha256_hash} for a in artifacts],
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # ── PDF ───────────────────────────────────────────────────────────────────
    global _STYLES
    _STYLES = build_styles()
    S = _STYLES

    page_w, page_h = letter
    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2*cm,
        title=f'Informe Forense — Scan #{scan.id}',
        author='Forense Móvil GT',
    )

    story = []

    # ── PORTADA ───────────────────────────────────────────────────────────────
    cover_page(story, {
        'page_w': page_w,
        'report_type_label': 'INFORME TÉCNICO — ANÁLISIS DE DISPOSITIVO MÓVIL',
        'cover_rows': [
            ('Número de escaneo',   f'SCAN-{scan.id:05d}'),
            ('Caso asociado',       case_obj.name if case_obj else 'Sin caso'),
            ('Investigador',        case_obj.investigator if case_obj else 'N/D'),
            ('Dispositivo',         f'{device.manufacturer} {device.model}' if device else 'N/D'),
            ('Serial / ADB',        device.adb_serial if device else 'N/D'),
            ('Nivel de riesgo',     RISK_LABEL.get(scan.risk_level or 'unknown', scan.risk_level)),
            ('Fecha inicio',        ts(scan.started_at)),
            ('Fecha fin',           ts(scan.finished_at)),
            ('Duración',            dur(scan.started_at, scan.finished_at)),
        ],
    }, S)

    # ── 1. RESUMEN EJECUTIVO ──────────────────────────────────────────────────
    section_header(story, 1, 'Resumen Ejecutivo', S)
    story.append(Paragraph(
        f'El presente informe documenta los resultados del análisis forense digital '
        f'realizado sobre el dispositivo <b>{device.manufacturer if device else "N/D"} '
        f'{device.model if device else ""}</b> (serial: <b>{device.adb_serial if device else "N/D"}</b>), '
        f'ejecutado el <b>{ts(scan.started_at)}</b> con una duración de '
        f'<b>{dur(scan.started_at, scan.finished_at)}</b>. '
        f'El análisis identificó un total de <b>{len(findings)} hallazgos</b> con un '
        f'nivel de riesgo global de <b>{RISK_LABEL.get(scan.risk_level or "unknown")}</b>.',
        S['FMBody']))

    story.append(Spacer(1, 12))
    # Tarjetas de estadísticas
    story.append(stat_cards([
        ('CRÍTICOS',   sev_counts.get('critical', 0), C_CRITICAL),
        ('ALTOS',      sev_counts.get('high', 0),     C_HIGH),
        ('MEDIOS',     sev_counts.get('medium', 0),   C_MEDIUM),
        ('BAJOS',      sev_counts.get('low', 0),      C_LOW),
        ('EVENTOS',    len(events),                    C_BLUE),
        ('ARTEFACTOS', len(artifacts),                 C_SLATE),
    ], S))
    story.append(Spacer(1, 12))

    # Caja de riesgo
    risk_row = Table(
        [[Paragraph('NIVEL DE RIESGO GLOBAL:', S['FMH2']), risk_box(scan.risk_level, S)]],
        colWidths=[9*cm, 5*cm])
    risk_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(risk_row)

    # ── 2. INFORMACIÓN DEL DISPOSITIVO ────────────────────────────────────────
    section_header(story, 2, 'Información del Dispositivo', S)
    if device:
        dev_data = [
            ('Fabricante',           device.manufacturer),
            ('Modelo',               device.model),
            ('Serial / ADB',         device.adb_serial),
            ('Versión Android',      device.android_version),
            ('SDK Version',          device.sdk_version),
            ('Tipo de conexión',     (device.connect_type or 'USB').upper()),
            ('Estado root',          '⚠️ ROOTED — acceso privilegiado detectado'
                                     if device.root_status else '✅ Sin root detectado'),
            ('Primera vez visto',    ts(device.created_at)),
        ]
        story.append(info_grid(dev_data, col_width=5*cm))

        if device.root_status:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                '⚠️  <b>ADVERTENCIA:</b> El dispositivo presenta acceso root. '
                'Esto permite eludir controles de seguridad del sistema operativo, '
                'acceder a datos de aplicaciones sin restricciones y potencialmente '
                'comprometer la integridad de la evidencia digital.',
                ParagraphStyle('warn', parent=S['FMBody'], textColor=C_CRITICAL,
                               backColor=colors.HexColor('#fff1f2'),
                               leftIndent=6, rightIndent=6,
                               borderPad=6)))

    # ── 3. INFORMACIÓN DEL CASO ───────────────────────────────────────────────
    if case_obj:
        section_header(story, 3, 'Información del Caso', S)
        story.append(info_grid([
            ('ID de caso',        str(case_obj.id)),
            ('Nombre',            case_obj.name),
            ('Slug',              case_obj.slug),
            ('Investigador',      case_obj.investigator),
            ('Descripción',       case_obj.description),
            ('Estado del caso',   case_obj.status.upper()),
            ('Ruta del expediente', case_obj.folder_path),
            ('Fecha de creación', ts(case_obj.created_at)),
        ], col_width=5*cm))

    # ── 4. HALLAZGOS DETALLADOS ───────────────────────────────────────────────
    section_header(story, 4, 'Hallazgos del Análisis', S)

    if not findings:
        story.append(Paragraph('✅ No se detectaron hallazgos en este escaneo.', S['FMBody']))
    else:
        # Agrupados por categoría
        cats = {}
        for f in findings:
            cats.setdefault(f.category, []).append(f)

        for cat, cat_findings in sorted(cats.items(),
                key=lambda x: min(
                    {'critical':0,'high':1,'medium':2,'low':3}.get(f.severity,9)
                    for f in x[1])):
            story.append(Paragraph(f'▸ {cat.replace("_"," ").title()} '
                                   f'({len(cat_findings)} hallazgo(s))', S['FMH2']))
            f_list = [{'severity': f.severity, 'category': f.category,
                       'tool': f.tool, 'evidence': f.evidence} for f in cat_findings]
            story.append(findings_table(f_list, S))
            story.append(Spacer(1, 8))

    # ── 5. ARTEFACTOS FORENSES ────────────────────────────────────────────────
    if artifacts:
        section_header(story, 5, 'Artefactos Forenses Recolectados', S)
        art_header = ['#', 'CATEGORÍA', 'SUBCATEGORÍA', 'ARCHIVO', 'TAMAÑO', 'SHA-256']
        art_rows   = [art_header]
        for i, a in enumerate(artifacts, 1):
            art_rows.append([
                str(i),
                a.category,
                a.subcategory or '-',
                Paragraph(os.path.basename(a.source_path or ''), S['FMSmall']),
                f'{a.size:,} B' if a.size else '-',
                Paragraph((a.sha256_hash or '-')[:20] + '…' if a.sha256_hash else '-',
                           S['FMCode']),
            ])
        at = Table(art_rows, colWidths=[0.5*cm, 2.5*cm, 2.5*cm, None, 1.8*cm, 2.8*cm],
                   repeatRows=1)
        at.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
            ('TEXTCOLOR',     (0,0), (-1,0), C_WHITE),
            ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,-1), 7.5),
            ('GRID',          (0,0), (-1,-1), 0.3, C_BORDER),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_ROW_ALT]),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ]))
        story.append(at)

    # ── 6. LÍNEA DE TIEMPO ────────────────────────────────────────────────────
    section_header(story, 6, 'Línea de Tiempo del Análisis', S)
    if not events:
        story.append(Paragraph('Sin eventos registrados.', S['FMBody']))
    else:
        ev_list = [{'timestamp': e.timestamp.isoformat(), 'source': e.source,
                    'message': e.message} for e in events]
        story.append(events_table(ev_list, S))

    # ── 7. METODOLOGÍA ────────────────────────────────────────────────────────
    section_header(story, 7, 'Metodología y Herramientas', S)
    for item in [
        '<b>ADB (Android Debug Bridge):</b> Enumeración de paquetes, permisos, '
        'procesos activos, servicios de accesibilidad y administradores de dispositivo.',
        '<b>Análisis de red:</b> Identificación de puertos abiertos mediante lectura '
        'de /proc/net/tcp y /proc/net/tcp6; correlación con UIDs y paquetes instalados.',
        '<b>ClamAV:</b> Escaneo antimalware de archivos descargados del almacenamiento '
        'externo del dispositivo (carpeta /sdcard/Download).',
        '<b>Análisis de logcat:</b> Revisión de registros del sistema en busca de '
        'palabras clave sensibles (credenciales, tokens, datos financieros).',
        '<b>Análisis de sistema de archivos:</b> Búsqueda de APKs sideloaded fuera '
        'de la Play Store y archivos sospechosos en particiones de sistema (root).',
    ]:
        story.append(Paragraph(f'• {item}', S['FMBullet']))
        story.append(Spacer(1, 3))

    # ── 8. INTEGRIDAD DEL REPORTE ─────────────────────────────────────────────
    section_header(story, 8, 'Integridad y Cadena de Custodia', S)
    story.append(info_grid([
        ('Archivo JSON',    json_path),
        ('SHA-256 JSON',    sha256(json_path)),
        ('Generado en',     f'{ts(datetime.utcnow())} UTC'),
        ('Plataforma',      f'{platform.system()} {platform.release()}'),
        ('Herramienta',     'Forense Móvil GT v2.1'),
    ], col_width=5*cm))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        'Este informe fue generado automáticamente por Forense Móvil GT. '
        'Los hallazgos aquí documentados deben ser validados por un perito forense '
        'certificado antes de ser presentados como evidencia en procesos legales.',
        S['FMSmall']))

    doc.build(story)

    # copiar al expediente del caso
    case_report_json = case_report_pdf = None
    if case_obj and case_obj.folder_path:
        rd = os.path.join(case_obj.folder_path, 'reportes')
        os.makedirs(rd, exist_ok=True)
        case_report_json = os.path.join(rd, f'scan_{scan.id}.json')
        case_report_pdf  = os.path.join(rd, f'scan_{scan.id}.pdf')
        for src, dst in [(json_path, case_report_json), (pdf_path, case_report_pdf)]:
            with open(src, 'rb') as s, open(dst, 'wb') as d:
                d.write(s.read())

    return {
        'json_path':        json_path,
        'json_sha256':      sha256(json_path),
        'pdf_path':         pdf_path,
        'pdf_sha256':       sha256(pdf_path),
        'case_report_json': case_report_json,
        'case_report_pdf':  case_report_pdf,
        'findings_count':   len(findings),
        'risk_level':       scan.risk_level,
    }


# ─────────────────────── INFORME PERICIAL CONSOLIDADO ──────────────────────────
def generate_pericial_report(db: Session, payload: dict):
    case_id  = payload.get('case_id')
    case_obj = db.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        raise ValueError('Caso no encontrado')

    report_dir = os.path.join(case_obj.folder_path, 'reportes')
    os.makedirs(report_dir, exist_ok=True)
    ts_str   = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    json_path = os.path.join(report_dir, f'reporte_pericial_{ts_str}.json')
    pdf_path  = os.path.join(report_dir, f'reporte_pericial_{ts_str}.pdf')

    # ── Recolectar todos los datos ─────────────────────────────────────────────
    scans_db = db.query(Scan).filter(Scan.case_id == case_id).all()
    requested_ids = payload.get('scan_ids') or []
    if requested_ids:
        scans_db = [s for s in scans_db if s.id in requested_ids]

    all_findings  = []
    all_events    = []
    all_artifacts = []
    devices_map   = {}
    scan_summaries= []
    SEV_ORDER     = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

    for scan in scans_db:
        device    = db.query(Device).filter(Device.id == scan.device_id).first()
        findings  = db.query(Finding).filter(Finding.scan_id == scan.id).all()
        events    = db.query(Event).filter(Event.scan_id == scan.id)\
                      .order_by(Event.timestamp.asc()).all()
        artifacts = db.query(Artifact).filter(Artifact.scan_id == scan.id).all()

        if device:
            devices_map[device.id] = device

        f_list = [{'scan_id': scan.id, 'severity': f.severity, 'category': f.category,
                   'tool': f.tool, 'evidence': f.evidence,
                   'created_at': f.created_at.isoformat() if f.created_at else ''}
                  for f in findings]
        e_list = [{'scan_id': scan.id, 'timestamp': e.timestamp.isoformat(),
                   'source': e.source, 'message': e.message} for e in events]
        a_list = [{'scan_id': scan.id, 'category': a.category,
                   'subcategory': a.subcategory, 'source_path': a.source_path,
                   'size': a.size, 'sha256': a.sha256_hash} for a in artifacts]

        all_findings.extend(f_list)
        all_events.extend(e_list)
        all_artifacts.extend(a_list)

        sev_counts = Counter(f.severity for f in findings)
        scan_summaries.append({
            'scan_id':       scan.id,
            'status':        scan.status,
            'risk_level':    scan.risk_level,
            'started_at':    scan.started_at.isoformat() if scan.started_at else '',
            'finished_at':   scan.finished_at.isoformat() if scan.finished_at else '',
            'duration':      dur(scan.started_at, scan.finished_at),
            'findings_count': len(findings),
            'events_count':   len(events),
            'artifacts_count':len(artifacts),
            'by_severity':    dict(sev_counts),
            'device': {
                'id':          device.id if device else None,
                'serial':      device.adb_serial if device else 'N/D',
                'model':       device.model if device else 'N/D',
                'manufacturer':device.manufacturer if device else 'N/D',
                'android':     device.android_version if device else 'N/D',
                'sdk':         device.sdk_version if device else 'N/D',
                'root':        device.root_status if device else False,
            },
        })

    # Ordenar hallazgos por severidad
    all_findings.sort(key=lambda x: SEV_ORDER.get((x.get('severity') or '').lower(), 9))

    # ── Estadísticas globales ──────────────────────────────────────────────────
    global_sev  = Counter(f['severity'] for f in all_findings)
    global_cats = Counter(f['category'] for f in all_findings)
    global_tools= Counter(f['tool'] for f in all_findings)
    worst_risk  = min(
        (s['risk_level'] for s in scan_summaries),
        key=lambda r: {'critical':0,'high':1,'medium':2,'low':3,'clean':4,'unknown':5}.get(r,5)
    ) if scan_summaries else 'unknown'

    # ── JSON exportado ────────────────────────────────────────────────────────
    data = {
        'report_version':  '2.1',
        'report_type':     'pericial_consolidado',
        'tool':            'Forense Móvil GT',
        'generated_at':    datetime.utcnow().isoformat(),
        'analyst':         payload.get('analyst_name', ''),
        'requested_by':    payload.get('requested_by', ''),
        'objective':       payload.get('objective', ''),
        'methodology':     payload.get('methodology', ''),
        'conclusions':     payload.get('conclusions', ''),
        'case': {
            'id':          case_obj.id,
            'name':        case_obj.name,
            'slug':        case_obj.slug,
            'investigator':case_obj.investigator,
            'description': case_obj.description,
            'status':      case_obj.status,
            'folder_path': case_obj.folder_path,
            'created_at':  case_obj.created_at.isoformat() if case_obj.created_at else '',
        },
        'global_summary': {
            'total_scans':     len(scan_summaries),
            'total_devices':   len(devices_map),
            'total_findings':  len(all_findings),
            'total_events':    len(all_events),
            'total_artifacts': len(all_artifacts),
            'worst_risk':      worst_risk,
            'by_severity':     dict(global_sev),
            'by_category':     dict(global_cats.most_common(20)),
            'by_tool':         dict(global_tools),
        },
        'scans':     scan_summaries,
        'findings':  all_findings,
        'events':    all_events,
        'artifacts': all_artifacts,
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # ── PDF ───────────────────────────────────────────────────────────────────
    global _STYLES
    _STYLES = build_styles()
    S = _STYLES

    page_w, page_h = letter
    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2*cm,
        title=f'Informe Pericial — {case_obj.name}',
        author='Forense Móvil GT',
    )
    story = []

    # ── PORTADA ───────────────────────────────────────────────────────────────
    cover_page(story, {
        'page_w': page_w,
        'report_type_label': 'INFORME PERICIAL FORENSE CONSOLIDADO',
        'cover_rows': [
            ('Caso',              case_obj.name),
            ('Slug / ID',         f'{case_obj.slug}  ·  ID: {case_obj.id}'),
            ('Investigador',      case_obj.investigator or 'N/D'),
            ('Descripción',       (case_obj.description or 'N/D')[:120]),
            ('Estado del caso',   case_obj.status.upper()),
            ('Scans analizados',  str(len(scan_summaries))),
            ('Dispositivos',      str(len(devices_map))),
            ('Total hallazgos',   str(len(all_findings))),
            ('Riesgo máximo',     RISK_LABEL.get(worst_risk, worst_risk)),
            ('Perito analista',   payload.get('analyst_name', 'N/D')),
            ('Solicitado por',    payload.get('requested_by', 'N/D')),
        ],
    }, S)

    # ── 1. RESUMEN EJECUTIVO ──────────────────────────────────────────────────
    section_header(story, 1, 'Resumen Ejecutivo', S)
    story.append(Paragraph(
        f'El presente informe pericial consolida los resultados del análisis forense '
        f'digital realizado en el marco del caso <b>«{case_obj.name}»</b>. '
        f'Se analizaron <b>{len(scan_summaries)} escaneo(s)</b> correspondientes a '
        f'<b>{len(devices_map)} dispositivo(s)</b> móvil(es), obteniendo un total de '
        f'<b>{len(all_findings)} hallazgo(s)</b> y <b>{len(all_events)} evento(s)</b> '
        f'en la línea de tiempo. El nivel de riesgo máximo identificado es '
        f'<b>{RISK_LABEL.get(worst_risk, worst_risk)}</b>.',
        S['FMBody']))

    story.append(Spacer(1, 12))
    story.append(stat_cards([
        ('CRÍTICOS',   global_sev.get('critical', 0), C_CRITICAL),
        ('ALTOS',      global_sev.get('high', 0),     C_HIGH),
        ('MEDIOS',     global_sev.get('medium', 0),   C_MEDIUM),
        ('BAJOS',      global_sev.get('low', 0),      C_LOW),
        ('EVENTOS',    len(all_events),                C_BLUE),
        ('ARTEFACTOS', len(all_artifacts),             C_SLATE),
    ], S))
    story.append(Spacer(1, 12))
    risk_row = Table(
        [[Paragraph('RIESGO MÁXIMO DEL CASO:', S['FMH2']),
          risk_box(worst_risk, S)]],
        colWidths=[9*cm, 5*cm])
    risk_row.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                                   ('LEFTPADDING',(0,0),(-1,-1),0)]))
    story.append(risk_row)

    # ── 2. OBJETIVO Y METODOLOGÍA ─────────────────────────────────────────────
    section_header(story, 2, 'Objetivo y Metodología', S)
    obj = (payload.get('objective') or
           'Identificar, preservar y documentar evidencia digital en dispositivos '
           'móviles Android bajo análisis forense, siguiendo principios de integridad, '
           'reproducibilidad y cadena de custodia.')
    met = (payload.get('methodology') or
           'Análisis técnico-forense no destructivo mediante herramientas ADB, '
           'inspección de permisos, procesos, red y sistema de archivos; '
           'escaneo antimalware ClamAV; y correlación de artefactos con la '
           'línea de tiempo del dispositivo.')
    story.append(Paragraph(f'<b>Objetivo:</b> {obj}', S['FMBody']))
    story.append(Paragraph(f'<b>Metodología:</b> {met}', S['FMBody']))

    # ── 3. INFORMACIÓN DEL CASO ───────────────────────────────────────────────
    section_header(story, 3, 'Información del Caso', S)
    story.append(info_grid([
        ('ID',            str(case_obj.id)),
        ('Nombre',        case_obj.name),
        ('Slug',          case_obj.slug),
        ('Investigador',  case_obj.investigator),
        ('Descripción',   case_obj.description),
        ('Estado',        case_obj.status.upper()),
        ('Carpeta',       case_obj.folder_path),
        ('Creado el',     ts(case_obj.created_at)),
    ], col_width=4.5*cm))

    # ── 4. DISPOSITIVOS ANALIZADOS ────────────────────────────────────────────
    section_header(story, 4, 'Dispositivos Analizados', S)
    dev_header = ['#', 'FABRICANTE', 'MODELO', 'SERIAL', 'ANDROID', 'SDK', 'ROOT', 'SCANS']
    dev_rows   = [dev_header]
    for i, (did, dev) in enumerate(devices_map.items(), 1):
        n_scans = sum(1 for s in scan_summaries if s['device']['id'] == did)
        dev_rows.append([
            str(i),
            dev.manufacturer, dev.model, dev.adb_serial,
            dev.android_version, dev.sdk_version,
            '⚠️ SÍ' if dev.root_status else 'No',
            str(n_scans),
        ])
    dt = Table(dev_rows, repeatRows=1)
    dt.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
        ('TEXTCOLOR',     (0,0), (-1,0), C_WHITE),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 8),
        ('GRID',          (0,0), (-1,-1), 0.3, C_BORDER),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_ROW_ALT]),
        ('ALIGN',         (6,1), (6,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 5),
    ]))
    story.append(dt)

    # ── 5. RESUMEN DE ESCANEOS ────────────────────────────────────────────────
    section_header(story, 5, 'Resumen de Escaneos', S)
    sc_header = ['SCAN', 'DISPOSITIVO', 'INICIO', 'FIN', 'DUR.', 'RIESGO',
                 'HALLAZGOS', 'CRÍTICOS', 'ALTOS']
    sc_rows   = [sc_header]
    for s in scan_summaries:
        sc_rows.append([
            f'#{s["scan_id"]:05d}',
            f'{s["device"]["manufacturer"]} {s["device"]["model"]}',
            ts(s['started_at'])[:16],
            ts(s['finished_at'])[:16],
            s['duration'],
            RISK_LABEL.get(s['risk_level'], s['risk_level']),
            str(s['findings_count']),
            str(s['by_severity'].get('critical', 0)),
            str(s['by_severity'].get('high', 0)),
        ])
    sct = Table(sc_rows, repeatRows=1)
    sct.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
        ('TEXTCOLOR',     (0,0), (-1,0), C_WHITE),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 7.5),
        ('GRID',          (0,0), (-1,-1), 0.3, C_BORDER),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_ROW_ALT]),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 5),
        ('ALIGN',         (6,0), (8,-1), 'CENTER'),
    ]))
    story.append(sct)

    # ── 6. ANÁLISIS DE HALLAZGOS ──────────────────────────────────────────────
    section_header(story, 6, 'Análisis de Hallazgos', S)

    # Distribución por categoría
    story.append(Paragraph('6.1 Distribución por Categoría', S['FMH2']))
    if global_cats:
        cat_header = ['CATEGORÍA', 'TOTAL', 'CRÍTICOS', 'ALTOS', 'MEDIOS', 'BAJOS']
        cat_rows   = [cat_header]
        for cat, total in global_cats.most_common():
            cat_f = [f for f in all_findings if f['category'] == cat]
            csev  = Counter(f['severity'] for f in cat_f)
            cat_rows.append([
                cat.replace('_', ' ').title(), str(total),
                str(csev.get('critical', 0)), str(csev.get('high', 0)),
                str(csev.get('medium', 0)),   str(csev.get('low', 0)),
            ])
        catt = Table(cat_rows, repeatRows=1)
        catt.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), C_SLATE),
            ('TEXTCOLOR',     (0,0), (-1,0), C_WHITE),
            ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,-1), 8),
            ('GRID',          (0,0), (-1,-1), 0.3, C_BORDER),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_ROW_ALT]),
            ('ALIGN',         (1,0), (-1,-1), 'CENTER'),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('LEFTPADDING',   (0,0), (-1,-1), 5),
        ]))
        story.append(catt)
        story.append(Spacer(1, 10))

    # Hallazgos completos
    story.append(Paragraph('6.2 Listado Completo de Hallazgos', S['FMH2']))
    if not all_findings:
        story.append(Paragraph('✅ No se registraron hallazgos en este caso.', S['FMBody']))
    else:
        story.append(findings_table(all_findings, S, show_scan_col=True))

    # ── 7. ARTEFACTOS FORENSES ────────────────────────────────────────────────
    if all_artifacts:
        section_header(story, 7, 'Artefactos Forenses', S)
        art_header = ['SCAN', 'CATEGORÍA', 'SUBCATEGORÍA', 'ARCHIVO', 'TAMAÑO', 'SHA-256']
        art_rows   = [art_header]
        for a in all_artifacts:
            art_rows.append([
                str(a['scan_id']),
                a['category'], a.get('subcategory') or '-',
                Paragraph(os.path.basename(a.get('source_path') or ''), S['FMSmall']),
                f'{a["size"]:,} B' if a.get('size') else '-',
                Paragraph((a.get('sha256') or '-')[:20] + '…'
                          if a.get('sha256') else '-', S['FMCode']),
            ])
        at = Table(art_rows, colWidths=[1.2*cm, 2.5*cm, 2.5*cm, None, 1.8*cm, 2.8*cm],
                   repeatRows=1)
        at.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), C_NAVY),
            ('TEXTCOLOR',     (0,0), (-1,0), C_WHITE),
            ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,-1), 7.5),
            ('GRID',          (0,0), (-1,-1), 0.3, C_BORDER),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_ROW_ALT]),
            ('TOPPADDING',    (0,0), (-1,-1), 3),
            ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ]))
        story.append(at)

    # ── 8. LÍNEA DE TIEMPO CONSOLIDADA ───────────────────────────────────────
    section_header(story, 8, 'Línea de Tiempo Consolidada', S)
    if not all_events:
        story.append(Paragraph('Sin eventos registrados en este caso.', S['FMBody']))
    else:
        # ordenar por timestamp
        sorted_events = sorted(all_events, key=lambda e: e.get('timestamp',''))
        story.append(Paragraph(
            f'Total de {len(sorted_events)} evento(s) registrados '
            f'(mostrando los primeros 200):', S['FMSmall']))
        story.append(Spacer(1, 4))
        story.append(events_table(sorted_events[:200], S))

    # ── 9. CONCLUSIÓN TÉCNICA ─────────────────────────────────────────────────
    section_header(story, 9, 'Conclusión Técnica', S)
    conclusion = (
        payload.get('conclusions') or
        f'El análisis forense del caso «{case_obj.name}» identificó '
        f'{len(all_findings)} hallazgo(s) distribuidos en '
        f'{len(global_cats)} categoría(s) distintas, con un nivel de riesgo '
        f'máximo de {RISK_LABEL.get(worst_risk, worst_risk)}. '
        f'La evidencia consolidada en este informe ha sido recolectada '
        f'mediante técnicas forenses no destructivas y su integridad puede '
        f'verificarse mediante los hashes SHA-256 documentados. '
        f'Se recomienda que este informe sea revisado y firmado por el '
        f'perito forense responsable antes de su presentación oficial.'
    )
    story.append(Paragraph(conclusion, S['FMBody']))

    # ── 10. INTEGRIDAD Y CADENA DE CUSTODIA ───────────────────────────────────
    section_header(story, 10, 'Integridad y Cadena de Custodia', S)
    story.append(info_grid([
        ('Archivo JSON',    json_path),
        ('SHA-256 JSON',    sha256(json_path)),
        ('Archivo PDF',     pdf_path),
        ('Generado en',     f'{ts(datetime.utcnow())} UTC'),
        ('Herramienta',     'Forense Móvil GT v2.1'),
        ('Plataforma',      f'{platform.system()} {platform.release()}'),
        ('Perito analista', payload.get('analyst_name', 'N/D')),
        ('Solicitado por',  payload.get('requested_by', 'N/D')),
    ], col_width=5*cm))

    # Espacio para firma
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width='40%', thickness=0.5, color=C_SLATE_LT))
    story.append(Paragraph(
        payload.get('analyst_name') or 'Perito Forense Responsable', S['FMSmall']))
    story.append(Paragraph('Firma y sello del analista', S['FMSmall']))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        'Forense Móvil GT — Documento generado automáticamente. '
        'Requiere validación pericial antes de uso en procesos legales.',
        S['FMFooter']))

    doc.build(story)

    return {
        'json_path':      json_path,
        'pdf_path':       pdf_path,
        'case_id':        case_obj.id,
        'case_name':      case_obj.name,
        'findings_count': len(all_findings),
        'events_count':   len(all_events),
        'scans_count':    len(scan_summaries),
        'worst_risk':     worst_risk,
        'json_sha256':    sha256(json_path),
    }

# variable global usada por helpers internos
_STYLES = None
