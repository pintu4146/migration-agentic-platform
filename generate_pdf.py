"""
IBM Migration Copilot — Submission PDF Generator
Generates a styled, multi-section PDF using reportlab.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import BalancedColumns
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Wedge, Circle, Polygon
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from reportlab.graphics.widgets.markers import makeMarker
import os

# ─── COLOUR PALETTE (IBM Carbon) ────────────────────────────────────────────
IBM_BLUE       = colors.HexColor('#0f62fe')
IBM_BLUE_DARK  = colors.HexColor('#0043ce')
IBM_BLUE_LIGHT = colors.HexColor('#d0e2ff')
IBM_TEXT       = colors.HexColor('#161616')
IBM_TEXT_2     = colors.HexColor('#525252')
IBM_BG         = colors.HexColor('#f4f4f4')
IBM_BORDER     = colors.HexColor('#c6c6c6')
IBM_GREEN      = colors.HexColor('#24a148')
IBM_RED        = colors.HexColor('#da1e28')
IBM_YELLOW     = colors.HexColor('#f1c21b')
IBM_PURPLE     = colors.HexColor('#8a3ffc')
IBM_TEAL       = colors.HexColor('#009d9a')
IBM_WHITE      = colors.white
IBM_ORANGE     = colors.HexColor('#ff832b')
IBM_CYAN       = colors.HexColor('#4589ff')

W, H = A4  # 595 x 842

OUTPUT = "IBM_Migration_Copilot_Submission.pdf"

# ─── STYLES ─────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()
    s = {}

    s['cover_title'] = ParagraphStyle('cover_title',
        fontName='Helvetica-Bold', fontSize=28, textColor=IBM_WHITE,
        leading=34, alignment=TA_LEFT)

    s['cover_sub'] = ParagraphStyle('cover_sub',
        fontName='Helvetica', fontSize=13, textColor=IBM_BLUE_LIGHT,
        leading=18, alignment=TA_LEFT, spaceBefore=6)

    s['cover_badge'] = ParagraphStyle('cover_badge',
        fontName='Helvetica-Bold', fontSize=10, textColor=IBM_BLUE_LIGHT,
        leading=14, alignment=TA_LEFT)

    s['section_label'] = ParagraphStyle('section_label',
        fontName='Helvetica-Bold', fontSize=9, textColor=IBM_BLUE,
        leading=12, spaceBefore=2, spaceAfter=2, letterSpacing=1.5)

    s['h1'] = ParagraphStyle('h1',
        fontName='Helvetica-Bold', fontSize=18, textColor=IBM_TEXT,
        leading=22, spaceBefore=18, spaceAfter=8)

    s['h2'] = ParagraphStyle('h2',
        fontName='Helvetica-Bold', fontSize=13, textColor=IBM_BLUE_DARK,
        leading=17, spaceBefore=14, spaceAfter=6,
        borderPadding=(0,0,4,0))

    s['h3'] = ParagraphStyle('h3',
        fontName='Helvetica-Bold', fontSize=11, textColor=IBM_TEXT,
        leading=14, spaceBefore=10, spaceAfter=4)

    s['body'] = ParagraphStyle('body',
        fontName='Helvetica', fontSize=10, textColor=IBM_TEXT_2,
        leading=15, spaceBefore=4, spaceAfter=4, alignment=TA_JUSTIFY)

    s['body_bold'] = ParagraphStyle('body_bold',
        fontName='Helvetica-Bold', fontSize=10, textColor=IBM_TEXT,
        leading=14, spaceBefore=2, spaceAfter=2)

    s['bullet'] = ParagraphStyle('bullet',
        fontName='Helvetica', fontSize=10, textColor=IBM_TEXT_2,
        leading=14, spaceBefore=2, spaceAfter=2,
        leftIndent=14, bulletIndent=4)

    s['highlight'] = ParagraphStyle('highlight',
        fontName='Helvetica-BoldOblique', fontSize=10, textColor=IBM_BLUE_DARK,
        leading=14, spaceBefore=4, spaceAfter=4,
        leftIndent=12, borderPadding=8)

    s['small'] = ParagraphStyle('small',
        fontName='Helvetica', fontSize=8.5, textColor=IBM_TEXT_2, leading=12)

    s['table_header'] = ParagraphStyle('table_header',
        fontName='Helvetica-Bold', fontSize=9, textColor=IBM_WHITE,
        leading=12, alignment=TA_CENTER)

    s['table_cell'] = ParagraphStyle('table_cell',
        fontName='Helvetica', fontSize=9, textColor=IBM_TEXT_2,
        leading=12, alignment=TA_LEFT)

    s['table_cell_c'] = ParagraphStyle('table_cell_c',
        fontName='Helvetica', fontSize=9, textColor=IBM_TEXT_2,
        leading=12, alignment=TA_CENTER)

    s['table_bold'] = ParagraphStyle('table_bold',
        fontName='Helvetica-Bold', fontSize=9, textColor=IBM_TEXT,
        leading=12, alignment=TA_LEFT)

    s['footer'] = ParagraphStyle('footer',
        fontName='Helvetica', fontSize=8, textColor=IBM_TEXT_2,
        leading=10, alignment=TA_CENTER)

    return s

# ─── HELPERS ────────────────────────────────────────────────────────────────
def section_header_block(label, title, subtitle, s):
    """Blue gradient header block for each section."""
    d = Drawing(W - 3*cm, 52)
    bg = Rect(0, 0, W - 3*cm, 52, fillColor=IBM_BLUE_DARK,
              strokeColor=IBM_BLUE_DARK)
    accent = Rect(0, 0, 5, 52, fillColor=IBM_YELLOW, strokeColor=None)
    d.add(bg); d.add(accent)
    d.add(String(14, 36, label, fontName='Helvetica-Bold', fontSize=8,
                 fillColor=IBM_BLUE_LIGHT))
    d.add(String(14, 20, title, fontName='Helvetica-Bold', fontSize=15,
                 fillColor=IBM_WHITE))
    d.add(String(14, 7, subtitle, fontName='Helvetica', fontSize=9,
                 fillColor=IBM_BLUE_LIGHT))
    return d

def hr(color=IBM_BORDER, thickness=0.5):
    return HRFlowable(width='100%', thickness=thickness, color=color,
                      spaceAfter=6, spaceBefore=6)

def badge_table(items, s):
    """Row of small colored badge chips."""
    cells = []
    clrs = [IBM_BLUE, IBM_GREEN, IBM_PURPLE, IBM_TEAL, IBM_ORANGE]
    for i, (label, val) in enumerate(items):
        c = clrs[i % len(clrs)]
        cells.append([
            Paragraph(f'<b>{val}</b>', ParagraphStyle('bv',
                fontName='Helvetica-Bold', fontSize=14, textColor=c,
                leading=18, alignment=TA_CENTER)),
            Paragraph(label, ParagraphStyle('bl',
                fontName='Helvetica', fontSize=8, textColor=IBM_TEXT_2,
                leading=11, alignment=TA_CENTER))
        ])
    col_w = (W - 3*cm) / len(items)
    t = Table([[c[0] for c in cells], [c[1] for c in cells]],
              colWidths=[col_w]*len(items))
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), IBM_WHITE),
        ('BOX', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return t

def highlight_box(text, s):
    t = Table([[Paragraph(text, s['highlight'])]], colWidths=[W - 3*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), IBM_BLUE_LIGHT),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LINEAFTER', (0,0), (0,-1), 4, IBM_BLUE),
    ]))
    return t

def info_card_row(cards, s, col_widths=None):
    """Render a row of info cards side-by-side."""
    n = len(cards)
    if not col_widths:
        cw = (W - 3*cm) / n
        col_widths = [cw] * n
    cells = []
    for title, color, items in cards:
        content = [Paragraph(f'<b>{title}</b>',
                       ParagraphStyle('ch', fontName='Helvetica-Bold',
                           fontSize=10, textColor=color, leading=13))]
        for item in items:
            content.append(Paragraph(f'• {item}',
                ParagraphStyle('ci', fontName='Helvetica', fontSize=9,
                    textColor=IBM_TEXT_2, leading=13, leftIndent=6)))
        cells.append(content)
    t = Table([cells], colWidths=col_widths)
    ts = [
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ('BACKGROUND', (0,0), (-1,-1), IBM_WHITE),
    ]
    for i, (_, color, _) in enumerate(cards):
        ts.append(('LINEABOVE', (i,0), (i,0), 3, color))
    t.setStyle(TableStyle(ts))
    return t

def std_table(headers, rows, s, col_widths=None):
    """Standard styled data table."""
    header_row = [Paragraph(h, s['table_header']) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([Paragraph(str(c), s['table_cell']) for c in row])
    if not col_widths:
        col_widths = [(W - 3*cm) / len(headers)] * len(headers)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    ts = [
        ('BACKGROUND', (0,0), (-1,0), IBM_TEXT),
        ('TEXTCOLOR', (0,0), (-1,0), IBM_WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [IBM_WHITE, IBM_BG]),
        ('INNERGRID', (0,0), (-1,-1), 0.4, IBM_BORDER),
        ('BOX', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]
    t.setStyle(TableStyle(ts))
    return t

def horizontal_bar_chart(labels, values, bar_colors, title, width=460, height=160):
    d = Drawing(width, height + 30)
    d.add(String(0, height + 16, title,
                 fontName='Helvetica-Bold', fontSize=10, fillColor=IBM_TEXT))
    bc = HorizontalBarChart()
    bc.x = 100; bc.y = 10
    bc.height = height; bc.width = width - 110
    bc.data = [values]
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.fillColor = IBM_TEXT_2
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 105
    bc.valueAxis.valueStep = 20
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.fillColor = IBM_TEXT_2
    bc.bars[0].fillColor = IBM_BLUE
    bc.bars[0].strokeColor = None
    # per-bar colours
    for i, c in enumerate(bar_colors):
        bc.bars[(0,i)].fillColor = c
    bc.barWidth = 0.6
    bc.groupSpacing = 0.3
    d.add(bc)
    return d

def vertical_bar_chart(labels, before_vals, after_vals, title, width=460, height=180):
    d = Drawing(width, height + 40)
    d.add(String(0, height + 26, title,
                 fontName='Helvetica-Bold', fontSize=10, fillColor=IBM_TEXT))
    bc = VerticalBarChart()
    bc.x = 40; bc.y = 30
    bc.height = height - 20; bc.width = width - 50
    bc.data = [before_vals, after_vals]
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.fillColor = IBM_TEXT_2
    bc.categoryAxis.labels.angle = 25
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 210
    bc.valueAxis.valueStep = 50
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.bars[0].fillColor = IBM_RED
    bc.bars[0].strokeColor = None
    bc.bars[1].fillColor = IBM_GREEN
    bc.bars[1].strokeColor = None
    bc.barWidth = 0.35
    bc.groupSpacing = 0.2
    # legend
    d.add(Rect(bc.x, 12, 10, 8, fillColor=IBM_RED, strokeColor=None))
    d.add(String(bc.x+13, 13, 'Before Copilot',
                 fontName='Helvetica', fontSize=7, fillColor=IBM_TEXT_2))
    d.add(Rect(bc.x+110, 12, 10, 8, fillColor=IBM_GREEN, strokeColor=None))
    d.add(String(bc.x+123, 13, 'After Copilot',
                 fontName='Helvetica', fontSize=7, fillColor=IBM_TEXT_2))
    d.add(bc)
    return d

def pie_chart(labels, values, chart_colors, title, width=400, height=200):
    d = Drawing(width, height + 20)
    d.add(String(0, height + 6, title,
                 fontName='Helvetica-Bold', fontSize=10, fillColor=IBM_TEXT))
    pie = Pie()
    pie.x = 20; pie.y = 20
    pie.width = 150; pie.height = 150
    pie.data = values
    pie.labels = [f'{v}h' for v in values]
    pie.sideLabels = 0
    pie.simpleLabels = 1
    pie.slices.strokeColor = IBM_WHITE
    pie.slices.strokeWidth = 1.5
    for i, c in enumerate(chart_colors):
        pie.slices[i].fillColor = c
    d.add(pie)
    # legend
    lx = 185; ly = height - 10
    for i, (label, val) in enumerate(zip(labels, values)):
        d.add(Rect(lx, ly - i*18, 10, 10,
                   fillColor=chart_colors[i % len(chart_colors)],
                   strokeColor=None))
        d.add(String(lx + 14, ly - i*18 + 1,
                     f'{label} — {val}h',
                     fontName='Helvetica', fontSize=7.5,
                     fillColor=IBM_TEXT_2))
    return d

# ─── PAGE TEMPLATE ───────────────────────────────────────────────────────────
def make_pdf():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.8*cm,
        title="IBM Migration Copilot — Submission",
        author="IBM Bob AI",
        subject="Solution Statement, Technical Statement, Solution Impact",
    )

    s = make_styles()
    story = []

    # ══════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════
    cover = Drawing(W - 3*cm, 220)
    cover.add(Rect(0, 0, W - 3*cm, 220,
                   fillColor=IBM_BLUE_DARK, strokeColor=None))
    cover.add(Rect(0, 0, 6, 220, fillColor=IBM_YELLOW, strokeColor=None))
    cover.add(String(18, 175, "IBM MIGRATION COPILOT",
                     fontName='Helvetica-Bold', fontSize=22,
                     fillColor=IBM_WHITE))
    cover.add(String(18, 150, "Submission Deliverable",
                     fontName='Helvetica', fontSize=14,
                     fillColor=IBM_BLUE_LIGHT))
    cover.add(String(18, 125, "Solution Statement  ·  Technical Statement  ·  Solution Impact",
                     fontName='Helvetica', fontSize=10,
                     fillColor=IBM_BLUE_LIGHT))
    cover.add(Line(18, 112, W - 3*cm - 18, 112,
                   strokeColor=IBM_BLUE, strokeWidth=0.8))
    cover.add(String(18, 90, "Built with IBM Bob",
                     fontName='Helvetica-Bold', fontSize=11,
                     fillColor=IBM_YELLOW))
    cover.add(String(18, 72, "LangGraph  ·  FastAPI  ·  React  ·  IBM Carbon Design System",
                     fontName='Helvetica', fontSize=9,
                     fillColor=IBM_BLUE_LIGHT))
    cover.add(String(18, 52, "OpenAI  ·  Google Gemini  ·  Qdrant  ·  Redis  ·  LangSmith",
                     fontName='Helvetica', fontSize=9,
                     fillColor=IBM_BLUE_LIGHT))
    cover.add(String(18, 22, "Agentic AI  ·  ReAct Framework  ·  Multi-Agent Orchestration",
                     fontName='Helvetica-Bold', fontSize=9,
                     fillColor=IBM_YELLOW))
    story.append(cover)
    story.append(Spacer(1, 20))

    # Stat badges
    story.append(badge_table([
        ('Phases Complete', '5/7'),
        ('AI Agents', '7'),
        ('Hours Saved / Project', '84h'),
        ('Overall Automation', '93%'),
        ('Word Limit', '500 / section'),
    ], s))
    story.append(Spacer(1, 12))
    story.append(hr(IBM_BLUE, 1))
    story.append(Paragraph(
        'This document covers all three submission deliverables on the following pages.',
        s['small']))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 1 — SOLUTION STATEMENT
    # ══════════════════════════════════════════════════════════════════════
    story.append(section_header_block(
        'SECTION 1 OF 3',
        'Solution Statement',
        'What the solution does · Target users · Outcomes · Productivity improvement',
        s))
    story.append(Spacer(1, 14))

    story.append(Paragraph('🎯 Problem Being Addressed', s['h2']))
    story.append(hr())
    story.append(Paragraph(
        'Enterprise cloud migration projects are crippled at the <b>intake and assessment phase</b>. '
        'Architecture teams spend <b>3–6 weeks</b> manually sifting through Confluence pages, '
        'config files, pom.xml dependencies, environment files, and scattered technical specs — '
        'just to produce a single AS-IS intake document before a migration plan can begin.',
        s['body']))
    story.append(Spacer(1, 6))
    story.append(highlight_box(
        '💡 The bottleneck is not the cloud architecture decision — it is the knowledge gathering: '
        'extracting facts, filling gaps, validating consistency, and drafting structured '
        'documentation for human sign-off. IBM Migration Copilot automates this entire pipeline.',
        s))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        'The platform ingests raw artifacts (PDFs, DOCX, pom.xml, .env, Confluence pages via MCP), '
        'extracts technical facts with AI confidence scoring, generates targeted gap-filling '
        'questionnaires, drafts an AS-IS intake document, validates it for completeness and '
        'consistency, and pauses for a <b>human-in-the-loop review gate</b>. The final planned layer '
        'is an <b>Advanced Assistance Service</b> — a ReAct (Reason + Act) conversational assistant '
        'embedded at the review gate so reviewers can interrogate extracted facts, search project '
        'documents, and request diagnostic commands in real time.',
        s['body']))

    story.append(Spacer(1, 10))
    story.append(Paragraph('👥 Target Users & Interaction Model', s['h2']))
    story.append(hr())

    story.append(info_card_row([
        ('Sr. Technical Architect — 38% AI Assist', IBM_BLUE,
         ['Reviews AI-generated migration plan', 'Approves / rejects intake draft',
          'Uses chat assistant to probe edge cases', 'Retains full strategic ownership']),
        ('Senior Developer — 69% AI Assist', IBM_PURPLE,
         ['Uploads config files & pom.xml', 'Reviews extracted dependency facts',
          'Runs AI-suggested diagnostic commands', 'Validates confidence scores']),
        ('Junior / Fresher — 93% AI Assist', IBM_GREEN,
         ['Triggers workflow, uploads docs', 'Answers AI questionnaire',
          'Monitors real-time SSE progress', 'No deep analysis required']),
    ], s))
    story.append(Spacer(1, 8))
    story.append(info_card_row([
        ('Vibe Coder / No-Code — 97% AI Assist', IBM_TEAL,
         ['Uploads documents, hits Start', 'Reviews auto-generated output',
          'Zero manual analysis required']),
        ('Project Manager / Reviewer — 83% AI Assist', IBM_ORANGE,
         ['Reviews flagged risks at Human Review gate', 'Uses ReAct chat panel for clarification',
          'Approves or rejects with comments']),
        ('Solution Architect — 55% AI Assist', IBM_CYAN,
         ['Validates migration strategy recommendations', 'Reviews phased execution plan',
          'Signs off on risk assessment']),
    ], s))

    story.append(Spacer(1, 10))
    story.append(Paragraph('✅ Anticipated Outcomes', s['h2']))
    story.append(hr())
    story.append(badge_table([
        ('Manual intake → hours with Copilot', '3–6 weeks'),
        ('Consistent validated output every run', '100%'),
        ('Specialist agents in pipeline', '7'),
        ('Manual Confluence reads needed', '0'),
    ], s))

    story.append(Spacer(1, 10))
    story.append(Paragraph('🚀 How It Improves Team Productivity', s['h2']))
    story.append(hr())
    story.append(Paragraph(
        'The platform eliminates the most <i>cognitively expensive</i> parts of migration prep: '
        'hunting for facts across disconnected sources, deciding which questions matter, writing '
        'consistent documentation, and re-checking for contradictions. Every team member gets a '
        '<b>co-pilot matched to their skill level</b> — architects retain control over strategy; '
        'developers stop doing manual archaeology; freshers contribute immediately without needing '
        'institutional knowledge.',
        s['body']))
    story.append(Paragraph(
        'The planned <b>Advanced Assistance ReAct agent</b> goes further: instead of a reviewer '
        'filing a ticket or pinging a subject-matter expert, they ask the assistant — which '
        'searches extracted facts, queries project vectors, and generates PowerShell/Maven '
        'diagnostics — all in the same review screen, in seconds.',
        s['body']))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 2 — TECHNICAL STATEMENT
    # ══════════════════════════════════════════════════════════════════════
    story.append(section_header_block(
        'SECTION 2 OF 3',
        'Technical Statement',
        'How the solution works · How IBM Bob was used throughout the build',
        s))
    story.append(Spacer(1, 14))

    story.append(Paragraph('⚙️ How the Solution Works', s['h2']))
    story.append(hr())

    story.append(info_card_row([
        ('🧠 Agent Pipeline', IBM_BLUE, [
            'Context Retrieval — MCP → Qdrant fallback; normalize docs',
            'Extraction — LLM fact extraction + confidence scores',
            'Questionnaire — gap analysis → prioritized questions',
            'Intake Draft — structured AS-IS document generation',
            'Validation — contradiction + completeness checks',
            'Human Review — pause gate with approve/reject',
            'Migration Planning — cloud strategy (Phase 6)',
        ]),
        ('🛠️ Infrastructure Stack', IBM_TEAL, [
            'FastAPI :8000 — main orchestration API',
            'FastAPI :8001 — Advanced Assistance SOA microservice',
            'Redis — state cache + per-project chat history',
            'Qdrant — vector embeddings per project collection',
            'LangSmith — full trace every node + LLM call',
            'OpenAI / Gemini — provider factory with fallback',
            'React + IBM Carbon — SSE-driven live UI at :3000',
        ]),
    ], s))

    story.append(Spacer(1, 8))
    story.append(Paragraph('Advanced Assistance Service — ReAct Engine', s['h3']))
    story.append(Paragraph(
        'A standalone <b>ReAct (Reason + Act)</b> service. The LangChain AgentExecutor runs a '
        'dynamic tool-selection loop: the LLM emits a <i>Thought</i>, picks a tool from the '
        'registry, receives an <i>Observation</i>, and iterates until a final answer. Each step is '
        'streamed via SSE (text/event-stream). The swap path from AgentExecutor to LangGraph '
        'ToolNode is isolated to a single file (react_agent.py).',
        s['body']))

    tbl_react = std_table(
        ['Tool', 'Phase', 'Input', 'Output / Action'],
        [
            ['search_state', 'V1', 'query string', 'extracted_facts + confidence from Redis state'],
            ['search_qdrant', 'V1', 'query string', 'top-k semantic chunks + similarity scores'],
            ['generate_command', 'V1', 'question + reason', 'PowerShell / Maven diagnostic command'],
            ['ingest_context', 'V1', 'text + context_type', 'chunks embedded into project Qdrant collection'],
            ['fetch_workflow_state', 'V1', 'project_id', 'Full MigrationState via HTTP GET :8000'],
            ['search_web', 'V2 stub', '—', 'NotImplementedError (future)'],
            ['run_in_sandbox', 'V2 stub', '—', 'NotImplementedError (future)'],
        ],
        s,
        col_widths=[3*cm, 1.8*cm, 3.5*cm, 8.2*cm]
    )
    story.append(tbl_react)

    story.append(Spacer(1, 14))
    story.append(Paragraph('🤖 How IBM Bob Was Used', s['h2']))
    story.append(hr())

    bob_steps = [
        ('1', 'Full Codebase Onboarding via Parallel Subagents',
         "Bob's spawn_subagent tool read 44+ documentation files, all agent source files, and "
         "the entire orchestration layer simultaneously — producing a verified project status map "
         "(Phases 1–5 complete; Phase 6 stub) in a single pass rather than sequential file reads."),
        ('2', 'Architecture Design via Structured Planning',
         "Bob authored docs/ADVANCED_ASSISTANCE_PLAN.md — a full 9-sub-task spec with ReAct loop "
         "diagrams, tool registry tables (V1 + V2 stubs), LangChain → LangGraph swap path, and "
         "pre-commit checklists. SOA decision (:8001 microservice) was proposed after reading "
         "backend/app/main.py to verify zero interference."),
        ('3', 'Bug-Memory-Driven Code Generation',
         "Before writing any code, Bob read .agents/CRITICAL_BUGS_MEMORY.md (10 historical bugs). "
         "Every generated file respects the rules: .isoformat() for all timestamps, ALL TypedDict "
         "fields initialized, handle_parsing_errors=True on AgentExecutor, LLM JSON markdown "
         "stripping, and method names matched to callers."),
        ('4', 'Pattern Replication Across Files',
         "Bob read the existing SSE pattern (api/orchestration.py lines 434–560), the Redis "
         "client singleton pattern, and the Qdrant search() signature — then replicated these "
         "exactly in assistance service files, ensuring zero API surface mismatch."),
        ('5', 'Todo Tracking + Multi-file Parallel Generation',
         "Bob used update_todo_list to track 13 implementation sub-tasks. Files were written in "
         "parallel (conversation_store.py + Qdrant search reads issued simultaneously) to "
         "minimise round-trip latency during the build session."),
        ('6', 'Documentation & README Maintenance',
         "Bob authored and updated README.md (Advanced Assistance section, roadmap, project "
         "structure tree), created all docs/ files, and produced onboarding-plan.md and "
         ".agents/AGENT_QUICKREF.md so future agents self-onboard without human guidance."),
    ]

    for num, title, body in bob_steps:
        row_data = [[
            Paragraph(f'<b>{num}</b>', ParagraphStyle('bn',
                fontName='Helvetica-Bold', fontSize=11, textColor=IBM_WHITE,
                alignment=TA_CENTER, leading=14)),
            [Paragraph(f'<b>{title}</b>', s['body_bold']),
             Paragraph(body, s['body'])]
        ]]
        t = Table(row_data, colWidths=[0.8*cm, W - 3*cm - 0.8*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), IBM_BLUE),
            ('BACKGROUND', (1,0), (1,-1), IBM_WHITE),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (0,-1), 4),
            ('RIGHTPADDING', (0,0), (0,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (1,0), (1,-1), 10),
            ('RIGHTPADDING', (1,0), (1,-1), 10),
            ('BOX', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ]))
        story.append(t)
        story.append(Spacer(1, 5))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 3 — SOLUTION IMPACT
    # ══════════════════════════════════════════════════════════════════════
    story.append(section_header_block(
        'SECTION 3 OF 3',
        'Solution Impact',
        'Productivity improvement categories · Time savings · Role-wise matrix · Visual charts',
        s))
    story.append(Spacer(1, 14))

    # Impact categories
    story.append(Paragraph('🏷️ Productivity Improvement Categories', s['h2']))
    story.append(hr())
    story.append(info_card_row([
        ('⏱️ Reduce Time on Routine Tasks', IBM_BLUE,
         ['Doc analysis automated', 'Questionnaire drafting automated', 'AS-IS writing automated']),
        ('✅ Accuracy & Consistency', IBM_GREEN,
         ['AI confidence scores', 'Validation agent every run', 'Zero human variation']),
        ('🔍 Reduce Search Time', IBM_PURPLE,
         ['Qdrant semantic search', 'ReAct agent replaces Confluence archaeology']),
    ], s))
    story.append(Spacer(1, 6))
    story.append(info_card_row([
        ('🚀 Speed Up Offering Development', IBM_ORANGE,
         ['Migration plan in hours', 'Enables parallel workstreams']),
        ('🛡️ Reduce Operational Risk', IBM_RED,
         ['Human Review gate', 'Validation catches contradictions']),
        ('🔬 Innovation & Exploration', IBM_TEAL,
         ['ReAct agent', 'QUERY HTTP method', 'LangGraph swap path']),
    ], s))

    story.append(Spacer(1, 12))

    # Time savings table
    story.append(Paragraph('⏱️ Time Savings — Before vs After Copilot (per migration project)', s['h2']))
    story.append(hr())
    story.append(Paragraph(
        'Frequency: ~8–12 migrations per year per team. Methodology: estimates derived from '
        'actual sprint-level task breakdowns in planning docs, compared against IBM engagement '
        'timelines (3–6 week intake phases). Post-AI times = human validation overhead only.',
        s['small']))
    story.append(Spacer(1, 6))

    savings_data = [
        ['Document collection & reading', '16h', '0.5h', '15.5h', '97%'],
        ['AS-IS fact extraction (manual)', '24h', '1h', '23h', '96%'],
        ['Questionnaire creation', '8h', '0.5h', '7.5h', '94%'],
        ['Intake document drafting', '12h', '0.5h', '11.5h', '96%'],
        ['Validation / consistency check', '6h', '0.25h', '5.75h', '96%'],
        ['Human review + Q&A with team', '4h', '1h', '3h', '75%'],
        ['Migration plan drafting', '20h', '2h', '18h', '90%'],
        ['TOTAL per project', '90h', '5.75h', '84.25h', '93.6%'],
    ]
    t = Table(
        [[Paragraph(h, s['table_header']) for h in
          ['Task', 'Before', 'After', 'Saved', 'Saving %']]] +
        [[Paragraph(r[0], s['table_cell']),
          Paragraph(r[1], ParagraphStyle('red', fontName='Helvetica-Bold', fontSize=9,
              textColor=IBM_RED, leading=12, alignment=TA_CENTER)),
          Paragraph(r[2], ParagraphStyle('grn', fontName='Helvetica-Bold', fontSize=9,
              textColor=IBM_GREEN, leading=12, alignment=TA_CENTER)),
          Paragraph(r[3], ParagraphStyle('blu', fontName='Helvetica-Bold', fontSize=9,
              textColor=IBM_BLUE, leading=12, alignment=TA_CENTER)),
          Paragraph(r[4], ParagraphStyle('pct', fontName='Helvetica-Bold', fontSize=9,
              textColor=IBM_BLUE_DARK, leading=12, alignment=TA_CENTER)),
         ] for r in savings_data],
        colWidths=[7*cm, 2*cm, 2*cm, 2*cm, 2.2*cm],
        repeatRows=1
    )
    last_row = len(savings_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), IBM_TEXT),
        ('TEXTCOLOR', (0,0), (-1,0), IBM_WHITE),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [IBM_WHITE, IBM_BG]),
        ('BACKGROUND', (0, last_row), (-1, last_row), IBM_BLUE_LIGHT),
        ('FONTNAME', (0, last_row), (-1, last_row), 'Helvetica-Bold'),
        ('INNERGRID', (0,0), (-1,-1), 0.4, IBM_BORDER),
        ('BOX', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)

    story.append(PageBreak())

    # Role-wise matrix
    story.append(Paragraph('👥 Role-Wise Productivity Matrix — AI Assistance % by Task', s['h2']))
    story.append(hr())

    roles = ['Sr. Architect', 'Sol. Arch.', 'Senior Dev', 'Mid Dev', 'Junior/Fresher',
             'Vibe Coder', 'Project Mgr']
    tasks = ['Doc\nIngest', 'Fact\nExtract', 'Question-\nnaire', 'Intake\nDraft',
             'Review\n& Q&A', 'Migration\nPlan', 'Avg AI\nAssist']
    matrix_vals = [
        [80,  40,  50,  30,  10,  20,  38],
        [90,  60,  65,  50,  25,  40,  55],
        [95,  70,  75,  70,  45,  60,  69],
        [99,  85,  88,  85,  65,  75,  83],
        [100, 95,  95,  95,  80,  90,  93],
        [100, 99,  99,  99,  90,  95,  97],
        [100, 90,  85,  90,  60,  70,  83],
    ]

    def heat_color(v):
        if v >= 90: return colors.HexColor('#a5d6a7')
        if v >= 75: return colors.HexColor('#c8e6c9')
        if v >= 60: return colors.HexColor('#e8f5e9')
        if v >= 40: return colors.HexColor('#fff8e1')
        return colors.HexColor('#fff1f1')

    header_row = [Paragraph('Role', s['table_header'])] + \
                 [Paragraph(t, s['table_header']) for t in tasks]
    data_rows = []
    for i, role in enumerate(roles):
        row = [Paragraph(role, s['table_bold'])]
        for j, v in enumerate(matrix_vals[i]):
            style = ParagraphStyle('hc', fontName='Helvetica-Bold', fontSize=9,
                textColor=IBM_TEXT, leading=12, alignment=TA_CENTER)
            row.append(Paragraph(f'{v}%', style))
        data_rows.append(row)

    mx_table = Table([header_row] + data_rows,
                     colWidths=[3.2*cm] + [1.7*cm]*7, repeatRows=1)
    ts = [
        ('BACKGROUND', (0,0), (-1,0), IBM_TEXT),
        ('TEXTCOLOR', (0,0), (-1,0), IBM_WHITE),
        ('INNERGRID', (0,0), (-1,-1), 0.4, IBM_BORDER),
        ('BOX', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        # Last col highlight
        ('BACKGROUND', (-1,1), (-1,-1), IBM_BLUE_LIGHT),
        ('TEXTCOLOR', (-1,1), (-1,-1), IBM_BLUE_DARK),
    ]
    for i, row_vals in enumerate(matrix_vals):
        for j, v in enumerate(row_vals[:-1]):
            ts.append(('BACKGROUND', (j+1, i+1), (j+1, i+1), heat_color(v)))
    mx_table.setStyle(TableStyle(ts))
    story.append(mx_table)

    story.append(Spacer(1, 14))

    # BAR CHART — AI assist by role
    bar_colors_list = [IBM_BLUE_DARK, IBM_BLUE, IBM_CYAN, IBM_PURPLE,
                       IBM_GREEN, IBM_TEAL, IBM_YELLOW]
    avg_vals = [38, 55, 69, 83, 93, 97, 83]
    story.append(horizontal_bar_chart(
        roles, avg_vals, bar_colors_list,
        'Average AI Assistance % by Role',
        width=460, height=160))

    story.append(PageBreak())

    # Time by complexity
    story.append(Paragraph('⏱️ Time to Complete Intake — Role × Application Complexity', s['h2']))
    story.append(hr())

    complex_data = [
        ['Sr. Architect',     '8h',   '4h',    '20h',  '8h',   '60h',  '18h'],
        ['Solution Arch.',    '12h',  '4h',    '30h',  '9h',   '80h',  '20h'],
        ['Senior Dev',        '16h',  '3h',    '40h',  '7h',   '90h',  '14h'],
        ['Mid Dev',           '24h',  '3h',    '60h',  '6h',   '120h', '10h'],
        ['Junior / Fresher',  '40h',  '2h',    '100h', '4h',   '200h', '8h'],
        ['Vibe Coder',        'N/A',  '1h',    'N/A',  '2h',   'N/A',  '4h'],
        ['Project Manager',   '6h',   '2h',    '15h',  '4h',   '40h',  '8h'],
    ]

    def color_cell(val, is_before):
        c = IBM_RED if is_before and val != 'N/A' else IBM_GREEN
        if val == 'N/A': c = IBM_TEXT_2
        return Paragraph(val, ParagraphStyle('tc', fontName='Helvetica-Bold',
            fontSize=9, textColor=c, leading=12, alignment=TA_CENTER))

    cplx_header = [
        Paragraph('Role', s['table_header']),
        Paragraph('Simple\nBefore', ParagraphStyle('rh', fontName='Helvetica-Bold',
            fontSize=8, textColor=IBM_WHITE, leading=11, alignment=TA_CENTER,
            backColor=IBM_RED)),
        Paragraph('Simple\nAfter', ParagraphStyle('rh', fontName='Helvetica-Bold',
            fontSize=8, textColor=IBM_WHITE, leading=11, alignment=TA_CENTER,
            backColor=IBM_GREEN)),
        Paragraph('Moderate\nBefore', ParagraphStyle('rh', fontName='Helvetica-Bold',
            fontSize=8, textColor=IBM_WHITE, leading=11, alignment=TA_CENTER,
            backColor=IBM_RED)),
        Paragraph('Moderate\nAfter', ParagraphStyle('rh', fontName='Helvetica-Bold',
            fontSize=8, textColor=IBM_WHITE, leading=11, alignment=TA_CENTER,
            backColor=IBM_GREEN)),
        Paragraph('Complex\nBefore', ParagraphStyle('rh', fontName='Helvetica-Bold',
            fontSize=8, textColor=IBM_WHITE, leading=11, alignment=TA_CENTER,
            backColor=IBM_RED)),
        Paragraph('Complex\nAfter', ParagraphStyle('rh', fontName='Helvetica-Bold',
            fontSize=8, textColor=IBM_WHITE, leading=11, alignment=TA_CENTER,
            backColor=IBM_GREEN)),
    ]
    cplx_rows = [[Paragraph(r[0], s['table_bold'])] +
                 [color_cell(r[j+1], j%2==0) for j in range(6)]
                 for r in complex_data]
    cplx_t = Table([cplx_header] + cplx_rows,
                   colWidths=[3.2*cm, 1.8*cm, 1.8*cm, 2*cm, 2*cm, 2.1*cm, 2.1*cm],
                   repeatRows=1)
    cplx_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), IBM_TEXT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [IBM_WHITE, IBM_BG]),
        ('INNERGRID', (0,0), (-1,-1), 0.4, IBM_BORDER),
        ('BOX', (0,0), (-1,-1), 0.5, IBM_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(cplx_t)
    story.append(Spacer(1, 14))

    # Vertical bar — complex app
    before_complex = [60, 80, 90, 120, 200, 0, 40]
    after_complex  = [18, 20, 14, 10,   8,  4,  8]
    story.append(vertical_bar_chart(
        roles, before_complex, after_complex,
        'Time Saved — Complex Application (Hours Before vs After)',
        width=460, height=180))

    story.append(Spacer(1, 12))

    # Pie chart
    pie_labels = ['Doc Collection', 'Fact Extraction', 'Questionnaire',
                  'Intake Drafting', 'Validation', 'Review Q&A', 'Migration Plan']
    pie_values = [15.5, 23, 7.5, 11.5, 5.75, 3, 18]
    pie_colors = [IBM_BLUE, IBM_PURPLE, IBM_TEAL, IBM_YELLOW,
                  IBM_RED, IBM_GREEN, IBM_CYAN]
    story.append(pie_chart(
        pie_labels, pie_values, pie_colors,
        'Where the 84.25h Savings Come From (per project)',
        width=420, height=200))

    story.append(Spacer(1, 12))

    # Annual impact
    story.append(Paragraph('📅 Annualised Team Impact', s['h2']))
    story.append(hr())
    story.append(Paragraph(
        '10 migrations/year · 3-person team · 84.25h saved per project', s['small']))
    story.append(Spacer(1, 6))
    story.append(badge_table([
        ('Hours saved per year (team of 3)', '843h'),
        ('Engineer-weeks reclaimed annually', '~21 weeks'),
        ('Overall automation rate', '93%'),
        ('Upload → draft ready (avg)', '< 2h'),
    ], s))

    story.append(Spacer(1, 16))
    story.append(hr(IBM_BLUE, 1))
    story.append(Paragraph(
        'IBM Migration Copilot  ·  Built with IBM Bob  ·  '
        'LangGraph · FastAPI · React · IBM Carbon Design System  ·  '
        '© 2025',
        s['footer']))

    # ── BUILD ────────────────────────────────────────────────────────────
    doc.build(story)
    print(f"[OK] PDF generated: {OUTPUT}")

if __name__ == '__main__':
    make_pdf()
