"""
Enhanced Form Generator
Generiert UI-Schemas, React Components und TypeScript aus annotierten Python-Klassen
"""

import json
from dataclasses import fields, is_dataclass
from typing import get_type_hints, get_origin, get_args, Union, Dict, List, Any
from datetime import date, datetime
from pathlib import Path
import inspect

from annotations import (
    CalculatedFieldRegistry,
    WorkflowStepRegistry,
    ValidationRule
)


class EnhancedFormGenerator:
    """
    Vollständiger Generator für UI-Schemas aus annotierten Python-Code
    
    Features:
    - Input Fields aus Dataclass
    - Calculated Fields aus @calculated_field
    - Workflow Steps aus @workflow_step
    - Validation Rules
    - Conditional Logic
    - TypeScript Interfaces
    - React Components
    """
    
    def __init__(
        self,
        input_dataclass,
        config: Any = None,
        berechnung_class: Any = None
    ):
        """
        Initialisiert den Generator
        
        Args:
            input_dataclass: Dataclass mit Input-Feldern
            config: Konfigurationsobjekt
            berechnung_class: Klasse mit Berechnungsmethoden
        """
        if not is_dataclass(input_dataclass):
            raise ValueError(f"{input_dataclass} muss eine Dataclass sein")
        
        self.input_dataclass = input_dataclass
        self.config = config
        self.berechnung_class = berechnung_class
        
        self.type_hints = get_type_hints(input_dataclass)
    
    def _infer_ui_type(self, python_type) -> str:
        """Leitet UI-Typ aus Python-Typ ab"""
        # Handle Optional[X]
        origin = get_origin(python_type)
        if origin is Union:
            args = get_args(python_type)
            python_type = next((arg for arg in args if arg is not type(None)), str)
        
        # Type mapping
        type_map = {
            str: 'text',
            int: 'number',
            float: 'number',
            bool: 'checkbox',
            date: 'date',
        }
        
        return type_map.get(python_type, 'text')
    
    def _infer_label(self, field_name: str) -> str:
        """Generiert Label aus Feldname (snake_case → Title Case)"""
        return field_name.replace('_', ' ').title()
    
    def _is_required(self, field_name: str) -> bool:
        """Prüft ob Feld required ist (nicht Optional)"""
        field_type = self.type_hints.get(field_name)
        if not field_type:
            return True
        
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            return type(None) not in args
        
        return True
    
    def extract_input_fields(self) -> List[Dict]:
        """
        Extrahiert Input-Felder aus Dataclass mit Metadaten
        
        Returns:
            Liste von Field-Definitionen
        """
        fields_list = []
        
        for field_obj in fields(self.input_dataclass):
            field_name = field_obj.name
            metadata = field_obj.metadata or {}
            
            # Auto-Ableitung mit Metadata-Override
            field_def = {
                'id': field_name,
                'field_type': 'input',
                'label': metadata.get('ui_label') or self._infer_label(field_name),
                'type': metadata.get('ui_type') or self._infer_ui_type(field_obj.type),
                'required': metadata.get('ui_required', self._is_required(field_name)),
                'hint': metadata.get('ui_hint'),
                'placeholder': metadata.get('ui_placeholder'),
                'group': metadata.get('ui_group', 'default'),
                'order': metadata.get('ui_order', 0),
                'validation': metadata.get('ui_validation', []),
                'min_value': metadata.get('ui_min'),
                'max_value': metadata.get('ui_max'),
                'depends_on': metadata.get('ui_depends_on'),
                'show_when': metadata.get('ui_show_when'),
                'options': metadata.get('ui_options'),
                'width': metadata.get('ui_width', 'full'),
                'css_class': metadata.get('ui_class')
            }
            
            # Cleanup None values
            field_def = {k: v for k, v in field_def.items() if v is not None}
            
            # Ensure validation is always a list
            if 'validation' not in field_def:
                field_def['validation'] = []
            elif not isinstance(field_def['validation'], list):
                field_def['validation'] = [field_def['validation']]
            
            fields_list.append(field_def)
        
        # Sortiere nach group und order
        fields_list.sort(key=lambda f: (f['group'], f.get('order', 0)))
        
        return fields_list
    
    def extract_calculated_fields(self) -> List[Dict]:
        """
        Extrahiert berechnete Felder aus Registry
        
        Returns:
            Liste von Calculated Field Definitionen
        """
        calc_fields = []
        
        for key, meta in CalculatedFieldRegistry.get_all().items():
            calc_fields.append({
                'id': key,
                'field_type': 'calculated',
                'label': meta['label'],
                'formel': meta['formel'],
                'requires': meta['requires'],
                'einheit': meta['einheit'],
                'editable': meta['editable'],
                'needs_confirmation': meta['needs_confirmation'],
                'confirmation_threshold': meta['confirmation_threshold'],
                'group': meta['group'],
                'hint': meta['hint'],
                'precision': meta['precision'],
                'function_name': meta['function_name']
            })
        
        return calc_fields
    
    def extract_workflow(self) -> Dict:
        """
        Extrahiert Workflow aus Registry
        
        Returns:
            Dictionary mit Workflow-Definition
        """
        steps = []
        
        for step_def in WorkflowStepRegistry.get_all():
            steps.append({
                'order': step_def['order'],
                'title': step_def['title'],
                'description': step_def['description'],
                'groups': step_def['groups'],
                'component_type': step_def['component_type'],
                'show_if': step_def['show_if'].__name__ if step_def.get('show_if') else None
            })
        
        return {'steps': steps}
    
    def _extract_validation_rules(self, fields_list: List[Dict]) -> Dict:
        """Extrahiert alle verwendeten Validierungsregeln"""
        rules = set()
        
        for field_def in fields_list:
            for rule in field_def.get('validation', []):
                rules.add(rule)
        
        return {
            'rules': list(rules),
            'implementations': {
                rule: f"ValidationRule.{rule}" for rule in rules
            }
        }
    
    def generate_complete_schema(self) -> Dict:
        """
        Generiert vollständiges Schema mit allem
        
        Returns:
            Vollständiges Schema-Dictionary
        """
        input_fields = self.extract_input_fields()
        calc_fields = self.extract_calculated_fields()
        workflow = self.extract_workflow()
        
        # Gruppiere Input Fields
        groups = {}
        for field_def in input_fields:
            group_name = field_def['group']
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(field_def)
        
        # Kombiniere alle Felder
        all_fields = input_fields + calc_fields
        
        # Config als Dict
        config_dict = {}
        if self.config:
            if hasattr(self.config, '__dict__'):
                config_dict = {
                    k: v.isoformat() if isinstance(v, date) else v
                    for k, v in self.config.__dict__.items()
                }
        
        schema = {
            'meta': {
                'title': self.input_dataclass.__doc__ or self.input_dataclass.__name__,
                'class_name': self.input_dataclass.__name__,
                'generated_at': datetime.now().isoformat()
            },
            'config': config_dict,
            'input_fields': input_fields,
            'calculated_fields': calc_fields,
            'all_fields': all_fields,
            'groups': groups,
            'workflow': workflow,
            'validation_rules': self._extract_validation_rules(input_fields)
        }
        
        return schema
    
    def generate_typescript_interface(self, schema: Dict = None) -> str:
        """
        Generiert TypeScript Interface
        
        Returns:
            TypeScript Code als String
        """
        if schema is None:
            schema = self.generate_complete_schema()
        
        type_map = {
            'text': 'string',
            'number': 'number',
            'date': 'string',  # ISO date string
            'checkbox': 'boolean',
            'select': 'string'
        }
        
        interface = f'''/**
 * Auto-generiert aus Python Dataclass: {schema['meta']['class_name']}
 * Generated: {schema['meta']['generated_at']}
 */
export interface {schema['meta']['class_name']}Data {{
'''
        
        # Input Fields
        for field_def in schema['input_fields']:
            ts_type = type_map.get(field_def['type'], 'string')
            optional = '?' if not field_def.get('required', True) else ''
            
            if field_def.get('hint'):
                interface += f"  /** {field_def['hint']} */\n"
            
            interface += f"  {field_def['id']}{optional}: {ts_type};\n"
        
        interface += '}\n\n'
        
        # Calculated Fields Interface
        if schema['calculated_fields']:
            interface += f'''export interface {schema['meta']['class_name']}Calculated {{
'''
            for calc_field in schema['calculated_fields']:
                interface += f"  {calc_field['id']}?: number;  // {calc_field['label']}\n"
            
            interface += '}\n'
        
        return interface
    
    def generate_react_form(self, schema: Dict = None) -> str:
        """
        Generiert einfache React Form Component
        
        Returns:
            React/JSX Code als String
        """
        if schema is None:
            schema = self.generate_complete_schema()
        
        component = f'''import React from 'react';

/**
 * Auto-generiert aus Python Dataclass
 * {schema['meta']['title']}
 * Generated: {schema['meta']['generated_at']}
 */
export default function {schema['meta']['class_name']}Form({{ data, onChange }}) {{
  const handleChange = (fieldId, value) => {{
    onChange({{ ...data, [fieldId]: value }});
  }};

  return (
    <div className="space-y-6">
'''
        
        # Gruppen-Labels
        group_labels = {
            'identifikation': 'Identifikation',
            'stammdaten': 'Stammdaten',
            'gehalt': 'Gehaltsdaten',
            'berechnungen': 'Berechnete Werte',
            'default': 'Weitere Angaben'
        }
        
        # Generiere pro Gruppe
        for group_name, group_fields in schema['groups'].items():
            group_label = group_labels.get(group_name, group_name.title())
            
            component += f'''
      {{/* Gruppe: {group_label} */}}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">{group_label}</h3>
        <div className="space-y-4">
'''
            
            for field_def in group_fields:
                field_id = field_def['id']
                label = field_def['label']
                required_mark = ' *' if field_def.get('required', False) else ''
                hint = field_def.get('hint')
                field_type = field_def['type']
                
                # Conditional rendering
                if field_def.get('depends_on'):
                    component += f'''
          {{data.{field_def['depends_on']} && (
'''
                
                component += f'''
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {label}{required_mark}
            </label>
'''
                
                # Input field based on type
                if field_type == 'date':
                    component += f'''
            <input
              type="date"
              value={{data.{field_id} || ''}}
              onChange={{(e) => handleChange('{field_id}', e.target.value)}}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
'''
                elif field_type == 'number':
                    component += f'''
            <input
              type="number"
              step="0.01"
              value={{data.{field_id} || ''}}
              onChange={{(e) => handleChange('{field_id}', parseFloat(e.target.value) || '')}}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
'''
                elif field_type == 'select' and field_def.get('options'):
                    component += f'''
            <select
              value={{data.{field_id} || ''}}
              onChange={{(e) => handleChange('{field_id}', e.target.value)}}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Bitte wählen...</option>
'''
                    for value, label in field_def['options']:
                        component += f'''              <option value="{value}">{label}</option>\n'''
                    
                    component += '''            </select>
'''
                else:  # text
                    placeholder = field_def.get('placeholder', '')
                    component += f'''
            <input
              type="text"
              value={{data.{field_id} || ''}}
              onChange={{(e) => handleChange('{field_id}', e.target.value)}}
              placeholder="{placeholder}"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
'''
                
                if hint:
                    component += f'''
            <p className="text-xs text-gray-500 mt-1">{hint}</p>
'''
                
                component += '''
          </div>
'''
                
                # Close conditional
                if field_def.get('depends_on'):
                    component += '''
          )}
'''
            
            component += '''
        </div>
      </div>
'''
        
        component += '''
    </div>
  );
}
'''
        
        return component
    
    def save_all(self, output_dir: str = '/mnt/user-data/outputs') -> Dict[str, Path]:
        """
        Speichert alle generierten Dateien
        
        Args:
            output_dir: Output-Verzeichnis
        
        Returns:
            Dictionary mit Pfaden zu generierten Dateien
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generiere Schema
        schema = self.generate_complete_schema()
        
        # 1. Complete Schema (JSON)
        schema_file = output_path / 'complete_schema.json'
        schema_file.write_text(
            json.dumps(schema, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        # 2. React Component
        react_code = self.generate_react_form(schema)
        react_file = output_path / f'{schema["meta"]["class_name"]}Form.jsx'
        react_file.write_text(react_code, encoding='utf-8')
        
        # 3. TypeScript Interface
        ts_code = self.generate_typescript_interface(schema)
        ts_file = output_path / f'{schema["meta"]["class_name"]}.ts'
        ts_file.write_text(ts_code, encoding='utf-8')
        
        # 4. README
        readme = self._generate_readme(schema)
        readme_file = output_path / 'README_GENERATED.md'
        readme_file.write_text(readme, encoding='utf-8')
        
        return {
            'schema': schema_file,
            'react': react_file,
            'typescript': ts_file,
            'readme': readme_file
        }
    
    def _generate_readme(self, schema: Dict) -> str:
        """Generiert README für die generierten Dateien"""
        readme = f"""# Auto-Generated Forms

