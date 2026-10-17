import streamlit as st
import pandas as pd
import io
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
    page_title="Evaluador de Vacantes - Mauricio Padilla",
    page_icon="💼",
    layout="wide"
)

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
        "Mejora Continua de Procesos & Control de Cambios (ECOs)",
        "Gobernanza Educativa & Dirección Académica"
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

def analyze_vacancy(job_text: str):
    """Calcula la afinidad ponderada según la matriz formal de 5 dimensiones."""
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
    edu_score = 95.0 if any(k in text_lower for k in ['b2', 'english', 'inglés', 'bachelor', 'licenciatura', 'master']) else 90.0
    
    # 4. Competencias y Habilidades Blandas (15%)
    soft_score = 100.0 if any(k in text_lower for k in ['leadership', 'communication', 'stakeholder', 'liderazgo', 'consulting', 'collaboration']) else 90.0
    
    # 5. Contexto / Deseables (10%)
    context_score = 100.0 if any(k in text_lower for k in ['costa rica', 'heredia', 'san josé', 'alajuela', 'remote', 'remoto', 'multinational', 'hybrid', 'híbrido']) else 85.0
    
    # Cálculo Ponderado
    weights = {'tech': 0.30, 'exp': 0.30, 'edu': 0.15, 'soft': 0.15, 'context': 0.10}
    total_affinity = (
        tech_score * weights['tech'] +
        exp_score * weights['exp'] +
        edu_score * weights['edu'] +
        soft_score * weights['soft'] +
        context_score * weights['context']
    )
    
    return {
        'total_affinity': round(total_affinity, 2),
        'dim_scores': {
            'Requisitos Técnicos y Herramientas (30%)': (tech_score, round(tech_score * 0.30, 2), "Dominio de LMS, Power BI, Excel VBA, People Analytics y diseño instruccional."),
            'Experiencia Funcional y Dominio (30%)': (exp_score, round(exp_score * 0.30, 2), "+8 años en L&D, RRHH, relaciones laborales e itinerarios formativos en multinacionales."),
            'Formación Académica e Idiomas (15%)': (edu_score, round(edu_score * 0.15, 2), "M.Sc. en Sociología, Bach. Trabajo Social, Esp. Mejora Continua e Inglés B2 verificado."),
            'Competencias y Habilidades Blandas (15%)': (soft_score, round(soft_score * 0.15, 2), "Consultoría interna, gestión de stakeholders, liderazgo de 20 docentes y mediación."),
            'Contexto / Deseables (10%)': (context_score, round(context_score * 0.10, 2), "Ubicación en Costa Rica y trayectoria en entornos corporativos de zona franca.")
        }
    }

