"""
PSVaG Leistungsverwaltungssystem - Vollständig Annotiert
Automatische Formular-Generierung aus Python-Definitionen
"""

from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass, field
import json
from pathlib import Path

# Import Annotations
from annotations import (
    ui_field,
    calculated_field,
    workflow_step,
    ValidationRule,
    Conditions,
    CalculatedFieldRegistry,
    WorkflowStepRegistry
)

# Import Generator
from enhanced_form_generator import EnhancedFormGenerator


# ============================================================
# KONFIGURATION: VERSORGUNGSORDNUNG
# ============================================================

@dataclass
class VersorgungsordnungConfig:
    """Zentrale Konfiguration der Versorgungsordnung"""
    name: str = "Versorgungsordnung für die Angestellten der Muster GmbH vom 01.01.2010"
    
    # PSVaG-Insolvenzfall
    ist_insolvenzfall: bool = True
    insolvenzdatum: date = date(2026, 1, 1)
    
    # Stichtagsregelung
    stichtag: date = date(2003, 1, 1)
    
    # Alt-Regelung (vor Stichtag)
    alt_betrag_pro_jahr: float = 30.0  # Euro
    
    # Neu-Regelung (ab Stichtag)
    neu_versorgungssatz: float = 0.002  # 0,2% pro Jahr
    neu_max_versorgungsgrad: float = 0.05  # Max 5%
    
    # Kapitalwahlrecht
    kapital_wahlrecht: bool = True
    kapital_bagatellgrenze: float = 100.0  # Euro/Monat
    kapital_faktor: float = 120.0  # Monate
    
    # Invalidität
    invaliditaet_schutz: bool = True
    invaliditaet_wartezeit: int = 5  # Jahre
    
    # Hinterbliebene
    hinterbliebene_versorgung: bool = True
    hinterbliebene_witwe_satz: float = 60.0  # Prozent
    hinterbliebene_waisen_satz: float = 12.0  # Prozent


# ============================================================
# EINGABEFORMULAR MIT VOLLSTÄNDIGEN ANNOTATIONS
# ============================================================

@dataclass
class MitarbeiterFormular:
    """
    Vollständiges Eingabeformular für PSVaG Leistungsverwaltung
    
    Workflow:
    1. Eingabedaten (Identifikation, Stammdaten, Gehalt)
    2. Unverzallbarkeitsprüfung (nur bei Austrittsdatum)
    3. Berechnete Leistung (mit Formel-Prüfung)
    4. Gesamtübersicht (Leistungsbescheid)
    """
    
    # ==========================================
    # GRUPPE: IDENTIFIKATION
    # ==========================================
    
    id: str = field(
        metadata=ui_field(
            label="Personal-Nr.",
            typ="text",
            required=True,
            hint="Eindeutige Personalnummer",
            placeholder="z.B. MA-001",
            group="identifikation",
            order=1,
            validation=[ValidationRule.REQUIRED.value]
        )
    )
    
    name: str = field(
        metadata=ui_field(
            label="Name",
            typ="text",
            required=True,
            hint="Vor- und Nachname",
            placeholder="Max Mustermann",
            group="identifikation",
            order=2,
            validation=[ValidationRule.REQUIRED.value]
        )
    )
    
    # ==========================================
    # GRUPPE: STAMMDATEN
    # ==========================================
    
    geburtsdatum: Optional[date] = field(
        default=None,
        metadata=ui_field(
            label="Geburtsdatum",
            typ="date",
            required=True,
            hint="Für Berechnung des gesetzlichen Rentenalters nach SGB VI",
            group="stammdaten",
            order=1,
            validation=[
                ValidationRule.REQUIRED.value,
                ValidationRule.DATE_PAST.value
            ]
        )
    )
    
    eintrittsdatum: Optional[date] = field(
        default=None,
        metadata=ui_field(
            label="Eintrittsdatum im Unternehmen",
            typ="date",
            required=True,
            hint="Beginn des Arbeitsverhältnisses bei der Muster GmbH",
            group="stammdaten",
            order=2,
            validation=[
                ValidationRule.REQUIRED.value,
                ValidationRule.DATE_PAST.value,
                ValidationRule.DATE_AFTER_GEBURTSDATUM.value
            ]
        )
    )
    
    austrittsdatum: Optional[date] = field(
        default=None,
        metadata=ui_field(
            label="Austrittsdatum (leer = aktiver Mitarbeiter)",
            typ="date",
            required=False,
            hint="Nur bei ausgeschiedenen Mitarbeitern oder Insolvenzfall",
            group="stammdaten",
            order=3,
            validation=[ValidationRule.DATE_AFTER_EINTRITTSDATUM.value]
        )
    )
    
    # ==========================================
    # GRUPPE: GEHALT (CONDITIONAL)
    # ==========================================
    
    letztes_gehalt: Optional[float] = field(
        default=None,
        metadata=ui_field(
            label="Letztes Bruttomonatsgehalt (in €)",
            typ="number",
            required=False,
            hint="Erforderlich bei Neu-Regelung (Eintritt ab 01.01.2003)",
            placeholder="z.B. 4500.00",
            group="gehalt",
            order=1,
            min_value=0,
            validation=[ValidationRule.POSITIVE.value],
            # Conditional: Nur bei Neu-Regelung
            depends_on="eintrittsdatum",
            show_when="eintrittsdatum >= '2003-01-01'"
        )
    )


