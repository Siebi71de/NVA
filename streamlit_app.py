"""
PSVaG Leistungsverwaltung - Vollständig in Python
Streamlit Frontend - Schema-Driven
Komplette Portierung des React Click-Dummies
"""

import streamlit as st
import json
from datetime import date, datetime
from pathlib import Path
import sys

# Backend importieren
sys.path.insert(0, str(Path(__file__).parent))
try:
    from psvag_annotated import (
        VersorgungsordnungConfig,
        VersorgungsBerechnung,
    )
except ImportError:
    st.error("Backend-Module nicht gefunden! Bitte `psvag_annotated.py` prüfen.")
    st.stop()

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="PSVaG Leistungsverwaltung",
    page_icon="💼",
    layout="wide"
)

# ============================================================
# SCHEMA LADEN
# ============================================================

@st.cache_data
def load_schema():
    schema_path = Path(__file__).parent / 'complete_schema.json'
    if schema_path.exists():
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

SCHEMA = load_schema()

# ============================================================
# INITIALISIERUNG
# ============================================================

config = VersorgungsordnungConfig()
berechnung = VersorgungsBerechnung(config)

# Session State
if 'parameter' not in st.session_state:
    st.session_state.parameter = {}
if 'formel_bestaetigung' not in st.session_state:
    st.session_state.formel_bestaetigung = {}
if 'ma_bestaetigt' not in st.session_state:
    st.session_state.ma_bestaetigt = {}

# Beispiel-Mitarbeiter
BEISPIEL_MITARBEITER = [
    {
        'name': 'Max Mustermann',
        'beschreibung': 'Alt-Regelung, 25 Jahre',
        'daten': {
            'id': 'max-alt',
            'name': 'Max Mustermann',
            'geburtsdatum': date(1960, 3, 15),
            'eintrittsdatum': date(2000, 1, 1),
            'austrittsdatum': config.insolvenzdatum,
        }
    },
    {
        'name': 'Anna Schmidt',
        'beschreibung': 'Neu-Regelung, 4.500€',
        'daten': {
            'id': 'anna-neu',
            'name': 'Anna Schmidt',
            'geburtsdatum': date(1980, 7, 22),
            'eintrittsdatum': date(2010, 3, 1),
            'austrittsdatum': config.insolvenzdatum,
            'letztes_gehalt': 4500.0
        }
    },
    {
        'name': 'Tom Klein',
        'beschreibung': 'Bagatellrente',
        'daten': {
            'id': 'tom-bagatell',
            'name': 'Tom Klein',
            'geburtsdatum': date(1988, 9, 20),
            'eintrittsdatum': date(2020, 1, 1),
            'austrittsdatum': config.insolvenzdatum,
            'letztes_gehalt': 2500.0
        }
    }
]

# ============================================================
# HEADER
# ============================================================

st.title("💼 PSVaG Leistungsverwaltung")
st.caption(config.name)

col1, col2, col3 = st.columns([2, 1, 1])
with col2:
    st.success("🔗 Schema-Driven")
with col3:
    st.info("🐍 Pure Python")

if config.ist_insolvenzfall:
    st.info(f"📋 **PSVaG Sicherungsfall** | Insolvenzdatum: {config.insolvenzdatum.strftime('%d.%m.%Y')}")

st.divider()

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(["📝 Beschreibung", "🔍 Schema", "🧮 Berechnung"])