**Generiert:** {schema['meta']['generated_at']}
**Quelle:** {schema['meta']['class_name']} Python Dataclass

## Dateien

- `complete_schema.json` - Vollständiges Schema mit allen Metadaten
- `{schema['meta']['class_name']}Form.jsx` - React Form Component
- `{schema['meta']['class_name']}.ts` - TypeScript Interfaces

## Schema-Struktur

### Input Fields ({len(schema['input_fields'])})

"""
        
        for field in schema['input_fields']:
            readme += f"- **{field['label']}** (`{field['id']}`): {field['type']}"
            if field.get('required'):
                readme += " *required*"
            if field.get('hint'):
                readme += f"\n  - {field['hint']}"
            readme += "\n"
        
        if schema['calculated_fields']:
            readme += f"\n### Calculated Fields ({len(schema['calculated_fields'])})\n\n"
            for calc in schema['calculated_fields']:
                readme += f"- **{calc['label']}** (`{calc['id']}`)\n"
                readme += f"  - Formel: `{calc['formel']}`\n"
                readme += f"  - Benötigt: {', '.join(calc['requires'])}\n"
        
        if schema['workflow']['steps']:
            readme += f"\n### Workflow ({len(schema['workflow']['steps'])} Schritte)\n\n"
            for step in schema['workflow']['steps']:
                readme += f"{step['order']}. **{step['title']}**"
                if step.get('description'):
                    readme += f" - {step['description']}"
                readme += "\n"
        
        readme += """
## Verwendung

```jsx
import MitarbeiterFormularForm from './MitarbeiterFormularForm';

function App() {
  const [data, setData] = useState({});
  
  return (
    <MitarbeiterFormularForm
      data={data}
      onChange={setData}
    />
  );
}
```

## Schema verwenden

```javascript
import schema from './complete_schema.json';

// Zugriff auf Metadaten
console.log(schema.input_fields);
console.log(schema.calculated_fields);
console.log(schema.workflow);
```
"""
        
        return readme
