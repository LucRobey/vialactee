import os
import sys
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Canonical strings with explicit Unicode escapes for absolute encoding safety
NAME_VIALACTEE = "Vialact\u00e9e"
NAME_VIALACTEE_UPPER = "VIALACT\u00c9E"

class VialacteePDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self.set_margins(18, 14, 18)
        
        # Load system fonts
        self.add_font("Arial", "", "C:/Windows/Fonts/arial.ttf")
        self.add_font("Arial", "B", "C:/Windows/Fonts/arialbd.ttf")
        self.add_font("Arial", "I", "C:/Windows/Fonts/ariali.ttf")
        
        # Refined Color Palette
        self.c_primary = (15, 23, 42)          # Slate 900
        self.c_secondary = (30, 41, 59)        # Slate 800
        self.c_accent = (67, 56, 202)          # Indigo 700
        self.c_accent_light = (238, 242, 255)  # Indigo 50
        self.c_accent_border = (199, 210, 254) # Indigo 200
        
        # Domain Colors
        # Audio / Analysis Domain: Violet / Indigo
        self.c_audio_badge_bg = (243, 232, 255)   # Purple 100
        self.c_audio_badge_txt = (109, 40, 217)   # Purple 700
        self.c_audio_border = (216, 180, 254)     # Purple 300
        self.c_audio_card_bg = (250, 245, 255)    # Purple 50 / Slate blend
        
        # Visual / Rendering Domain: Cyan / Sky Blue
        self.c_vis_badge_bg = (224, 242, 254)     # Sky 100
        self.c_vis_badge_txt = (3, 105, 161)      # Sky 700
        self.c_vis_border = (186, 230, 253)       # Sky 300
        self.c_vis_card_bg = (240, 249, 255)      # Sky 50 / Slate blend

        self.c_text = (51, 65, 85)             # Slate 700
        self.c_muted = (100, 116, 139)         # Slate 500
        self.c_card_bg = (248, 250, 252)       # Slate 50
        self.c_card_border = (226, 232, 240)   # Slate 200
        self.c_white = (255, 255, 255)
        self.c_live_green = (16, 185, 129)     # Emerald 500
        self.c_live_bg = (236, 253, 245)       # Emerald 50

    def draw_header(self, page_num, title, subtitle, badge_text):
        # Header accent top strip
        self.set_fill_color(*self.c_primary)
        self.rect(0, 0, 210, 4.5, 'F')
        
        # Category Tag / Badge
        self.set_xy(18, 11.5)
        self.set_font("Arial", "B", 7.8)
        self.set_text_color(*self.c_accent)
        self.cell(0, 4.5, badge_text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Main Title
        self.set_font("Arial", "B", 20.5)
        self.set_text_color(*self.c_primary)
        self.set_xy(18, 16)
        self.cell(0, 8.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Subtitle
        self.set_font("Arial", "I", 9.6)
        self.set_text_color(*self.c_muted)
        self.set_xy(18, 25)
        self.cell(0, 5, subtitle, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Live Indicator badge on the right
        self.set_xy(145, 14.5)
        self.set_fill_color(*self.c_live_bg)
        self.set_draw_color(*self.c_live_green)
        self.set_line_width(0.35)
        self.rect(145, 14.5, 47, 8, 'DF')
        
        # Green pulsing status dot
        self.set_fill_color(*self.c_live_green)
        self.circle(150.5, 18.5, 1.8, 'F')
        
        self.set_xy(153.5, 15)
        self.set_font("Arial", "B", 7.8)
        self.set_text_color(6, 95, 70)
        self.cell(38, 7, "100% REAL-TIME LIVE", new_x=XPos.RIGHT, new_y=YPos.TOP)

        # Subtle divider rule
        self.set_draw_color(*self.c_card_border)
        self.set_line_width(0.35)
        self.line(18, 32, 192, 32)

    def draw_footer(self, page_num, total_pages=2):
        self.set_draw_color(*self.c_card_border)
        self.set_line_width(0.3)
        self.line(18, 283, 192, 283)
        
        self.set_xy(18, 285)
        self.set_font("Arial", "", 8)
        self.set_text_color(*self.c_muted)
        self.cell(100, 4.5, f"{NAME_VIALACTEE} Product Brief \u2014 Real-Time Architecture", new_x=XPos.RIGHT, new_y=YPos.TOP)
        
        self.set_xy(150, 285)
        self.cell(42, 4.5, f"Page {page_num} of {total_pages}", align="R", new_x=XPos.RIGHT, new_y=YPos.TOP)

    def draw_card(self, x, y, w, h, bg_color=None, border_color=None):
        bg = bg_color or self.c_card_bg
        border = border_color or self.c_card_border
        self.set_fill_color(*bg)
        self.set_draw_color(*border)
        self.set_line_width(0.3)
        self.rect(x, y, w, h, 'DF')

def build_pdf(filename="Vialactee_Project_Overview.pdf"):
    pdf = VialacteePDF()
    
    # =========================================================================
    # PAGE 1: NON-TECHNICAL / GENERAL OVERVIEW
    # =========================================================================
    pdf.add_page()
    pdf.draw_header(
        page_num=1,
        title=NAME_VIALACTEE_UPPER,
        subtitle="The Autonomous, Music-Reactive LED Chandelier",
        badge_text="Executive Product Overview"
    )
    
    # 1. Executive Summary Box
    y_pos = 36
    pdf.draw_card(18, y_pos, 174, 27, bg_color=pdf.c_accent_light, border_color=pdf.c_accent_border)
    pdf.set_xy(23, y_pos + 3.2)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(*pdf.c_accent)
    pdf.cell(0, 4.5, f"WHAT IS {NAME_VIALACTEE_UPPER}?", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_xy(23, y_pos + 8.2)
    pdf.set_font("Arial", "", 8.9)
    pdf.set_text_color(*pdf.c_text)
    intro_text = (
        f"{NAME_VIALACTEE} is a bespoke architectural chandelier composed of over 1,300 individually "
        "controlled LEDs. It continuously listens to surrounding sound and translates musical energy, rhythm, and emotion "
        "into breathing, three-dimensional light in real time. It is neither a static decorative lamp nor a simplistic "
        "sound-level flasher: it functions as an autonomous digital performer, playing live in perfect synergy with any music."
    )
    pdf.multi_cell(164, 4.3, intro_text)
    
    # 2. Key Pillars of the Live Experience
    y_pos = 67
    pdf.set_xy(18, y_pos)
    pdf.set_font("Arial", "B", 11.5)
    pdf.set_text_color(*pdf.c_primary)
    pdf.cell(0, 5.5, "The Live Experience: Performing in Real Time", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    features = [
        (
            "True Spontaneity \u2014 100% Live & Unscripted",
            f"{NAME_VIALACTEE} requires zero pre-recorded stems, no MIDI files, and no pre-rendered timelines. "
            "Whether an artist plays an unreleased track, a live band improvises on stage, or guests stream a random playlist, "
            "the system ingests the live acoustic stream and synthesizes synchronized light on the fly. "
            "It reacts to the moment, completely free of manual cueing or offline preparation."
        ),
        (
            "Zero Perceived Latency \u2014 The Chandelier Anticipates",
            "Human senses immediately spot lighting delay: reacting after a beat is heard feels sluggish and clumsy. "
            "Standard sound fixtures lag because digital processing takes time. "
            f"{NAME_VIALACTEE} eliminates this latency by tracking musical tempo phase and predicting upcoming beats, "
            "triggering light pulses milliseconds in advance so visual impact and speaker sound strike the audience simultaneously."
        ),
        (
            "Deep Musical Intelligence vs. Volume Blinking",
            "Instead of flashing indiscriminately whenever noise spikes, the chandelier understands musical depth. "
            "It isolates thumping sub-bass kicks, melodic mid-range chords, vocal expressions, and delicate cymbal shimmers, "
            "choreographing each frequency across distinct spatial zones of the chandelier for a nuanced, breathing performance."
        ),
        (
            "Organic Narrative & Seamless Transitions",
            "The chandelier continuously mirrors the emotional evolution of the music. A calm, intimate passage evokes gentle, "
            "breathing embers; an escalating buildup radiates energetic waves across all segments; a climatic drop unleashes "
            "explosive light cascades. Transitions between visual aesthetics morph smoothly without jarring cuts or stuttering."
        )
    ]
    
    card_y = y_pos + 7.5
    card_h = 32
    for title, desc in features:
        pdf.draw_card(18, card_y, 174, card_h)
        
        # Accent left stripe
        pdf.set_fill_color(*pdf.c_accent)
        pdf.rect(18, card_y, 2, card_h, 'F')
        
        pdf.set_xy(23, card_y + 3)
        pdf.set_font("Arial", "B", 9.5)
        pdf.set_text_color(*pdf.c_secondary)
        pdf.cell(0, 4.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_xy(23, card_y + 8.2)
        pdf.set_font("Arial", "", 8.5)
        pdf.set_text_color(*pdf.c_text)
        pdf.multi_cell(164, 4.3, desc)
        
        card_y += card_h + 3.5

    # 3. Everyday Interaction & Control
    y_pos = card_y + 1.5
    pdf.set_xy(18, y_pos)
    pdf.set_font("Arial", "B", 11.5)
    pdf.set_text_color(*pdf.c_primary)
    pdf.cell(0, 5.5, "Everyday Interaction: Seamless Remote Control", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    col_w = 84
    col_gap = 6
    card_ctrl_y = y_pos + 7
    card_ctrl_h = 35
    
    # Left column: Web Controller
    pdf.draw_card(18, card_ctrl_y, col_w, card_ctrl_h)
    pdf.set_xy(22, card_ctrl_y + 3)
    pdf.set_font("Arial", "B", 9.2)
    pdf.set_text_color(*pdf.c_accent)
    pdf.cell(0, 4.5, "Instant Web Remote (Any Device)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(22, card_ctrl_y + 8.2)
    pdf.set_font("Arial", "", 8.3)
    pdf.set_text_color(*pdf.c_text)
    pdf.multi_cell(col_w - 8, 4.2, (
        "Operates via a responsive web app reachable from any smartphone, tablet, or laptop on the local network. "
        "No installation or app store downloads required\u2014open the browser to adjust visual modes, colors, "
        "and brightness live during any performance."
    ))
    
    # Right column: Presets
    rx = 18 + col_w + col_gap
    pdf.draw_card(rx, card_ctrl_y, col_w, card_ctrl_h)
    pdf.set_xy(rx + 4, card_ctrl_y + 3)
    pdf.set_font("Arial", "B", 9.2)
    pdf.set_text_color(*pdf.c_accent)
    pdf.cell(0, 4.5, "Atmosphere Curation & Presets", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(rx + 4, card_ctrl_y + 8.2)
    pdf.set_font("Arial", "", 8.3)
    pdf.set_text_color(*pdf.c_text)
    pdf.multi_cell(col_w - 8, 4.2, (
        "Explore dozens of visual modes, sculpt color palettes, and isolate individual spatial segments. "
        "Store favorite light ambiances into one-touch presets for intimate dinners, vibrant cocktail lounges, "
        "or high-energy live concerts."
    ))

    pdf.draw_footer(page_num=1, total_pages=2)

    # =========================================================================
    # PAGE 2: TECHNICAL ARCHITECTURE \u2014 CLEARLY DIVIDED:
    #         PART I: MUSIC ANALYSIS vs PART II: VISUALIZATION & LIGHT
    # =========================================================================
    pdf.add_page()
    pdf.draw_header(
        page_num=2,
        title="TECHNICAL ARCHITECTURE",
        subtitle="Dual Real-Time Engines: Live Music Analysis & Vectorized Visualization",
        badge_text="System Architecture & Core Engineering"
    )

    # Top Real-Time Pipeline Bridge (Audio -> Analysis -> Sync -> Visualization -> LED)
    pipe_y = 35
    pdf.set_xy(18, pipe_y)
    pdf.set_font("Arial", "B", 10.5)
    pdf.set_text_color(*pdf.c_primary)
    pdf.cell(0, 4.5, "The End-to-End Real-Time Pipeline", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pipe_box_y = pipe_y + 5.5
    pipe_h = 16
    pdf.draw_card(18, pipe_box_y, 174, pipe_h, bg_color=(248, 250, 252), border_color=(203, 213, 225))

    pipe_steps = [
        ("Live Audio In", "Mic / Line-In\n~10ms Frames", (241, 245, 249), pdf.c_primary),
        ("Music Analysis", "Multi-band DSP\nEnergy & Drops", pdf.c_audio_badge_bg, pdf.c_audio_badge_txt),
        ("Anticipation Sync", "Oracle Flywheel\nPhase Alignment", pdf.c_accent_light, pdf.c_accent),
        ("Visualization", "Vectorized Math\n60 FPS Engine", pdf.c_vis_badge_bg, pdf.c_vis_badge_txt),
        ("LED Output", "1,304 Channels\nGPIO / UDP", (241, 245, 249), pdf.c_primary)
    ]

    p_w = 30.5
    p_gap = 5.2
    for i, (p_title, p_sub, p_bg, p_txt) in enumerate(pipe_steps):
        px = 20.5 + i * (p_w + p_gap)
        pdf.draw_card(px, pipe_box_y + 2, p_w, pipe_h - 4, bg_color=p_bg, border_color=(226, 232, 240))
        
        pdf.set_xy(px + 1, pipe_box_y + 3.2)
        pdf.set_font("Arial", "B", 7.2)
        pdf.set_text_color(*p_txt)
        pdf.cell(p_w - 2, 3.5, p_title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_xy(px + 1, pipe_box_y + 6.8)
        pdf.set_font("Arial", "", 6.6)
        pdf.set_text_color(*pdf.c_text)
        pdf.multi_cell(p_w - 2, 3.0, p_sub, align="C")

        # Arrow indicator
        if i < len(pipe_steps) - 1:
            arr_x = px + p_w + 0.6
            pdf.set_xy(arr_x, pipe_box_y + 4.5)
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(*pdf.c_muted)
            pdf.cell(p_gap - 1.2, 5, ">", align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)

    # TWO MAJOR DOMAIN COLUMNS:
    # LEFT COLUMN: MUSIC ANALYSIS ENGINE (THE "EARS & BRAIN")
    # RIGHT COLUMN: VISUALIZATION & LIGHT ENGINE (THE "BODY & EXPRESSION")
    
    col_y = pipe_box_y + pipe_h + 5
    col_w = 84
    col_gap = 6
    col_h = 162
    
    # -------------------------------------------------------------
    # LEFT COLUMN: PART I - MUSIC ANALYSIS ENGINE
    # -------------------------------------------------------------
    lx = 18
    # Outer container border for Music Analysis
    pdf.draw_card(lx, col_y, col_w, col_h, bg_color=(253, 251, 255), border_color=pdf.c_audio_border)
    
    # Left Header Banner
    pdf.set_fill_color(*pdf.c_audio_badge_bg)
    pdf.rect(lx, col_y, col_w, 14, 'F')
    pdf.set_draw_color(*pdf.c_audio_border)
    pdf.line(lx, col_y + 14, lx + col_w, col_y + 14)
    
    pdf.set_xy(lx + 4, col_y + 2.5)
    pdf.set_font("Arial", "B", 9.2)
    pdf.set_text_color(*pdf.c_audio_badge_txt)
    pdf.cell(col_w - 8, 4.2, "PART I \u2014 MUSIC ANALYSIS ENGINE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_xy(lx + 4, col_y + 7.2)
    pdf.set_font("Arial", "I", 7.4)
    pdf.set_text_color(126, 34, 206)
    pdf.cell(col_w - 8, 3.8, "The 'Ears & Brain': Ingestion, DSP & Prediction", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # 4 Cards for Music Analysis
    audio_cards = [
        (
            "1. Zero-Latency Ingestion",
            "AudioIngestion · Local_Microphone",
            "Slices live audio into micro-windows (~10ms) from line-in or microphone feeds. Employs lock-free circular ring buffers that run independently from graphics, guaranteeing zero buffer overflows and zero latency buildup over time."
        ),
        (
            "2. Multi-Band Spectral Decomposition",
            "AudioAnalyzer · MultiBandOnset",
            "Splits the live signal into 4 distinct frequency registers: sub-bass, low-mid, presence, and brilliance. Computes continuous spectral flux and onset novelty to track kick transients, snare hits, and melodic contours independently."
        ),
        (
            "3. The 'Oracle' Beat Anticipation",
            "comb_kernels · Phase Projection",
            "The mathematical core of live synchronization. Rather than reacting late after a sound is emitted, the Oracle locks into the rhythmic period and projects future beat phase ahead in time, completely canceling speaker and physical travel latency."
        ),
        (
            "4. Musical Context & Dynamics",
            "MusicalContextEngine · StructuralNovelty",
            "Extracts macro musical narrative without lookahead. Dynamically tracks cumulative energy, dynamic range, and builds/drops, signaling when the music enters an intimate breakdown or an explosive chorus drop."
        )
    ]

    card_in_y = col_y + 16.5
    c_in_h = 34.5
    for title, sub, desc in audio_cards:
        pdf.draw_card(lx + 3, card_in_y, col_w - 6, c_in_h, bg_color=pdf.c_white, border_color=(233, 213, 255))
        
        pdf.set_xy(lx + 6, card_in_y + 2.2)
        pdf.set_font("Arial", "B", 8.4)
        pdf.set_text_color(*pdf.c_primary)
        pdf.cell(col_w - 12, 3.8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_xy(lx + 6, card_in_y + 6.2)
        pdf.set_font("Arial", "I", 7.0)
        pdf.set_text_color(*pdf.c_audio_badge_txt)
        pdf.cell(col_w - 12, 3.4, sub, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_xy(lx + 6, card_in_y + 10.2)
        pdf.set_font("Arial", "", 7.2)
        pdf.set_text_color(*pdf.c_text)
        pdf.multi_cell(col_w - 12, 3.4, desc)
        
        card_in_y += c_in_h + 2.3

    # -------------------------------------------------------------
    # RIGHT COLUMN: PART II - VISUALIZATION & LIGHT ENGINE
    # -------------------------------------------------------------
    rx = 18 + col_w + col_gap
    # Outer container border for Visualization Engine
    pdf.draw_card(rx, col_y, col_w, col_h, bg_color=(250, 253, 255), border_color=pdf.c_vis_border)
    
    # Right Header Banner
    pdf.set_fill_color(*pdf.c_vis_badge_bg)
    pdf.rect(rx, col_y, col_w, 14, 'F')
    pdf.set_draw_color(*pdf.c_vis_border)
    pdf.line(rx, col_y + 14, rx + col_w, col_y + 14)
    
    pdf.set_xy(rx + 4, col_y + 2.5)
    pdf.set_font("Arial", "B", 9.2)
    pdf.set_text_color(*pdf.c_vis_badge_txt)
    pdf.cell(col_w - 8, 4.2, "PART II \u2014 VISUALIZATION ENGINE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_xy(rx + 4, col_y + 7.2)
    pdf.set_font("Arial", "I", 7.4)
    pdf.set_text_color(2, 132, 199)
    pdf.cell(col_w - 8, 3.8, "The 'Body & Expression': Vectorized Modes & LEDs", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # 4 Cards for Visualization Engine
    vis_cards = [
        (
            "1. Vectorized NumPy Rendering",
            "modes.Mode · Matrix Math Pipeline",
            "Eliminates slow, per-pixel Python loops. All light math (dimensional waves, ripples, color shifts) is computed across all 1,304 LED channels simultaneously using NumPy matrix arrays, locking silky 60 FPS output on embedded hardware."
        ),
        (
            "2. 3D Spatial Geometry Mapping",
            "Segment.py · segments_full.json",
            "Translates abstract audio into true 3D spatial motion. Geometry profiles map physical coordinates, segment lengths, and vertical wiring directions (bottom-to-top), allowing light pulses to rise, expand, and orbit realistically in space."
        ),
        (
            "3. Transition Director & Morphing",
            "Transition_Director · Transition_Engine",
            "Choreographs fluid transitions between visual aesthetics. Rather than jarring cuts, it continuously interpolates color palettes, speeds, and geometric states, creating an uninterrupted, evolving visual narrative."
        ),
        (
            "4. Decoupled Hardware & Remote Control",
            "HardwareFactory · Connector · wabb-interface",
            "Decoupled drivers support dual-channel GPIO (Raspberry Pi), networked ESP32 (UDP), or a PC simulator. An asynchronous WebSocket server routes real-time commands from the React web controller without stalling animation."
        )
    ]

    card_in_y = col_y + 16.5
    for title, sub, desc in vis_cards:
        pdf.draw_card(rx + 3, card_in_y, col_w - 6, c_in_h, bg_color=pdf.c_white, border_color=(186, 230, 253))
        
        pdf.set_xy(rx + 6, card_in_y + 2.2)
        pdf.set_font("Arial", "B", 8.4)
        pdf.set_text_color(*pdf.c_primary)
        pdf.cell(col_w - 12, 3.8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_xy(rx + 6, card_in_y + 6.2)
        pdf.set_font("Arial", "I", 7.0)
        pdf.set_text_color(*pdf.c_vis_badge_txt)
        pdf.cell(col_w - 12, 3.4, sub, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_xy(rx + 6, card_in_y + 10.2)
        pdf.set_font("Arial", "", 7.2)
        pdf.set_text_color(*pdf.c_text)
        pdf.multi_cell(col_w - 12, 3.4, desc)
        
        card_in_y += c_in_h + 2.3

    # Bottom Operational Specs Strip
    specs_y = col_y + col_h + 4
    spec_h = 20
    pdf.draw_card(18, specs_y, 174, spec_h, bg_color=pdf.c_accent_light, border_color=pdf.c_accent_border)
    
    spec_cols = [
        ("Analysis Domain", "4-Band Spectral DSP\n~10ms Ring Buffer\nComb Beat Tracking"),
        ("Visual Domain", "60 FPS NumPy Math\n11 Spatial Segments\nSmooth Morphing"),
        ("Scale & Hardware", "1,304 LEDs (Full Setup)\nDual-Channel GPIO / UDP\nRaspberry Pi 4 / CM4"),
        ("Live Interaction", "Asyncio Main Loop\nWebSocket Control\nReact Web Interface")
    ]
    
    sp_w = 174 / 4
    for i, (s_title, s_val) in enumerate(spec_cols):
        sx = 18 + i * sp_w
        pdf.set_xy(sx + 3, specs_y + 2)
        pdf.set_font("Arial", "B", 7.6)
        pdf.set_text_color(*pdf.c_accent)
        pdf.cell(sp_w - 6, 3.6, s_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(sx + 3, specs_y + 6.0)
        pdf.set_font("Arial", "", 7.0)
        pdf.set_text_color(*pdf.c_secondary)
        pdf.multi_cell(sp_w - 6, 3.4, s_val)

    pdf.draw_footer(page_num=2, total_pages=2)
    
    pdf.output(filename)
    print(f"Generated {filename} successfully with {pdf.page_no()} pages.")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "Vialactee_Project_Overview.pdf"
    build_pdf(out_file)