# TAB 1: BESCHREIBUNG
with tab1:
    st.header("Beschreibung der Versorgungsordnung")
    
    st.subheader("§1 Grundlagen")
    st.write("Die betriebliche Altersversorgung wird als **lebenslange monatliche Rente** gewährt.")
    
    st.subheader(f"§2 Berechnung (Stichtag: {config.stichtag.strftime('%d.%m.%Y')})")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        **Alt-Regelung** (vor Stichtag)
        ```
        Rente = Jahre × {config.alt_betrag_pro_jahr}€
        ```
        Beispiel: 30 Jahre × 30€ = 900€/Monat
        """)
    with col2:
        st.info(f"""
        **Neu-Regelung** (ab Stichtag)
        ```
        Rente = Jahre × {config.neu_versorgungssatz*100}% × Gehalt
        ```
        Max: {config.neu_max_versorgungsgrad*100}% vom Gehalt
        """)
    
    st.subheader("§3 Features")
    if config.kapital_wahlrecht:
        st.write(f"✓ Kapitalwahlrecht bei Rente < {config.kapital_bagatellgrenze}€")
    if config.invaliditaet_schutz:
        st.write(f"✓ Invaliditätsschutz (Wartezeit: {config.invaliditaet_wartezeit} Jahre)")
    if config.hinterbliebene_versorgung:
        st.write(f"✓ Hinterbliebenenversorgung: {config.hinterbliebene_witwe_satz}% / {config.hinterbliebene_waisen_satz}%")

# TAB 2: SCHEMA
with tab2:
    st.header("Schema-Ansicht")
    
    if SCHEMA:
        subtab1, subtab2, subtab3 = st.tabs(["Input Fields", "Calculated Fields", "Workflow"])
        
        with subtab1:
            for field in SCHEMA['input_fields']:
                with st.expander(f"{field['label']} ({field['id']})"):
                    st.write(f"**Typ:** {field['type']}")
                    st.write(f"**Gruppe:** {field['group']}")
                    if field.get('hint'):
                        st.info(field['hint'])
        
        with subtab2:
            for calc in SCHEMA['calculated_fields']:
                with st.expander(f"{calc['label']}"):
                    st.code(calc['formel'])
                    st.write(f"**Benötigt:** {', '.join(calc['requires'])}")
                    st.write(f"**Einheit:** {calc['einheit']}")
        
        with subtab3:
            for step in SCHEMA['workflow']['steps']:
                st.markdown(f"**{step['order']}. {step['title']}**")
                if step.get('description'):
                    st.caption(step['description'])

# TAB 3: BERECHNUNG
with tab3:
    st.header("Leistungsberechnung")
    
    # SCHRITT 1: EINGABE
    with st.expander("📝 Schritt 1: Eingabedaten", expanded=True):
        # Datenimport
        st.subheader("Datenimport")
        cols = st.columns(len(BEISPIEL_MITARBEITER))
        for idx, person in enumerate(BEISPIEL_MITARBEITER):
            with cols[idx]:
                st.write(f"**{person['name']}**")
                st.caption(person['beschreibung'])
                if st.button("Laden", key=f"load_{idx}"):
                    st.session_state.parameter = person['daten'].copy()
                    st.rerun()
        
        st.divider()
        
        # Felder
        if SCHEMA:
            groups = {}
            for field in SCHEMA['input_fields']:
                g = field['group']
                if g not in groups:
                    groups[g] = []
                groups[g].append(field)
            
            labels = {'identifikation': 'Identifikation', 'stammdaten': 'Stammdaten', 'gehalt': 'Gehaltsdaten'}
            
            for group_name, fields in groups.items():
                st.subheader(labels.get(group_name, group_name))
                
                for field in fields:
                    # Conditional
                    if field.get('depends_on') and not st.session_state.parameter.get(field['depends_on']):
                        continue
                    
                    if field.get('show_when'):
                        eintritt = st.session_state.parameter.get('eintrittsdatum')
                        if eintritt and isinstance(eintritt, date):
                            if field['id'] == 'letztes_gehalt' and eintritt < config.stichtag:
                                continue
                    
                    # Render
                    label = f"{field['label']} {'*' if field.get('required') else ''}"
                    
                    if field['type'] == 'text':
                        val = st.text_input(label, value=st.session_state.parameter.get(field['id'], ''), 
                                          help=field.get('hint'), key=f"f_{field['id']}")
                        st.session_state.parameter[field['id']] = val
                    
                    elif field['type'] == 'number':
                        val = st.number_input(label, value=float(st.session_state.parameter.get(field['id'], 0)), 
                                            min_value=field.get('min_value', 0.0), step=0.01,
                                            help=field.get('hint'), key=f"f_{field['id']}")
                        st.session_state.parameter[field['id']] = val
                    
                    elif field['type'] == 'date':
                        current = st.session_state.parameter.get(field['id'])
                        val = st.date_input(label, value=current if isinstance(current, date) else None,
                                          help=field.get('hint'), key=f"f_{field['id']}")
                        st.session_state.parameter[field['id']] = val
    
    # SCHRITT 2: UNVERZALLBARKEIT
    if all([st.session_state.parameter.get('austrittsdatum'),
            st.session_state.parameter.get('geburtsdatum'),
            st.session_state.parameter.get('eintrittsdatum')]):
        
        with st.expander("⚖️ Schritt 2: Unverzallbarkeitsprüfung", expanded=True):
            ist_unverfallbar, grund = berechnung.unverfallbarkeit_pruefung(
                st.session_state.parameter['geburtsdatum'],
                st.session_state.parameter['eintrittsdatum'],
                st.session_state.parameter['austrittsdatum']
            )
            
            if ist_unverfallbar:
                st.success(f"✓ **Unverfallbarkeit erfüllt**")
                st.info(grund)
            else:
                st.error(f"✗ **Unverfallbarkeit NICHT erfüllt**")
                st.warning(grund)
                st.warning("⚠️ Kein Anspruch - weitere Berechnungen entfallen")
                st.stop()
    
    # SCHRITT 3: BERECHNUNGEN
    if all([st.session_state.parameter.get('geburtsdatum'),
            st.session_state.parameter.get('eintrittsdatum')]):
        
        with st.expander("🧮 Schritt 3: Berechnete Leistung", expanded=True):
            if SCHEMA:
                for calc in SCHEMA['calculated_fields']:
                    # Requirements check
                    if not all(st.session_state.parameter.get(r) for r in calc['requires']):
                        continue
                    
                    # Berechne
                    wert = 0
                    
                    if calc['id'] == 'dienstzeit':
                        wert = berechnung.betriebszugehoerigkeit_jahre(
                            st.session_state.parameter['eintrittsdatum'],
                            st.session_state.parameter['geburtsdatum']
                        )
                    
                    elif calc['id'] == 'mn_faktor':
                        if st.session_state.parameter.get('austrittsdatum'):
                            f, m, n = berechnung.mn_faktor(
                                st.session_state.parameter['eintrittsdatum'],
                                st.session_state.parameter['austrittsdatum'],
                                st.session_state.parameter['geburtsdatum']
                            )
                            wert = round(f * 100, 2)
                    
                    elif calc['id'] in ['grundrente_alt', 'grundrente_neu']:
                        ist_alt = st.session_state.parameter['eintrittsdatum'] < config.stichtag
                        
                        if (calc['id'] == 'grundrente_alt' and not ist_alt) or \
                           (calc['id'] == 'grundrente_neu' and ist_alt):
                            continue
                        
                        bzg = st.session_state.parameter.get('dienstzeit_berechnet', 
                            berechnung.betriebszugehoerigkeit_jahre(
                                st.session_state.parameter['eintrittsdatum'],
                                st.session_state.parameter['geburtsdatum']))
                        
                        if isinstance(bzg, str):
                            bzg = float(bzg)
                        
                        gehalt = st.session_state.parameter.get('letztes_gehalt', 0)
                        
                        if calc['id'] == 'grundrente_alt':
                            wert = bzg * config.alt_betrag_pro_jahr
                        else:
                            satz = min(bzg * config.neu_versorgungssatz, config.neu_max_versorgungsgrad)
                            wert = gehalt * satz
                        
                        # m/n
                        if st.session_state.parameter.get('austrittsdatum'):
                            mn = st.session_state.parameter.get('mn_faktor_berechnet')
                            if mn is None:
                                f, m, n = berechnung.mn_faktor(
                                    st.session_state.parameter['eintrittsdatum'],
                                    st.session_state.parameter['austrittsdatum'],
                                    st.session_state.parameter['geburtsdatum'])
                                mn = f * 100
                            wert = wert * (float(mn) / 100)
                        
                        wert = round(wert, 2)
                    
                    # Render
                    st.markdown(f"#### {calc['label']}")
                    st.caption(f"📐 Formel: `{calc['formel']}`")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        field_id = f"{calc['id']}_berechnet"
                        current = st.session_state.parameter.get(field_id, wert)
                        if calc.get('editable', True):
                            val = st.number_input(f"Wert ({calc['einheit']})", value=float(current), 
                                                step=0.01, key=f"c_{calc['id']}")
                            st.session_state.parameter[field_id] = val
                        else:
                            st.metric("", f"{wert} {calc['einheit']}")
                    
                    with col2:
                        # Bestätigung
                        threshold = calc.get('confirmation_threshold', 3)
                        bestaetigt = st.session_state.formel_bestaetigung.get(calc['id'], 0)
                        
                        if bestaetigt >= threshold:
                            st.success("✓ Geprüft")
                        elif calc.get('needs_confirmation', True):
                            st.warning(f"{bestaetigt}/{threshold}")
                            
                            ma_id = f"{st.session_state.parameter.get('geburtsdatum')}_{st.session_state.parameter.get('eintrittsdatum')}"
                            ma_geprueft = st.session_state.ma_bestaetigt.get(ma_id, {}).get(calc['id'], False)
                            
                            if not ma_geprueft and bestaetigt < threshold:
                                if st.button("✓", key=f"btn_{calc['id']}"):
                                    st.session_state.formel_bestaetigung[calc['id']] = bestaetigt + 1
                                    if ma_id not in st.session_state.ma_bestaetigt:
                                        st.session_state.ma_bestaetigt[ma_id] = {}
                                    st.session_state.ma_bestaetigt[ma_id][calc['id']] = True
                                    st.rerun()
                    
                    st.caption(f"Berechnet: {wert} {calc['einheit']}")
                    st.divider()
    
    # SCHRITT 4: ÜBERSICHT
    if st.session_state.parameter.get('geburtsdatum') and st.session_state.parameter.get('eintrittsdatum'):
        with st.expander("📋 Schritt 4: Gesamtübersicht", expanded=True):
            ist_alt = st.session_state.parameter['eintrittsdatum'] < config.stichtag
            
            rente = st.session_state.parameter.get('grundrente_alt_berechnet' if ist_alt else 'grundrente_neu_berechnet')
            
            if rente:
                rente = float(rente)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Monatliche Rente", f"{rente:.2f} €")
                with col2:
                    rentenbeginn = berechnung.rentenbeginn(st.session_state.parameter['geburtsdatum'])
                    st.metric("Rentenbeginn", rentenbeginn)
                with col3:
                    if config.kapital_wahlrecht and rente < config.kapital_bagatellgrenze:
                        st.metric("Kapitalabfindung", f"{rente * config.kapital_faktor:.2f} €")
                    else:
                        st.metric("Art", "Rente")
                
                st.markdown("### Weitere Regelungen")
                st.write("**Anpassung ab Fälligkeit:** BetrAVG §16 (jährlich)")
                st.write("**Anpassung vor Rentenbeginn:** 0 (keine)")
                
                if config.invaliditaet_schutz:
                    st.write(f"**Invalidität:** Volle Rente bei Berufsunfähigkeit (Wartezeit: {config.invaliditaet_wartezeit} Jahre)")
                
                if config.hinterbliebene_versorgung:
                    st.write(f"**Hinterbliebene:** Witwe/r {config.hinterbliebene_witwe_satz}%, Waisen {config.hinterbliebene_waisen_satz}%")
                
                st.divider()
                if st.button("🖨️ Leistungsbescheid drucken", type="primary"):
                    st.success("Druckfunktion würde hier starten")

# FOOTER
st.divider()
col1, col2, col3 = st.columns(3)
if SCHEMA:
    with col1:
        st.caption(f"📊 {len(SCHEMA['input_fields'])} Input Fields")
    with col2:
        st.caption(f"🧮 {len(SCHEMA['calculated_fields'])} Calculated Fields")
    with col3:
        st.caption(f"🔄 {len(SCHEMA['workflow']['steps'])} Workflow Steps")
