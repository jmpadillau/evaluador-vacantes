import streamlit as st
import pandas as pd
import io
import re
import requests
from bs4 import BeautifulSoup

# Modulos para la generación de reportes en PDF
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Afinia - Evaluador de Afinidad Laboral",
    page_icon="⚡",
    layout="wide"
)

# Estilos CSS personalizados para tarjetas y semáforo
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8fafc;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2a75d3;
        margin-bottom: 10px;
    }
    .badge-high {
        background-color: #d1e7dd;
        color: #0f5132;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .badge-mid {
        background-color: #fff3cd;
        color: #664d03;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .badge-low {
        background-color: #f8d7da;
        color: #842029;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# PERFIL PROFESIONAL DE MAURICIO (BASE DE CONOCIMIENTO)
# ---------------------------------------------------------
PROFILE = {
    "nombre": "Mauricio Padilla Ureña",
    "titulos": "M.Sc. en Sociología (UCR) | Bach. en Trabajo Social (UCR) | Esp. Mejora Continua (Fidélitas)",
    "idioma": "Inglés B2 Profesional / Fluido | Español Nativo",
    "experiencia_anios": "+8 años en RRHH, L&D, Relaciones Laborales y Gestión Educativa",
    "ubicacion": "Costa Rica (San José / Heredia / Alajuela / Coyol)",
    "hard_skills": [
        "L&D Strategy & Instructional Design (Job Instruction - JI, ADDIE)",
        "Employee Relations & Labor Law (Costa Rica)",
        "Investigaciones Laborales (Acoso Laboral / Hostigamiento Sexual)",
        "LMS Administration (Moodle, Workday, LearnDash)",
        "Excel Avanzado (VBA, Power Query) & Power BI (DAX)",
        "People Analytics & Métricas de Efectividad de Capacitación",
        "Mejora Continua de Procesos & Control de Cambios (ECOs)"
    ]
}

# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------
def fetch_url_text(url: str) -> str:
    """Extrae el contenido de texto de un enlace web."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator=' ')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return '\n'.join(chunk for chunk in chunks if chunk)
    except Exception as e:
        st.warning(f"No se pudo extraer texto automáticamente de la URL ({e}). Por favor, pega la descripción manualmente.")
    return ""

def extract_vacancy_details(job_text: str):
    """Extrae automáticamente metadatos clave de la vacante a partir del texto."""
    text_lower = job_text.lower()
    
    # Extracción de Puesto (Búsqueda heurística simple)
    lines = [line.strip() for line in job_text.splitlines() if line.strip()]
    puesto = lines[0] if len(lines) > 0 and len(lines[0]) < 80 else "Especialista / Analista de Puesto"
    
    # Empresa
    empresa = "Empresa Confidencial / Consultada"
    for line in lines[:10]:
        if any(kw in line.lower() for kw in ['inc', 'corp', 'cr', 'costa rica', 'sa', 's.a.', 'llc', 'company']):
            empresa = line
            break
            
    # Modalidad
    modalidad = "Híbrido / Presencial"
    if "remote" in text_lower or "remoto" in text_lower or "teletrabajo" in text_lower:
        modalidad = "Remoto"
    elif "hybrid" in text_lower or "híbrido" in text_lower:
        modalidad = "Híbrido"
    elif "onsite" in text_lower or "presencial" in text_lower:
        modalidad = "Presencial"
        
    # Ubicación
    ubicacion = "Costa Rica"
    for loc in ['alajuela', 'coyol', 'heredia', 'san josé', 'cartago', 'belén', 'santa ana']:
        if loc in text_lower:
            ubicacion = f"{loc.capitalize()}, Costa Rica"
            break
            
    # Horario / Nivel
    horario_nivel = "Tiempo Completo / Mid-Senior level"
    if "part time" in text_lower or "medio tiempo" in text_lower:
        horario_nivel = "Medio Tiempo / Profesional"
        
    # Salario
    salario = "No especificado en la oferta"
    salary_match = re.search(r'(\$|\b₡\b|\busd\b|\bcrc\b)\s?\d+([.,]\d+)?', text_lower)
    if salary_match:
        salario = salary_match.group(0).upper()
        
    # Sector
    sector = "Servicios Corporativos / Zonas Francas / Tecnología"
    if any(k in text_lower for k in ['manufactura', 'medical', 'farma', 'alimentos', 'lácteos']):
        sector = "Manufactura / Dispositivos Médicos / Alimentos"

    return {
        "puesto": puesto,
        "empresa": empresa,
        "modalidad": modalidad,
        "ubicacion": ubicacion,
        "horario_nivel": horario_nivel,
        "salario": salario,
        "sector": sector
    }

def analyze_vacancy(job_text: str):
    """Calcula la afinidad y construye la matriz detallada de requisitos y competencias."""
    details = extract_vacancy_details(job_text)
    text_lower = job_text.lower()
    
    # 1. Requisitos Técnicos y Herramientas (30%)
    tech_keywords = ['excel', 'vba', 'power bi', 'lms', 'moodle', 'workday', 'analytics', 'data', 'design', 'instructional', 'sop', 'kpi']
    tech_matches = [kw for kw in tech_keywords if kw in text_lower]
    tech_score = min(100.0, 70.0 + len(tech_matches) * 5.0)
    
    # 2. Experiencia Funcional y Dominio (30%)
    exp_keywords = ['learning', 'development', 'l&d', 'hr', 'human resources', 'training', 'employee relations', 'capacitación', 'talent', 'management']
    exp_matches = [kw for kw in exp_keywords if kw in text_lower]
    exp_score = min(100.0, 75.0 + len(exp_matches) * 5.0)
    
    # 3. Formación Académica e Idiomas (15%)
    edu_score = 97.5 if any(k in text_lower for k in ['b2', 'english', 'inglés', 'bachelor', 'licenciatura', 'master']) else 90.0
    
    # 4. Competencias y Habilidades Blandas (15%)
    soft_score = 100.0 if any(k in text_lower for k in ['leadership', 'communication', 'stakeholder', 'liderazgo', 'consulting', 'collaboration']) else 90.0
    
    # 5. Contexto / Deseables (10%)
    context_score = 100.0 if any(k in text_lower for k in ['costa rica', 'heredia', 'san josé', 'alajuela', 'remote', 'remoto', 'multinational', 'hybrid', 'híbrido']) else 85.0
    
    weights = {'tech': 0.30, 'exp': 0.30, 'edu': 0.15, 'soft': 0.15, 'context': 0.10}
    total_affinity = (
        tech_score * weights['tech'] +
        exp_score * weights['exp'] +
        edu_score * weights['edu'] +
        soft_score * weights['soft'] +
        context_score * weights['context']
    )
    
    # Desglose de Requisitos (Columna "Requisitos" en lugar de "Dimensión")
    requisitos_desglose = [
        {
            "Requisitos Solicitados por la Vacante": "Requisitos Técnicos y Herramientas (LMS, Power BI, Excel VBA, People Analytics, Diseño Instruccional)",
            "Puntaje (0-100)": f"{tech_score:.1f}",
            "Justificación del Puntaje / Evidencia en el Perfil": "Dominio avanzado en diseño de arquitecturas curriculares, rutas de aprendizaje, LMS/Moodle, Workday, Power BI (DAX) y tableros de control de entrenamiento."
        },
        {
            "Requisitos Solicitados por la Vacante": "Experiencia Funcional y Dominio (+5 años en L&D, RRHH, Relaciones Laborales y Capacitación Corporativa)",
            "Puntaje (0-100)": f"{exp_score:.1f}",
            "Justificación del Puntaje / Evidencia en el Perfil": "+8 años en L&D, gestión de capacitación corporativa en Abbott (Zona Franca Coyol) y +8 años en dirección académica/proyectos universitarios."
        },
        {
            "Requisitos Solicitados por la Vacante": "Formación Académica e Idiomas (Grado Universitario afín a Gestión Humana/Educación + Inglés B2)",
            "Puntaje (0-100)": f"{edu_score:.1f}",
            "Justificación del Puntaje / Evidencia en el Perfil": "M.Sc. en Sociología y Bach. en Trabajo Social (UCR); Esp. Mejora Continua (Fidélitas). Posgrado afín a gestión humana/educación + Inglés B2 verificado."
        },
        {
            "Requisitos Solicitados por la Vacante": "Competencias y Habilidades Blandas (Pensamiento Estratégico, Liderazgo, Gestión de Stakeholders y Análisis)",
            "Puntaje (0-100)": f"{soft_score:.1f}",
            "Justificación del Puntaje / Evidencia en el Perfil": "Pensamiento estratégico, visión sistémica, liderazgo probado (20 docentes a nivel nacional), influencia, análisis de datos y disciplina de ejecución."
        },
        {
            "Requisitos Solicitados por la Vacante": "Contexto / Deseables (Ubicación en Costa Rica, Entorno Multinacional, Zonas Francas o Remoto)",
            "Puntaje (0-100)": f"{context_score:.1f}",
            "Justificación del Puntaje / Evidencia en el Perfil": "Ubicación geográfica idónea, experiencia previa en multinacionales (Abbott, BMA Group) y certificaciones en Mejora Continua y Analytics."
        }
    ]
    
    # Matriz de Competencias del Puesto vs. Candidato
    matriz_competencias = [
        {"#": 1, "Requisito / Competencia Solicitada": "Estrategia y hoja de ruta de academias corporativas / L&D alineadas al negocio", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Diseño e implementación de itinerarios NPI en Abbott y arquitectura curricular universitaria."},
        {"#": 2, "Requisito / Competencia Solicitada": "Diseño de modelos, metodologías y arquitecturas curriculares sostenibles", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Metodología Job Instruction (JI), diseño instruccional y proyectos educativos de impacto."},
        {"#": 3, "Requisito / Competencia Solicitada": "Implementación del plan anual de formación, cronogramas y plataformas LMS", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Administración de cambios de calidad (ECOs), plataformas LMS (Moodle, Workday) y recursos."},
        {"#": 4, "Requisito / Competencia Solicitada": "Gestión de indicadores de desempeño y tableros de control de aprendizaje", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Desarrollo de tableros ejecutivos en Power BI (DAX) y automatización con macros Excel VBA."},
        {"#": 5, "Requisito / Competencia Solicitada": "Articulación con líderes, especialistas, proveedores e instituciones educativas", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Coordinación de proveedores, convenios RSE, equipo de 20 docentes e interacción multifuncional."},
        {"#": 6, "Requisito / Competencia Solicitada": "Experiencia mínima de 5 años en L&D, universidades o academias corporativas", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "+8 años acumulados en L&D corporativo en Abbott y dirección educativa en educación superior."},
        {"#": 7, "Requisito / Competencia Solicitada": "Licenciatura en Área Social, Administración, Ingeniería Industrial o área afín", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Maestría M.Sc. en Sociología y Bach. en Trabajo Social (UCR) con posgrado enfocado en gestión."},
        {"#": 8, "Requisito / Competencia Solicitada": "Dominio de herramientas digitales de aprendizaje y análisis de datos", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Experto en Power BI, Power Query, VBA, Workday, LMS y modelos cuantitativos de People Analytics."},
        {"#": 9, "Requisito / Competencia Solicitada": "Deseable liderazgo o coordinación de equipos y frentes complejos", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Selección, formación y supervisión de 20 docentes a nivel nacional en 7 sedes universitarias."},
        {"#": 10, "Requisito / Competencia Solicitada": "Formación en L&D, Diseño Instruccional, Mejora Continua e Inglés B2", "Existente": "X", "Inexistente": "", "Detalle / Evidencia en el Perfil": "Esp. en Mejora Continua (U. Fidélitas), cert. en Analytics (UNA) y nivel de Inglés B2 verificado."}
    ]

    return {
        "details": details,
        "total_affinity": round(total_affinity, 2),
        "requisitos_desglose": requisitos_desglose,
        "matriz_competencias": matriz_competencias
    }

def generate_pdf_bytes(analysis):
    """Genera el reporte PDF completo manteniendo el diseño oficial."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    
    styles = getSampleStyleSheet()
    primary = colors.HexColor("#0f2a4a")
    secondary = colors.HexColor("#1b4d82")
    accent = colors.HexColor("#2a75d3")
    dark_gray = colors.HexColor("#2c3e50")
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, textColor=primary, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=secondary, alignment=TA_CENTER, spaceAfter=8)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, textColor=primary, spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=dark_gray, leading=10)
    body_bold = ParagraphStyle('BodyBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=dark_gray, leading=10)
    table_head = ParagraphStyle('TableHead', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, alignment=TA_CENTER)
    
    story = []
    
    # Encabezado
    story.append(Paragraph("Afinia — ANÁLISIS DE PLAZA VACANTE", title_style))
    story.append(Paragraph("Evaluación de Afinidad Perfil Profesional vs. Requerimientos del Puesto", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent, spaceAfter=8))
    
    det = analysis['details']
    aff = analysis['total_affinity']
    
    if aff >= 85:
        verdict = f"Sí — Recomendado (Afinidad Alta ≥ 85%)"
        adjust_cv = "Sí (Enfoque en L&D, Academias y Analytics)"
    elif aff >= 70:
        verdict = f"Evaluar (Afinidad Media 70%-84%)"
        adjust_cv = "Sí (Adaptar competencias transferibles)"
    else:
        verdict = f"No Recomendado (Afinidad Baja < 70%)"
        adjust_cv = "Revisar brechas indispensables"

    # Cuadro 1: Detalle de Vacante
    summary_data = [
        [Paragraph(f"<b>Puesto:</b> {det['puesto']}", body_style), Paragraph(f"<b>% Afinidad:</b> <b>{aff:.2f}%</b>", body_bold)],
        [Paragraph(f"<b>Empresa:</b> {det['empresa']}", body_style), Paragraph(f"<b>¿Aplicar?:</b> {verdict}", body_bold)],
        [Paragraph(f"<b>Ubicación:</b> {det['ubicacion']}", body_style), Paragraph(f"<b>¿Ajustar CV?:</b> {adjust_cv}", body_style)],
        [Paragraph(f"<b>Horario / Nivel:</b> {det['horario_nivel']}", body_style), Paragraph(f"<b>Sector:</b> {det['sector']}", body_style)],
        [Paragraph(f"<b>Modalidad:</b> {det['modalidad']}", body_style), Paragraph(f"<b>Salario:</b> {det['salario']}", body_style)]
    ]
    t_summary = Table(summary_data, colWidths=[270, 270])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f4f7f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d7de")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 8))
    
    # Sección 1: Desglose de Requisitos
    story.append(Paragraph("1. DESGLOSE DE PONDERACIÓN POR REQUISITOS", h2_style))
    req_headers = [Paragraph("Requisitos Solicitados por la Vacante", table_head), Paragraph("Puntaje", table_head), Paragraph("Justificación del Puntaje / Evidencia en el Perfil", table_head)]
    req_rows = [req_headers]
    
    for row in analysis['requisitos_desglose']:
        req_rows.append([
            Paragraph(f"<b>{row['Requisitos Solicitados por la Vacante']}</b>", body_style),
            Paragraph(f"{row['Puntaje (0-100)']} pts", ParagraphStyle('C', parent=body_style, alignment=TA_CENTER)),
            Paragraph(row['Justificación del Puntaje / Evidencia en el Perfil'], body_style)
        ])
        
    t_req = Table(req_rows, colWidths=[200, 60, 280])
    t_req.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d7de")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_req)
    story.append(Spacer(1, 8))
    
    # Sección 2: Matriz de Competencias
    story.append(Paragraph("2. MATRIZ DE COMPETENCIAS DEL PUESTO VS. CANDIDATO", h2_style))
    comp_headers = [Paragraph("#", table_head), Paragraph("Requisito / Competencia Solicitada", table_head), Paragraph("Existente", table_head), Paragraph("Inexistente", table_head), Paragraph("Detalle / Evidencia en el Perfil de Mauricio", table_head)]
    comp_rows = [comp_headers]
    
    for row in analysis['matriz_competencias']:
        comp_rows.append([
            Paragraph(str(row['#']), ParagraphStyle('C', parent=body_style, alignment=TA_CENTER)),
            Paragraph(row['Requisito / Competencia Solicitada'], body_style),
            Paragraph(f"<b>{row['Existente']}</b>", ParagraphStyle('C', parent=body_bold, alignment=TA_CENTER)),
            Paragraph(row['Inexistente'], ParagraphStyle('C', parent=body_style, alignment=TA_CENTER)),
            Paragraph(row['Detalle / Evidencia en el Perfil'], body_style)
        ])
        
    t_comp = Table(comp_rows, colWidths=[20, 180, 45, 45, 250])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d7de")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 8))
    
    # Sección 3: Acciones y Recomendaciones
    story.append(Paragraph("3. ACCIONES Y RECOMENDACIONES PARA EL CV", h2_style))
    recs = [
        f"<b>1. Titular Sugerido para el CV:</b> Presentar la postulación como '<i>{det['puesto']} | L&D & Analytics Specialist</i>'.",
        "<b>2. Enfoque en Academias Corporativas y Rutas de Aprendizaje:</b> Resaltar en primer plano el diseño de itinerarios formativos NPI en Abbott, arquitectura curricular y la metodología Job Instruction (JI).",
        "<b>3. Visibilizar Liderazgo y Gobernanza:</b> Destacar la dirección del equipo nacional de 20 docentes en 7 sedes y la gestión de convenios/RSE.",
        "<b>4. Destacar Analítica e Indicadores:</b> Subrayar la creación de tableros en Power BI para medir efectividad del entrenamiento, cobertura y ROI en capacitación."
    ]
    for r in recs:
        story.append(Paragraph(r, body_style))
        story.append(Spacer(1, 2))
        
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------------------------------------
# INTERFAZ DE USUARIO EN STREAMLIT
# ---------------------------------------------------------
st.title("⚡ Afinia")
st.caption("Sistema Inteligente de Evaluación de Afinidad Perfil Profesional vs. Ofertas Laborales")

with st.sidebar:
    st.header("👤 Perfil Profesional Base")
    st.write(f"**Nombre:** {PROFILE['nombre']}")
    st.write(f"**Títulos:** {PROFILE['titulos']}")
    st.write(f"**Idiomas:** {PROFILE['idioma']}")
    st.write(f"**Experiencia:** {PROFILE['experiencia_anios']}")
    st.write(f"**Ubicación:** {PROFILE['ubicacion']}")
    st.divider()
    st.subheader("🛠️ Competencias Clave")
    for skill in PROFILE['hard_skills']:
        st.markdown(f"- {skill}")

st.subheader("📋 Evaluación de Oferta Laboral")
url_input = st.text_input("🔗 Enlace / URL de la Vacante (Opcional):", placeholder="https://...")
job_description = st.text_area("📄 Texto o Descripción de la Oferta Laboral:", height=180, placeholder="Pega aquí el contenido completo de la vacante...")

if st.button("🚀 Analizar Afinidad de Vacante", type="primary"):
    if not job_description and url_input:
        with st.spinner("Extrayendo texto del enlace suministrado..."):
            extracted_text = fetch_url_text(url_input)
            if extracted_text:
                job_description = extracted_text
                st.success("Texto extraído exitosamente del enlace.")
    
    if not job_description:
        st.error("Por favor, ingresa el texto de la oferta o un enlace válido para realizar el análisis.")
    else:
        analysis = analyze_vacancy(job_description)
        det = analysis['details']
        aff = analysis['total_affinity']
        
        st.divider()
        st.header("📊 ANÁLISIS DE PLAZA VACANTE")
        st.caption("Evaluación de Afinidad Perfil Profesional vs. Requerimientos del Puesto")
        
        # --- TARJETA CABECERA PRINCIPAL CON SEMÁFORO ---
        if aff >= 85:
            badge_html = f'<span class="badge-high">🟢 AFINIDAD ALTA ({aff:.2f}%) — SÍ RECOMENDADO</span>'
            aplicar_str = "SÍ — Recomendado (Afinidad Alta ≥ 85%)"
            ajustar_cv_str = "Sí (Enfoque en Academias Corporativas, L&D y Analytics)"
        elif aff >= 70:
            badge_html = f'<span class="badge-mid">🟡 AFINIDAD MEDIA ({aff:.2f}%) — AJUSTAR CV</span>'
            aplicar_str = "EVALUAR CON AJUSTES (Afinidad Media 70%-84%)"
            ajustar_cv_str = "Sí (Adaptar competencias transferibles)"
        else:
            badge_html = f'<span class="badge-low">🔴 AFINIDAD BAJA ({aff:.2f}%) — NO RECOMENDADO</span>'
            aplicar_str = "NO RECOMENDADO (Afinidad Baja < 70%)"
            ajustar_cv_str = "Revisar brechas indispensables"

        st.markdown(f"### Dictamen Final: {badge_html}", unsafe_allow_html=True)
        st.write("")
        
        # Grid de Detalles Extraídos
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Puesto:** {det['puesto']}")
            st.markdown(f"**Empresa:** {det['empresa']}")
            st.markdown(f"**Ubicación:** {det['ubicacion']}")
            st.markdown(f"**Horario / Nivel:** {det['horario_nivel']}")
        with col2:
            st.markdown(f"**% Afinidad:** **{aff:.2f}%**")
            st.markdown(f"**¿Aplicar?:** {aplicar_str}")
            st.markdown(f"**¿Ajustar CV?:** {ajustar_cv_str}")
            st.markdown(f"**Modalidad / Salario:** {det['modalidad']} | {det['salario']}")
            
        st.divider()
        
        # --- SECCIÓN 1: DESGLOSE DE REQUISITOS ---
        st.subheader("1. DESGLOSE DE PONDERACIÓN POR REQUISITOS")
        df_req = pd.DataFrame(analysis['requisitos_desglose'])
        st.dataframe(df_req, use_container_width=True, hide_index=True)
        
        # --- SECCIÓN 2: MATRIZ DE COMPETENCIAS ---
        st.subheader("2. MATRIZ DE COMPETENCIAS DEL PUESTO VS. CANDIDATO")
        df_comp = pd.DataFrame(analysis['matriz_competencias'])
        st.dataframe(df_comp, use_container_width=True, hide_index=True)
        
        # --- SECCIÓN 3: ACCIONES Y RECOMENDACIONES ---
        st.subheader("3. ACCIONES Y RECOMENDACIONES PARA EL CV")
        st.markdown(f"1. **Titular Sugerido para el CV:** Presentar la postulación como *'{det['puesto']} | L&D & Analytics Specialist'*.")
        st.markdown("2. **Enfoque en Academias Corporativas y Rutas de Aprendizaje:** Resaltar en primer plano el diseño de itinerarios formativos NPI en Abbott Coyol, la arquitectura curricular universitaria y la metodología Job Instruction (JI).")
        st.markdown("3. **Visibilizar Liderazgo y Gobernanza:** Destacar la dirección del equipo nacional de 20 docentes en 7 sedes y la gestión de convenios/RSE.")
        st.markdown("4. **Destacar la Analítica e Indicadores:** Subrayar la creación de tableros en Power BI para medir la efectividad del entrenamiento, cobertura y retorno de inversión en capacitación.")
        
        st.divider()
        
        # --- BOTÓN DE DESCARGA PDF ---
        pdf_bytes = generate_pdf_bytes(analysis)
        st.download_button(
            label="📄 Descargar Informe Oficial en PDF",
            data=pdf_bytes,
            file_name=f"Analisis_Plaza_Vacante_{det['empresa'].replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary"
        )