# ============================================================
# BERECHNUNGSKLASSE MIT CALCULATED FIELDS
# ============================================================

class VersorgungsBerechnung:
    """Zentrale Berechnungslogik mit Formel-Tracking"""
    
    def __init__(self, config: VersorgungsordnungConfig):
        self.config = config
    
    # ==========================================
    # HELPER METHODS (ohne Annotation)
    # ==========================================
    
    def gesetzliches_rentenalter(self, geburtsdatum: date) -> float:
        """Berechnet gesetzliches Rentenalter nach SGB VI"""
        geburtsjahr = geburtsdatum.year
        
        if geburtsjahr < 1947:
            return 65.0
        elif geburtsjahr >= 1964:
            return 67.0
        elif geburtsjahr <= 1958:
            # Von 1947 bis 1958: +1 Monat pro Jahrgang
            monate = geburtsjahr - 1946
            return 65 + monate / 12
        else:
            # Von 1959 bis 1963: 66 Jahre + 2 Monate pro Jahrgang
            monate = (geburtsjahr - 1958) * 2
            return 66 + monate / 12
    
    def rentenbeginn(self, geburtsdatum: date) -> date:
        """Berechnet geplanten Rentenbeginn (Monatserster)"""
        rentenalter = self.gesetzliches_rentenalter(geburtsdatum)
        rentenalter_jahre = int(rentenalter)
        rentenalter_monate = round((rentenalter - rentenalter_jahre) * 12)
        
        rentenjahr = geburtsdatum.year + rentenalter_jahre
        rentenmonat = geburtsdatum.month + rentenalter_monate
        
        if rentenmonat > 12:
            rentenjahr += 1
            rentenmonat -= 12
        
        return date(rentenjahr, rentenmonat, 1)
    
    def betriebszugehoerigkeit_tage(self, eintritt: date, austritt: date) -> int:
        """Berechnet Betriebszugehörigkeit in Tagen (taggenau)"""
        return (austritt - eintritt).days
    
    def unverfallbarkeit_pruefung(
        self, 
        geburtsdatum: date, 
        eintritt: date, 
        austritt: date
    ) -> tuple[bool, str]:
        """
        Prüft Unverfallbarkeit nach BetrAVG §1b
        Returns: (erfuellt, grund)
        """
        alter_bei_austritt = (austritt.year - geburtsdatum.year) - (
            1 if (austritt.month, austritt.day) < (geburtsdatum.month, geburtsdatum.day) else 0
        )
        
        dienstjahre = self.betriebszugehoerigkeit_jahre(eintritt, austritt)
        austrittsjahr = austritt.year
        
        # Regelung ab 2018
        if austrittsjahr >= 2018:
            if dienstjahre >= 3 and alter_bei_austritt >= 21:
                return (True, f"Erfüllt: {dienstjahre} Jahre Dienstzeit, {alter_bei_austritt} Jahre alt (Regelung ab 2018: mind. 3 Jahre + 21 Jahre)")
            else:
                return (False, f"Nicht erfüllt: {dienstjahre} Jahre Dienstzeit, {alter_bei_austritt} Jahre alt (Regelung ab 2018 erfordert: mind. 3 Jahre + 21 Jahre)")
        
        # Regelung 2009-2017
        elif austrittsjahr >= 2009:
            if dienstjahre >= 5 and alter_bei_austritt >= 25:
                return (True, f"Erfüllt: {dienstjahre} Jahre Dienstzeit, {alter_bei_austritt} Jahre alt")
            else:
                return (False, f"Nicht erfüllt: {dienstjahre} Jahre Dienstzeit, {alter_bei_austritt} Jahre alt (benötigt: 5 Jahre + 25 Jahre)")
        
        # Regelung vor 2009
        else:
            if dienstjahre >= 10:
                return (True, f"Erfüllt: {dienstjahre} Jahre Dienstzeit")
            elif dienstjahre >= 5 and alter_bei_austritt >= 30:
                return (True, f"Erfüllt: {dienstjahre} Jahre Dienstzeit, {alter_bei_austritt} Jahre alt")
            else:
                return (False, f"Nicht erfüllt (benötigt: 10 Jahre ODER 5 Jahre + 30 Jahre)")
    
    # ==========================================
    # CALCULATED FIELDS (mit Annotation)
    # ==========================================
    
    @calculated_field(
        key='dienstzeit',
        label='Potenzielle Dienstzeit (Eintritt → planm. Rentenbeginn)',
        formel='Rentenbeginn - Eintrittsdatum',
        requires=['eintrittsdatum', 'geburtsdatum'],
        einheit='Jahre',
        editable=True,
        needs_confirmation=True,
        confirmation_threshold=3,
        group='berechnungen',
        hint='Volle Jahre von Eintritt bis geplantem Rentenbeginn',
        precision=0
    )
    def betriebszugehoerigkeit_jahre(
        self, 
        eintrittsdatum: date, 
        geburtsdatum: date
    ) -> int:
        """
        Berechnet potenzielle Dienstzeit in vollendeten Jahren
        Eintritt bis geplanter Rentenbeginn
        """
        rentenbeginn = self.rentenbeginn(geburtsdatum)
        jahre = rentenbeginn.year - eintrittsdatum.year
        
        if (rentenbeginn.month, rentenbeginn.day) < (eintrittsdatum.month, eintrittsdatum.day):
            jahre -= 1
        
        return max(0, jahre)
    
    def mn_faktor(
        self,
        eintrittsdatum: date,
        austrittsdatum: date,
        geburtsdatum: date
    ) -> tuple[float, int, int]:
        """
        Berechnet m/n-Kürzungsfaktor bei vorzeitigem Austritt
        Returns: (faktor, m_tage, n_tage)
        """
        rentenbeginn = self.rentenbeginn(geburtsdatum)
        
        m = self.betriebszugehoerigkeit_tage(eintrittsdatum, austrittsdatum)
        n = self.betriebszugehoerigkeit_tage(eintrittsdatum, rentenbeginn)
        
        if n == 0:
            return (0.0, m, n)
        
        faktor = m / n
        return (faktor, m, n)
    
    @calculated_field(
        key='mn_faktor',
        label='m/n-Faktor (Kürzung bei vorzeitigem Austritt)',
        formel='m Tage / n Tage × 100',
        requires=['eintrittsdatum', 'austrittsdatum', 'geburtsdatum'],
        einheit='%',
        editable=True,
        needs_confirmation=True,
        confirmation_threshold=3,
        group='berechnungen',
        hint='Prozentualer Faktor für vorzeitigen Austritt (taggenau)',
        precision=2
    )
    def mn_faktor_prozent(
        self,
        eintrittsdatum: date,
        austrittsdatum: date,
        geburtsdatum: date
    ) -> float:
        """
        Berechnet m/n-Kürzungsfaktor bei vorzeitigem Austritt
        Returns: Prozent (0-100)
        """
        faktor, m, n = self.mn_faktor(eintrittsdatum, austrittsdatum, geburtsdatum)
        return faktor * 100
    
    @calculated_field(
        key='grundrente_alt',
        label='Monatliche Betriebsrente (Alt-Regelung)',
        formel='Dienstjahre × 30€ [× m/n bei Austritt]',
        requires=['eintrittsdatum', 'geburtsdatum'],
        einheit='€/Monat',
        editable=True,
        needs_confirmation=True,
        confirmation_threshold=3,
        group='berechnungen',
        hint='Alt-Regelung: 30€ pro Dienstjahr',
        precision=2
    )
    def grundrente_alt_berechnen(
        self,
        dienstjahre: float,
        eintrittsdatum: date,
        austrittsdatum: Optional[date] = None,
        geburtsdatum: Optional[date] = None
    ) -> float:
        """
        Berechnet Rente nach Alt-Regelung
        Verwendet ggf. überschriebene Dienstzeit
        """
        grundrente = dienstjahre * self.config.alt_betrag_pro_jahr
        
        # m/n-Faktor bei vorzeitigem Austritt
        if austrittsdatum and geburtsdatum:
            mn_prozent = self.mn_faktor_prozent(eintrittsdatum, austrittsdatum, geburtsdatum)
            return grundrente * (mn_prozent / 100)
        
        return grundrente
    
    @calculated_field(
        key='grundrente_neu',
        label='Monatliche Betriebsrente (Neu-Regelung)',
        formel='Dienstjahre × 0,2% × Gehalt [× m/n bei Austritt]',
        requires=['eintrittsdatum', 'geburtsdatum', 'letztes_gehalt'],
        einheit='€/Monat',
        editable=True,
        needs_confirmation=True,
        confirmation_threshold=3,
        group='berechnungen',
        hint='Neu-Regelung: 0,2% vom Gehalt pro Dienstjahr (max. 5%)',
        precision=2
    )
    def grundrente_neu_berechnen(
        self,
        dienstjahre: float,
        letztes_gehalt: float,
        eintrittsdatum: date,
        austrittsdatum: Optional[date] = None,
        geburtsdatum: Optional[date] = None
    ) -> float:
        """
        Berechnet Rente nach Neu-Regelung
        Verwendet ggf. überschriebene Dienstzeit
        """
        jahresrente = dienstjahre * self.config.neu_versorgungssatz * letztes_gehalt
        max_rente = self.config.neu_max_versorgungsgrad * letztes_gehalt
        grundrente = min(jahresrente, max_rente)
        
        # m/n-Faktor bei vorzeitigem Austritt
        if austrittsdatum and geburtsdatum:
            mn_prozent = self.mn_faktor_prozent(eintrittsdatum, austrittsdatum, geburtsdatum)
            return grundrente * (mn_prozent / 100)
        
        return grundrente


# ============================================================
# WORKFLOW DEFINITION
# ============================================================

@workflow_step(
    order=1,
    title="Eingabedaten",
    description="Erfassung der Mitarbeiterdaten aus Personaldatenbank",
    groups=['identifikation', 'stammdaten', 'gehalt'],
    component_type="form"
)
class SchrittEingabe:
    """Schritt 1: Dateneingabe"""
    dataclass = MitarbeiterFormular
    show_data_import = True


@workflow_step(
    order=2,
    title="Unverzallbarkeitsprüfung",
    description="Prüfung nach BetrAVG §1b",
    show_if=Conditions.has_austrittsdatum,
    component_type="custom"
)
class SchrittUnverfallbarkeit:
    """Schritt 2: Unverzallbarkeitsprüfung"""
    pass


@workflow_step(
    order=3,
    title="Berechnete Leistung (überschreibbar)",
    description="Berechnung mit Formel-Prüfung",
    component_type="calculation"
)
class SchrittBerechnungen:
    """Schritt 3: Berechnungen"""
    calculations = ['dienstzeit', 'mn_faktor', 'grundrente_alt', 'grundrente_neu']
    enable_confirmation = True
    confirmation_threshold = 3
    allow_override = True


@workflow_step(
    order=4,
    title="PSVaG Leistungsberechnung",
    description="Gesamtübersicht für Leistungsbescheid",
    component_type="summary"
)
class SchrittUebersicht:
    """Schritt 4: Gesamtübersicht"""
    sections = [
        'art_der_leistung',
        'monatliche_rente',
        'termin_faelligkeit',
        'anpassung_ab_faelligkeit',
        'anpassung_austritt_bis_faelligkeit',
        'zuschlag_abschlag',
        'invaliditaet',
        'hinterbliebene'
    ]
    enable_print = True
    print_button_label = "Leistungsbescheid drucken"


# ============================================================
# HAUPTFUNKTION - DEMO
# ============================================================

def main():
    """Demonstriert die automatische Formular-Generierung"""
    
    print("=" * 80)
    print("PSVaG LEISTUNGSVERWALTUNG - AUTOMATISCHE FORMULAR-GENERIERUNG")
    print("=" * 80)
    print()
    
    # 1. Konfiguration erstellen
    config = VersorgungsordnungConfig()
    
    print("1. KONFIGURATION")
    print("-" * 80)
    print(f"Versorgungsordnung: {config.name}")
    print(f"PSVaG-Insolvenzfall: {config.ist_insolvenzfall}")
    print(f"Insolvenzdatum: {config.insolvenzdatum.strftime('%d.%m.%Y')}")
    print(f"Stichtag Alt/Neu: {config.stichtag.strftime('%d.%m.%Y')}")
    print()
    
    # 2. Berechnungsklasse initialisieren (registriert calculated_fields)
    berechnung = VersorgungsBerechnung(config)
    
    print("2. REGISTRIERTE CALCULATED FIELDS")
    print("-" * 80)
    for key, meta in CalculatedFieldRegistry.get_all().items():
        print(f"✓ {meta['label']} ({key})")
        print(f"  Formel: {meta['formel']}")
        print(f"  Benötigt: {', '.join(meta['requires'])}")
        print()
    
    # 3. Generator erstellen
    generator = EnhancedFormGenerator(
        input_dataclass=MitarbeiterFormular,
        config=config,
        berechnung_class=berechnung
    )
    
    print("3. SCHEMA GENERIEREN")
    print("-" * 80)
    
    schema = generator.generate_complete_schema()
    
    print(f"Input Fields: {len(schema['input_fields'])}")
    print(f"Calculated Fields: {len(schema['calculated_fields'])}")
    print(f"Workflow Steps: {len(schema['workflow']['steps'])}")
    print(f"Groups: {', '.join(schema['groups'].keys())}")
    print()
    
    # 4. Dateien speichern
    print("4. DATEIEN GENERIEREN")
    print("-" * 80)
    
    files = generator.save_all()
    
    for file_type, filepath in files.items():
        size_kb = filepath.stat().st_size / 1024
        print(f"✓ {file_type:12s}: {filepath.name:40s} ({size_kb:.1f} KB)")
    
    print()
    
    # 5. Schema-Ausgabe
    print("5. SCHEMA-DETAILS")
    print("-" * 80)
    print()
    
    print("Input Fields by Group:")
    for group_name, group_fields in schema['groups'].items():
        print(f"\n  {group_name.upper()}:")
        for field_def in group_fields:
            req = " *" if field_def.get('required') else ""
            print(f"    - {field_def['label']}{req} ({field_def['type']})")
            if field_def.get('hint'):
                print(f"      → {field_def['hint']}")
    
    print()
    print("Workflow Steps:")
    for step in schema['workflow']['steps']:
        print(f"  {step['order']}. {step['title']}")
        if step.get('description'):
            print(f"     → {step['description']}")
    
    print()
    print("=" * 80)
    print("GENERIERUNG ABGESCHLOSSEN")
    print("=" * 80)
    print()
    print("Vorteile:")
    print("  ✓ Eine Quelle der Wahrheit (Python)")
    print("  ✓ Automatische UI-Generierung")
    print("  ✓ Type Safety (TypeScript)")
    print("  ✓ Konsistenz zwischen Backend und Frontend")
    print("  ✓ Formel-Prüfung automatisch integriert")
    print("  ✓ Workflow-Schritte deklarativ definiert")
    print()
    print("Nächste Schritte:")
    print("  1. Schema in React-App importieren")
    print("  2. Generierte Components verwenden")
    print("  3. Backend-Berechnungen anbinden")
    print()


if __name__ == "__main__":
    main()
