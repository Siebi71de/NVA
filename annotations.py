"""
Vollständiges Annotation-System für automatische Formular-Generierung
Ermöglicht deklarative Definition von UI-Elementen in Python
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, Callable, List, Any, Tuple, Union
from datetime import date
from enum import Enum
from functools import wraps


# ============================================================
# UI FIELD METADATA
# ============================================================

def ui_field(
    label: str = None,
    typ: Literal["text", "number", "date", "select", "checkbox"] = None,
    required: bool = None,
    hint: str = None,
    placeholder: str = None,
    group: str = "default",
    order: int = 0,
    # Validierung
    validation: Union[str, List[str]] = None,
    min_value: float = None,
    max_value: float = None,
    # Conditional Logic
    depends_on: str = None,
    show_when: str = None,  # JavaScript expression oder Python callable
    # UI Options
    options: List[Tuple[str, str]] = None,  # Für select: [(value, label), ...]
    # Styling
    width: Literal["full", "half", "third"] = "full",
    css_class: str = None
) -> dict:
    """
    Factory für UI-Metadaten an Dataclass Fields
    
    Args:
        label: Anzeigetext im Formular (default: field_name.title())
        typ: UI-Feldtyp (default: aus Python-Type abgeleitet)
        required: Pflichtfeld (default: aus Optional abgeleitet)
        hint: Hilfetext unter dem Feld
        placeholder: Placeholder im Eingabefeld
        group: Gruppierung für Sections (default: "default")
        order: Sortierung innerhalb der Gruppe
        validation: Validierungsregel(n) als String oder Liste
        min_value: Minimum für Number-Felder
        max_value: Maximum für Number-Felder
        depends_on: Zeigt Feld nur wenn anderes Feld gesetzt ist
        show_when: JavaScript-Expression oder Python-Callable für Conditional
        options: Liste von (value, label) für Select-Felder
        width: Breite des Feldes im Layout
        css_class: Zusätzliche CSS-Klassen
    
    Returns:
        Dictionary mit UI-Metadaten
    
    Example:
        >>> @dataclass
        >>> class Person:
        >>>     name: str = field(metadata=ui_field(
        >>>         label="Vollständiger Name",
        >>>         hint="Vor- und Nachname",
        >>>         required=True
        >>>     ))
    """
    metadata = {}
    
    if label is not None: metadata['ui_label'] = label
    if typ is not None: metadata['ui_type'] = typ
    if required is not None: metadata['ui_required'] = required
    if hint is not None: metadata['ui_hint'] = hint
    if placeholder is not None: metadata['ui_placeholder'] = placeholder
    if group is not None: metadata['ui_group'] = group
    if order is not None: metadata['ui_order'] = order
    
    # Validation
    if validation is not None:
        metadata['ui_validation'] = validation if isinstance(validation, list) else [validation]
    if min_value is not None: metadata['ui_min'] = min_value
    if max_value is not None: metadata['ui_max'] = max_value
    
    # Conditional Logic
    if depends_on is not None: metadata['ui_depends_on'] = depends_on
    if show_when is not None: metadata['ui_show_when'] = show_when
    
    # Options
    if options is not None: metadata['ui_options'] = options
    
    # Styling
    if width is not None: metadata['ui_width'] = width
    if css_class is not None: metadata['ui_class'] = css_class
    
    return metadata


# ============================================================
# CALCULATED FIELD REGISTRY & DECORATOR
# ============================================================

class CalculatedFieldRegistry:
    """Globale Registry für alle berechneten Felder"""
    _fields = {}
    
    @classmethod
    def register(cls, metadata):
        """Registriert ein berechnetes Feld"""
        cls._fields[metadata['key']] = metadata
    
    @classmethod
    def get_all(cls):
        """Gibt alle registrierten Felder zurück"""
        return cls._fields
    
    @classmethod
    def get(cls, key: str):
        """Gibt ein spezifisches Feld zurück"""
        return cls._fields.get(key)
    
    @classmethod
    def clear(cls):
        """Löscht alle registrierten Felder (für Tests)"""
        cls._fields = {}


def calculated_field(
    key: str,
    label: str,
    formel: str,
    requires: List[str],
    einheit: str = "",
    editable: bool = True,
    needs_confirmation: bool = True,
    confirmation_threshold: int = 3,
    group: str = "berechnungen",
    hint: str = None,
    precision: int = 2
):
    """
    Decorator für berechnete Felder mit Formel-Prüfung
    
    Args:
        key: Eindeutiger Schlüssel für Tracking
        label: Anzeigetext
        formel: Human-readable Formel (z.B. "Rentenbeginn - Eintrittsdatum")
        requires: Liste der benötigten Input-Felder
        einheit: Anzeigeeinheit (z.B. "Jahre", "€/Monat")
        editable: Kann Nutzer den Wert überschreiben?
        needs_confirmation: Braucht 3x Bestätigung?
        confirmation_threshold: Anzahl Bestätigungen (default: 3)
        group: Gruppierung
        hint: Hilfetext
        precision: Dezimalstellen für Zahlen
    
    Returns:
        Decorated function
    
    Example:
        >>> @calculated_field(
        >>>     key='dienstzeit',
        >>>     label='Potenzielle Dienstzeit',
        >>>     formel='Rentenbeginn - Eintrittsdatum',
        >>>     requires=['eintrittsdatum', 'geburtsdatum'],
        >>>     einheit='Jahre'
        >>> )
        >>> def berechne_dienstzeit(eintrittsdatum: date, geburtsdatum: date) -> float:
        >>>     # Berechnung hier
        >>>     return jahre
    """
    def decorator(func: Callable):
        # Erstelle Metadata
        metadata = {
            'key': key,
            'label': label,
            'formel': formel,
            'requires': requires,
            'einheit': einheit,
            'editable': editable,
            'needs_confirmation': needs_confirmation,
            'confirmation_threshold': confirmation_threshold,
            'group': group,
            'hint': hint,
            'precision': precision,
            'function': func,
            'function_name': func.__name__
        }
        
        # Registriere in globaler Registry
        CalculatedFieldRegistry.register(metadata)
        
        # Attach metadata to function
        func._calculation_metadata = metadata
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ============================================================
# VALIDATION RULES
# ============================================================

class ValidationRule(Enum):
    """Vordefinierte Validierungsregeln"""
    REQUIRED = "required"
    EMAIL = "email"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    DATE_PAST = "date_in_past"
    DATE_FUTURE = "date_in_future"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    
    # Custom für Versorgung
    DATE_AFTER_EINTRITTSDATUM = "date_after_eintrittsdatum"
    DATE_AFTER_GEBURTSDATUM = "date_after_geburtsdatum"
    GEHALT_BEI_NEU_REGELUNG = "gehalt_bei_neu_regelung"


class ValidationRuleImpl:
    """Implementierung der Validierungsregeln"""
    
    @staticmethod
    def validate(rule: str, value: Any, context: dict = None) -> Tuple[bool, str]:
        """
        Validiert einen Wert gegen eine Regel
        
        Args:
            rule: Regelname
            value: Zu validierender Wert
            context: Kontext-Daten (andere Felder)
        
        Returns:
            (is_valid, error_message)
        """
        context = context or {}
        
        if rule == "required":
            valid = value is not None and value != ""
            return (valid, "Dieses Feld ist erforderlich" if not valid else "")
        
        if rule == "date_in_past":
            if not value:
                return (True, "")
            try:
                d = date.fromisoformat(value) if isinstance(value, str) else value
                valid = d < date.today()
                return (valid, "Datum muss in der Vergangenheit liegen" if not valid else "")
            except:
                return (False, "Ungültiges Datum")
        
        if rule == "date_after_eintrittsdatum":
            if not value or 'eintrittsdatum' not in context:
                return (True, "")
            try:
                d = date.fromisoformat(value) if isinstance(value, str) else value
                eintritt = date.fromisoformat(context['eintrittsdatum']) if isinstance(context['eintrittsdatum'], str) else context['eintrittsdatum']
                valid = d >= eintritt
                return (valid, "Austrittsdatum muss nach Eintrittsdatum liegen" if not valid else "")
            except:
                return (False, "Ungültiges Datum")
        
        if rule == "positive":
            try:
                valid = float(value) > 0
                return (valid, "Wert muss positiv sein" if not valid else "")
            except:
                return (False, "Ungültige Zahl")
        
        # Default: Regel nicht bekannt
        return (True, "")


# ============================================================
# WORKFLOW STEPS
# ============================================================

class WorkflowStepRegistry:
    """Registry für Workflow-Schritte"""
    _steps = []
    
    @classmethod
    def register(cls, step_def):
        """Registriert einen Workflow-Schritt"""
        cls._steps.append(step_def)
        cls._steps.sort(key=lambda x: x['order'])
    
    @classmethod
    def get_all(cls):
        """Gibt alle Schritte zurück"""
        return cls._steps
    
    @classmethod
    def clear(cls):
        """Löscht alle Schritte (für Tests)"""
        cls._steps = []


def workflow_step(
    order: int,
    title: str,
    description: str = None,
    groups: List[str] = None,
    show_if: Callable = None,
    component_type: Literal["form", "calculation", "summary", "custom"] = "form"
):
    """
    Decorator für Workflow-Schritte
    
    Args:
        order: Reihenfolge (1, 2, 3, 4)
        title: Schritt-Titel
        description: Optionale Beschreibung
        groups: Welche Feld-Gruppen in diesem Schritt anzeigen
        show_if: Callable die prüft ob Schritt angezeigt wird
        component_type: Art des Schrittes
    
    Returns:
        Decorated class
    
    Example:
        >>> @workflow_step(
        >>>     order=1,
        >>>     title="Eingabedaten",
        >>>     description="Erfassung der Mitarbeiterdaten",
        >>>     groups=['identifikation', 'stammdaten'],
        >>>     component_type="form"
        >>> )
        >>> class EingabeStep:
        >>>     pass
    """
    def decorator(cls):
        step_def = {
            'order': order,
            'title': title,
            'description': description,
            'groups': groups or [],
            'show_if': show_if,
            'component_type': component_type,
            'class': cls,
            'class_name': cls.__name__
        }
        
        WorkflowStepRegistry.register(step_def)
        
        return cls
    
    return decorator


# ============================================================
# CONDITIONAL LOGIC HELPERS
# ============================================================

class Conditions:
    """Vordefinierte Condition-Funktionen"""
    
    @staticmethod
    def is_neu_regelung(data: dict, stichtag: str = '2003-01-01') -> bool:
        """Prüft ob Neu-Regelung (Eintritt >= Stichtag)"""
        eintritt = data.get('eintrittsdatum')
        if not eintritt:
            return False
        if isinstance(eintritt, str):
            eintritt = date.fromisoformat(eintritt)
        return eintritt >= date.fromisoformat(stichtag)
    
    @staticmethod
    def has_austrittsdatum(data: dict) -> bool:
        """Prüft ob Austrittsdatum vorhanden"""
        return bool(data.get('austrittsdatum'))
    
    @staticmethod
    def is_unverfallbar(data: dict) -> bool:
        """Prüft Unverfallbarkeit (wird vom Backend berechnet)"""
        return data.get('_computed', {}).get('ist_unverfallbar', False)


def show_if(condition_func: Callable[[dict], bool]):
    """
    Decorator für conditional rendering
    
    Example:
        >>> @show_if(lambda data: data.get('eintrittsdatum') >= date(2003, 1, 1))
        >>> class GehaltsEingabe:
        >>>     pass
    """
    def decorator(item):
        item._show_if = condition_func
        return item
    return decorator