def generate_pdf_bytes(puesto, empresa, analysis):
    """Genera el reporte PDF en formato oficial y retorna los bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    
    styles = getSampleStyleSheet()
    primary = colors.HexColor("#0f2a4a")
    secondary = colors.HexColor("#1b4d82")
    accent = colors.HexColor("#2a75d3")
    dark_gray = colors.HexColor("#2c3e50")
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=primary, alignment=TA_CENTER, spaceAfter=6)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=secondary, alignment=TA_CENTER, spaceAfter=12)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, textColor=primary, spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=dark_gray, leading=12)
    body_bold = ParagraphStyle('BodyBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=dark_gray, leading=12)
    table_head = ParagraphStyle('TableHead', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=TA_CENTER)
    
    story = []
    
    story.append(Paragraph("INFORME DE EVALUACIÓN DE PLAZA VACANTE", title_style))
    story.append(Paragraph(f"Candidato: Mauricio Padilla Ureña | Puesto: {puesto} - {empresa}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent, spaceAfter=10))
    
    aff = analysis['total_affinity']
    verdict = "SÍ — RECOMENDADO" if aff >= 85 else ("EVALUAR CON AJUSTES" if aff >= 70 else "NO RECOMENDADO")
    
    summary_data = [
        [Paragraph("<b>Puesto Evaluado:</b>", body_style), Paragraph(puesto, body_style), Paragraph("<b>Porcentaje de Afinidad:</b>", body_style), Paragraph(f"<b>{aff:.2f}%</b>", body_bold)],
        [Paragraph("<b>Empresa / Organización:</b>", body_style), Paragraph(empresa, body_style), Paragraph("<b>Dictamen Final:</b>", body_style), Paragraph(f"<b>{verdict}</b>", body_bold)]
    ]
    t_summary = Table(summary_data, colWidths=[120, 180, 120, 120])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f4f7f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d7de")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("1. Desglose de Ponderación por Dimensiones", h2_style))
    dim_headers = [Paragraph("Dimensión de Evaluación", table_head), Paragraph("Peso", table_head), Paragraph("Puntaje", table_head), Paragraph("Aporte", table_head), Paragraph("Justificación", table_head)]
    dim_rows = [dim_headers]
    
    for dim_name, (score, weighted, desc) in analysis['dim_scores'].items():
        peso = "30%" if "30%" in dim_name else ("15%" if "15%" in dim_name else "10%")
        clean_name = dim_name.split('(')[0].strip()
        dim_rows.append([
            Paragraph(f"<b>{clean_name}</b>", body_style),
            Paragraph(peso, ParagraphStyle('C', parent=body_style, alignment=TA_CENTER)),
            Paragraph(f"{score:.1f} pts", ParagraphStyle('C', parent=body_style, alignment=TA_CENTER)),
            Paragraph(f"{weighted:.2f}%", ParagraphStyle('C', parent=body_style, alignment=TA_CENTER)),
            Paragraph(desc, body_style)
        ])
    
    t_dim = Table(dim_rows, colWidths=[140, 45, 55, 55, 245])
    t_dim.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#d0d7de")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_dim)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("2. Recomendaciones Estratégicas para la Postulación", h2_style))
    recs = [
        f"<b>Titular Profesional Recomendado:</b> Encabezar la postulación como <i>{puesto} | L&D & Analytics Specialist</i>.",
        "<b>Enfoque de Experiencia:</b> Posicionar en primer plano la experiencia en L&D corporativo, diseño instruccional (Job Instruction) y desarrollo de tableros de efectividad en Power BI.",
        "<b>Visibilidad de Logros:</b> Resaltar la automatización de procesos en Excel VBA/Power Query y el liderazgo de equipos de trabajo."
    ]
    for r in recs:
        story.append(Paragraph(f"• {r}", body_style))
        story.append(Spacer(1, 3))
        
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------------------------------------
# INTERFAZ DE USUARIO EN STREAMLIT
# ---------------------------------------------------------
st.title("💼 Evaluador de Vacantes - Mauricio Padilla Ureña")
st.markdown("Herramienta interactiva para la evaluación cuantitativa y cualitativa de ofertas laborales frente al perfil profesional de Mauricio.")

with st.sidebar:
    st.header("👤 Perfil de Mauricio")
    st.write(f"**Nombre:** {PROFILE['nombre']}")
    st.write(f"**Títulos:** {PROFILE['titulos']}")
    st.write(f"**Idiomas:** {PROFILE['idioma']}")
    st.write(f"**Experiencia:** {PROFILE['experiencia_anios']}")
    st.write(f"**Ubicación:** {PROFILE['ubicacion']}")
    st.divider()
    st.subheader("🛠️ Competencias Clave")
    for skill in PROFILE['hard_skills'][:5]:
        st.markdown(f"- {skill}")

st.subheader("📋 Datos de la Vacante a Evaluar")
col1, col2 = st.columns(2)
with col1:
    puesto_input = st.text_input("Nombre del Puesto / Posición:", placeholder="Ej. L&D Specialist / HR Advisor")
with col2:
    empresa_input = st.text_input("Empresa u Organización:", placeholder="Ej. Citi / Deloitte / Abbott")

url_input = st.text_input("🔗 Enlace / URL de la Vacante (Opcional):", placeholder="https://...")
job_description = st.text_area("📄 Texto de la Oferta Laboral (Requisitos, Funciones, Competencias):", height=180, placeholder="Pega aquí el texto completo de la vacante...")

if st.button("🚀 Evaluar Vacante", type="primary"):
    if not job_description and url_input:
        with st.spinner("Extrayendo información del enlace..."):
            extracted_text = fetch_url_text(url_input)
            if extracted_text:
                job_description = extracted_text
                st.success("Texto extraído con éxito del enlace.")
    
    if not job_description:
        st.error("Por favor, ingresa el texto de la vacante o un enlace válido para realizar la evaluación.")
    else:
        puesto = puesto_input if puesto_input else "Posición Evaluada"
        empresa = empresa_input if empresa_input else "Empresa"
        
        analysis = analyze_vacancy(job_description)
        aff = analysis['total_affinity']
        
        st.divider()
        st.header(f"📊 Resultado del Análisis: {puesto} en {empresa}")
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Porcentaje de Afinidad", f"{aff:.2f}%")
        with m_col2:
            if aff >= 85:
                st.success("🟢 AFINIDAD ALTA (≥ 85%) — SÍ APLICAR")
            elif aff >= 70:
                st.warning("🟡 AFINIDAD MEDIA (70% - 84%) — AJUSTAR CV")
            else:
                st.error("🔴 AFINIDAD BAJA (< 70%) — REVISAR BRECHAS")
        with m_col3:
            st.info(" Dictamen: Postulación Recomendada")
            
        st.subheader("1. Desglose de Ponderación por Dimensiones")
        table_data = []
        for dim, (score, weighted, desc) in analysis['dim_scores'].items():
            peso = "30%" if "30%" in dim else ("15%" if "15%" in dim else "10%")
            clean_dim = dim.split('(')[0].strip()
            table_data.append({
                "Dimensión": clean_dim,
                "Peso": peso,
                "Puntaje (0-100)": f"{score:.1f} pts",
                "Aporte (%)": f"{weighted:.2f}%",
                "Justificación / Evidencia": desc
            })
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
        
        pdf_bytes = generate_pdf_bytes(puesto, empresa, analysis)
        st.download_button(
            label="📄 Descargar Informe Oficial en PDF",
            data=pdf_bytes,
            file_name=f"Analisis_Plaza_Vacante_{empresa.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )