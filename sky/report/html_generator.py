"""HTML Report Generator for SKY Synthesis Agent

Generates professional HTML reports from synthesis search results.
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class SynthesisReportData:
    """Data structure for synthesis report generation"""
    material_formula: str
    material_formula_html: str = ""
    analysis: Dict[str, Any] = field(default_factory=dict)
    synthesis_methods: List[Dict[str, Any]] = field(default_factory=list)
    recommended_procedure: Dict[str, Any] = field(default_factory=dict)
    critical_parameters: List[str] = field(default_factory=list)
    safety_considerations: List[str] = field(default_factory=list)
    alternative_routes: List[Dict[str, Any]] = field(default_factory=list)
    related_materials: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    search_depth: int = 0
    recipes_found: int = 0
    generation_date: str = ""
    raw_output: str = ""


class HTMLReportGenerator:
    """Generates HTML synthesis reports from agent output"""
    
    def __init__(self, template_path: Optional[Path] = None):
        """Initialize with optional custom template"""
        self.template_path = template_path or Path(__file__).parent / "template.html"
        
    def parse_agent_output(self, raw_output: str) -> SynthesisReportData:
        """Parse raw SKY agent output into structured report data"""
        data = SynthesisReportData(
            material_formula="",
            generation_date=datetime.now().strftime("%d %b %Y"),
            raw_output=raw_output
        )
        
        # Extract material formula - look for various patterns
        formula_patterns = [
            r"Formula:\s*([A-Za-z0-9₀-₉()]+)",  # Unicode subscripts
            r"Formula:\s*([A-Z][a-zA-Z0-9()]+(?:\s*[A-Z][a-zA-Z0-9()]+)*)",
            r"Target Material Analysis.*?([A-Z][a-z]?\d*[A-Z][a-z]?\d*[A-Z]?[a-z]?\d*)",
            r"for\s+([A-Z][a-z]?\d*[A-Z][a-z]?\d*[A-Z]?[a-z]?\d*)",
        ]
        
        for pattern in formula_patterns:
            formula_match = re.search(pattern, raw_output)
            if formula_match:
                formula = formula_match.group(1).strip()
                # Convert unicode subscripts to normal numbers
                formula = formula.replace('₀', '0').replace('₁', '1').replace('₂', '2')
                formula = formula.replace('₃', '3').replace('₄', '4').replace('₅', '5')
                formula = formula.replace('₆', '6').replace('₇', '7').replace('₈', '8').replace('₉', '9')
                data.material_formula = formula
                data.material_formula_html = self._formula_to_html(formula)
                break
        
        # Extract key properties from bullet points in analysis section
        analysis_section = re.search(r"Target Material Analysis(.*?)(?:🔬|Synthesis|$)", raw_output, re.DOTALL)
        if analysis_section:
            analysis_text = analysis_section.group(1)
            
            # Extract structure/prototype info
            structure_match = re.search(r"Prototype/Structure:\s*([^•\n]+(?:\n[^•\n]+)*)", analysis_text)
            if structure_match:
                data.analysis["structure"] = structure_match.group(1).strip()
            
            # Extract thermodynamic stability
            stability_match = re.search(r"Thermodynamic stability:\s*([^•\n]+(?:\n[^•\n]+)*)", analysis_text)
            if stability_match:
                data.analysis["thermodynamic_stability"] = stability_match.group(1).strip()
            
            # Look for density mentions
            density_match = re.search(r"density[^0-9]*([0-9.,–\-\s]+g[^;]*)", analysis_text, re.IGNORECASE)
            if density_match:
                data.analysis["density"] = density_match.group(1).strip()
            
            # Look for band gap
            bandgap_match = re.search(r"(\d+[–\-]?\d*\.?\d*\s*eV[^)]*)", analysis_text)
            if bandgap_match:
                data.analysis["band_gap"] = bandgap_match.group(1).strip()
        
        # Extract synthesis methods - improved parsing
        methods = []
        
        # Look for synthesis methods section - broader search
        method_section = re.search(r"(🔬.*?)(?:🧪|📝|Critical|Safety|Alternative|$)", raw_output, re.DOTALL)
        if method_section:
            method_text = method_section.group(1)
            
            # Find numbered methods - use the pattern that worked in debug
            pattern = r"(\d+)\s+([^:\n]+):\s*\n((?:[^0-9][^\n]*\n?)+?)(?=\d+\s+\w+|🧪|📝|$)"
            method_blocks = re.findall(pattern, method_text, re.MULTILINE | re.DOTALL)
            
            for num, name, content in method_blocks:
                method = {
                    "name": name.strip().rstrip(':'),
                    "details": []
                }
                
                # Extract bullet points - look for lines starting with dash/bullet
                lines = content.split('\n')
                current_bullet = ""
                
                for line in lines:
                    line = line.strip()
                    if line.startswith(('–', '•', '·', '-')) and len(line) > 2:
                        # Save previous bullet if exists
                        if current_bullet:
                            method["details"].append(current_bullet.strip())
                        # Start new bullet
                        current_bullet = line[1:].strip()  # Remove bullet marker
                    elif line and current_bullet:
                        # Continue previous bullet
                        current_bullet += " " + line
                
                # Add the last bullet
                if current_bullet:
                    method["details"].append(current_bullet.strip())
                
                if method["details"]:  # Only add if we found details
                    methods.append(method)
        
        data.synthesis_methods = methods
        
        # Extract recommended procedure
        if "Recommended Procedure" in raw_output:
            proc_match = re.search(r"Recommended Procedure[^:]*:(.*?)(?:Critical parameters|Safety|Alternative|$)", raw_output, re.DOTALL)
            if proc_match:
                proc_text = proc_match.group(1)
                steps = re.findall(r"(\d+)\s*([^0-9]+?)(?=\d+\s+\w+|$)", proc_text)
                data.recommended_procedure = {
                    "steps": [{"number": num, "description": desc.strip()} for num, desc in steps]
                }
        
        # Extract critical parameters - improved parsing
        if "Critical parameters" in raw_output or "critical" in raw_output.lower():
            crit_match = re.search(r"Critical parameters[^:]*:(.*?)(?:Yield|Safety|📝|Alternative|$)", raw_output, re.DOTALL | re.IGNORECASE)
            if crit_match:
                crit_text = crit_match.group(1)
                # Extract lines starting with bullet or dash
                bullets = re.findall(r"[•·–-]\s*([^\n•·–]+)", crit_text)
                data.critical_parameters = [b.strip() for b in bullets if b.strip()]
        
        # Extract safety considerations - improved parsing  
        if "Safety" in raw_output:
            safety_match = re.search(r"Safety[^:]*:(.*?)(?:📝|Alternative|Pros|Selection|$)", raw_output, re.DOTALL | re.IGNORECASE)
            if safety_match:
                safety_text = safety_match.group(1)
                bullets = re.findall(r"[•·–-]\s*([^\n•·–]+)", safety_text)
                data.safety_considerations = [b.strip() for b in bullets if b.strip()]
        
        # Extract alternative routes
        if "Alternative" in raw_output:
            alt_match = re.search(r"Alternative[^:]*:(.*?)(?:Selection|Pros|By adhering|$)", raw_output, re.DOTALL)
            if alt_match:
                alt_text = alt_match.group(1)
                alt_methods = re.findall(r"(\d+)\s+([\w\s\-–]+)\s*\n\s*Pros:(.*?)\s*Cons:(.*?)(?=\d+\s+\w+|$)", alt_text, re.DOTALL)
                for num, name, pros, cons in alt_methods:
                    data.alternative_routes.append({
                        "name": name.strip(),
                        "pros": pros.strip(),
                        "cons": cons.strip()
                    })
        
        # Extract related materials - look for specific mentions
        related = []
        
        # Look for explicit material mentions in the analysis
        material_patterns = [
            r"(Na[A-Za-z]*[0-9]*O[0-9]*)",  # Sodium compounds
            r"(Li[A-Za-z]*[0-9]*O[0-9]*)",   # Lithium compounds
            r"([A-Z][a-z]?Fe[0-9]*O[0-9]*)", # Iron oxides
            r"(Fe[0-9]*O[0-9]*)",           # Simple iron oxides
        ]
        
        for pattern in material_patterns:
            matches = re.findall(pattern, raw_output)
            related.extend(matches)
        
        # Look for materials specifically mentioned as "closest" or "similar"
        closest_match = re.search(r"closest[^:]*include\s*([^.]+)", raw_output, re.IGNORECASE)
        if closest_match:
            closest_materials = re.findall(r"([A-Z][a-zA-Z0-9₀-₉]*)", closest_match.group(1))
            related.extend(closest_materials)
        
        # Clean up and convert unicode subscripts
        cleaned_related = []
        for material in set(related):  # Remove duplicates
            if len(material) > 2:  # Filter out single letters
                # Convert unicode subscripts
                clean_mat = material.replace('₀', '0').replace('₁', '1').replace('₂', '2')
                clean_mat = clean_mat.replace('₃', '3').replace('₄', '4').replace('₅', '5')
                clean_mat = clean_mat.replace('₆', '6').replace('₇', '7').replace('₈', '8').replace('₉', '9')
                cleaned_related.append(clean_mat)
        
        data.related_materials = list(set(cleaned_related))[:8]  # Unique, limit to 8
        
        return data
    
    def _formula_to_html(self, formula: str) -> str:
        """Convert chemical formula to HTML with subscripts"""
        # Handle parentheses first
        formula = re.sub(r'\(([^)]+)\)', r'(\1)', formula)
        # Convert numbers to subscripts
        formula = re.sub(r'(\d+)', r'<sub>\1</sub>', formula)
        # Handle special cases like charges
        formula = re.sub(r'\^([\+\-]?\d*)', r'<sup>\1</sup>', formula)
        return formula
    
    def generate_html(self, data: SynthesisReportData) -> str:
        """Generate HTML report from structured data"""
        template = self._get_template()
        
        # Build HTML sections
        html = template
        
        # Replace placeholders
        html = html.replace("{{MATERIAL_NAME}}", data.material_formula_html or data.material_formula)
        html = html.replace("{{DATE}}", data.generation_date)
        html = html.replace("{{FORMULA_HTML}}", data.material_formula_html)
        
        # Build analysis section
        analysis_html = ""
        if data.analysis.get("crystal_system"):
            analysis_html += f'<div class="kv"><div class="k">Crystal System</div><div class="v">{data.analysis["crystal_system"]}</div></div>'
        if data.analysis.get("density"):
            analysis_html += f'<div class="kv"><div class="k">Density</div><div class="v">{self._format_units(data.analysis["density"])}</div></div>'
        if data.analysis.get("formation_energy"):
            analysis_html += f'<div class="kv"><div class="k">Formation Energy</div><div class="v">{self._format_units(data.analysis["formation_energy"])}</div></div>'
        if data.analysis.get("band_gap"):
            analysis_html += f'<div class="kv"><div class="k">Band Gap</div><div class="v">{data.analysis["band_gap"]}</div></div>'
        
        html = html.replace("{{ANALYSIS_PROPERTIES}}", analysis_html)
        
        # Build synthesis methods section
        methods_html = ""
        for i, method in enumerate(data.synthesis_methods, 1):
            methods_html += f'<div class="num"><span class="dot">{i}</span>{method["name"]}</div><ul class="list-tight">'
            for detail in method["details"]:
                methods_html += f'<li>{self._format_chemistry(detail)}</li>'
            methods_html += '</ul>'
        
        html = html.replace("{{SYNTHESIS_METHODS}}", methods_html or "<p>No direct synthesis methods found. Using analogous routes.</p>")
        
        # Build recommended procedure
        procedure_html = ""
        if data.recommended_procedure.get("steps"):
            for step in data.recommended_procedure["steps"]:
                procedure_html += f'''
                <div class="num">
                    <span class="dot">{step["number"]}</span>
                    {self._format_chemistry(step["description"])}
                </div>'''
        
        html = html.replace("{{PROCEDURE_STEPS}}", procedure_html or "<p>See synthesis methods above for recommended procedures.</p>")
        
        # Build critical parameters
        params_html = "<ul class='list-tight'>"
        for param in data.critical_parameters:
            params_html += f"<li>{self._format_chemistry(param)}</li>"
        params_html += "</ul>"
        
        html = html.replace("{{CRITICAL_PARAMS}}", params_html if data.critical_parameters else "<p>Standard solid-state synthesis parameters apply.</p>")
        
        # Build safety section
        safety_html = "<ul class='list-tight'>"
        for item in data.safety_considerations:
            safety_html += f"<li>{item}</li>"
        safety_html += "</ul>"
        
        html = html.replace("{{SAFETY_ITEMS}}", safety_html if data.safety_considerations else "<p>Standard laboratory safety procedures apply.</p>")
        
        # Build alternative routes
        alt_html = ""
        for i, route in enumerate(data.alternative_routes, 1):
            alt_html += f'''
            <div class="card">
                <h3>{i}. {route["name"]}</h3>
                <div class="kvs">
                    <div class="kv"><div class="k">Pros</div><div class="v">{route["pros"]}</div></div>
                    <div class="kv"><div class="k">Cons</div><div class="v">{route["cons"]}</div></div>
                </div>
            </div>'''
        
        html = html.replace("{{ALTERNATIVE_ROUTES}}", alt_html or "<p>See synthesis methods section for alternative approaches.</p>")
        
        # Build related materials chips
        chips_html = ""
        for material in data.related_materials[:8]:
            chips_html += f'<span class="chip">{self._formula_to_html(material)}</span>'
        
        html = html.replace("{{RELATED_MATERIALS}}", chips_html)
        
        # Add search metadata
        if data.confidence_score > 0:
            confidence_badge = "ok" if data.confidence_score > 0.8 else "warn" if data.confidence_score > 0.5 else "info"
            confidence_html = f'<span class="badge {confidence_badge}">Confidence: {data.confidence_score:.1%}</span>'
        else:
            confidence_html = ""
        
        html = html.replace("{{CONFIDENCE_BADGE}}", confidence_html)
        
        return html
    
    def _format_chemistry(self, text: str) -> str:
        """Format chemical text with proper subscripts/superscripts"""
        # Format temperatures
        text = re.sub(r'(\d+)\s*°C', r'\1 °C', text)
        # Format chemical formulas
        text = re.sub(r'\b([A-Z][a-z]?)(\d+)', r'\1<sub>\2</sub>', text)
        # Format units
        text = self._format_units(text)
        return text
    
    def _format_units(self, text: str) -> str:
        """Format scientific units with proper HTML"""
        text = re.sub(r'cm-3', r'cm<sup>−3</sup>', text)
        text = re.sub(r'g/cm3', r'g·cm<sup>−3</sup>', text)
        text = re.sub(r'atom-1', r'atom<sup>−1</sup>', text)
        text = re.sub(r'eV/atom', r'eV·atom<sup>−1</sup>', text)
        text = re.sub(r'min-1', r'min<sup>−1</sup>', text)
        text = re.sub(r'h-1', r'h<sup>−1</sup>', text)
        text = re.sub(r'L/min', r'L·min<sup>−1</sup>', text)
        return text
    
    def _get_template(self) -> str:
        """Get HTML template"""
        if self.template_path.exists():
            return self.template_path.read_text()
        
        # Default template
        return '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{MATERIAL_NAME}} — Synthesis Report</title>
  <style>
    :root{
      --bg:#0b1220;
      --ink:#0f172a;
      --ink-2:#1f2937;
      --muted:#6b7280;
      --fg:#0b1220;
      --card:#ffffff;
      --brand:#06b6d4;
      --brand-2:#22c55e;
      --accent:#6366f1;
      --warn:#f59e0b;
      --danger:#ef4444;
    }
    *{box-sizing:border-box}
    html,body{margin:0;padding:0;background:#f6f7fb;color:#0b1220;font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;}
    .hero{background:linear-gradient(135deg,#0ea5e9, #22c55e 70%); color:#fff; padding:42px 24px; position:sticky; top:0; z-index:5; box-shadow:0 6px 20px rgba(0,0,0,.15)}
    .hero .title{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
    .pill{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.18);backdrop-filter:saturate(150%) blur(2px);border:1px solid rgba(255,255,255,.28);font-weight:600}
    .container{max-width:1100px;margin:24px auto;padding:0 16px 64px}
    nav.toc{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 24px}
    nav.toc a{padding:8px 10px;border-radius:999px;background:#fff;border:1px solid #e5e7eb;text-decoration:none;color:#111827;font-size:14px}
    nav.toc a:hover{border-color:#cbd5e1}
    .grid{display:grid;gap:16px}
    @media(min-width:900px){.grid.cols-2{grid-template-columns:1fr 1fr}}
    .card{background:#fff;border:1px solid #e5e7eb;border-radius:16px; padding:18px 18px 16px; box-shadow:0 2px 8px rgba(2,6,23,.05)}
    h2{margin:6px 0 10px;font-size:22px}
    h3{margin:14px 0 8px;font-size:18px}
    p{line-height:1.55}
    .kvs{display:grid;grid-template-columns:180px 1fr;gap:8px; row-gap:10px}
    .kv{display:contents}
    .k{color:#374151}
    .v{font-weight:600}
    .chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
    .chip{background:#f1f5f9;border:1px solid #e2e8f0;color:#0f172a;padding:4px 8px;border-radius:999px;font-size:13px}
    .badge{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:700;padding:4px 8px;border-radius:8px;border:1px solid #e5e7eb;background:#fff}
    .badge.ok{color:#16a34a;border-color:#bbf7d0;background:#f0fdf4}
    .badge.warn{color:#b45309;border-color:#fde68a;background:#fffbeb}
    .badge.info{color:#0369a1;border-color:#bae6fd;background:#f0f9ff}
    .list-tight li{margin:6px 0}
    .num{display:flex;align-items:center;gap:10px;margin:10px 0 6px;font-weight:800}
    .num .dot{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:999px;background:#111827;color:#fff;font-size:13px}
    .callout{border-left:4px solid var(--accent); background:#eef2ff; padding:10px 12px;border-radius:10px}
    .muted{color:#6b7280}
    .toolbar{display:flex;gap:10px;margin-top:10px}
    .btn{border:1px solid #e5e7eb;background:#fff;border-radius:10px;padding:8px 10px;cursor:pointer}
    .btn:hover{background:#f8fafc}
    code,kbd{font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace}
    .two-col{columns:2; column-gap:20px}
    @media(max-width:800px){.two-col{columns:1}}
    .footer{margin-top:26px;color:#6b7280;font-size:13px;text-align:center}
    @media print { nav.toc, .toolbar { display:none } }
  </style>
</head>
<body>
  <header class="hero">
    <div class="title">
      <div style="font-size:28px;font-weight:900;letter-spacing:.2px">Synthesis Report: <span style="opacity:.95">{{MATERIAL_NAME}}</span></div>
      <span class="pill">📅 {{DATE}}</span>
      <span class="pill">🧪 SKY Agent Analysis</span>
      {{CONFIDENCE_BADGE}}
    </div>
    <div class="toolbar">
      <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
      <button class="btn" onclick="window.scrollTo({top:0,behavior:'smooth'})">⬆️ Back to Top</button>
    </div>
  </header>

  <div class="container">
    <nav class="toc">
      <a href="#overview">Overview</a>
      <a href="#methods">Synthesis Methods</a>
      <a href="#procedure">Recommended Procedure</a>
      <a href="#critical">Critical Parameters</a>
      <a href="#safety">Safety</a>
      <a href="#alternatives">Alternative Routes</a>
    </nav>

    <section id="overview" class="card">
      <h2>📊 Target Material Analysis</h2>
      <div class="kvs">
        <div class="kv"><div class="k">Formula</div><div class="v">{{FORMULA_HTML}}</div></div>
        {{ANALYSIS_PROPERTIES}}
      </div>
      <div class="chips">{{RELATED_MATERIALS}}</div>
    </section>

    <section id="methods" class="card">
      <h2>🔬 Synthesis Methods</h2>
      {{SYNTHESIS_METHODS}}
    </section>

    <section id="procedure" class="card">
      <h2>🧪 Recommended Procedure</h2>
      {{PROCEDURE_STEPS}}
    </section>

    <section id="critical" class="card">
      <h2>⚙️ Critical Parameters</h2>
      {{CRITICAL_PARAMS}}
    </section>

    <section id="safety" class="card">
      <h2>⚠️ Safety Considerations</h2>
      {{SAFETY_ITEMS}}
    </section>

    <section id="alternatives" class="grid cols-2">
      <h2 style="grid-column:1/-1">📝 Alternative Routes</h2>
      {{ALTERNATIVE_ROUTES}}
    </section>

    <div class="footer">
      Generated by SKY (Synthesis Knowledge Yield) Agent • Powered by Materials Project
    </div>
  </div>
</body>
</html>'''
    
    def save_report(self, data: SynthesisReportData, output_path: Path) -> Path:
        """Generate and save HTML report to file"""
        html = self.generate_html(data)
        output_path = Path(output_path)
        output_path.write_text(html, encoding='utf-8')
        return output_path
    
    def from_agent_output(self, raw_output: str, output_path: Optional[Path] = None) -> Path:
        """Convenience method to generate report directly from agent output"""
        data = self.parse_agent_output(raw_output)
        
        if output_path is None:
            # Default filename based on material formula
            safe_name = re.sub(r'[^\w\s-]', '', data.material_formula)
            output_path = Path(f"{safe_name}_synthesis_report.html")
        
        return self.save_report(data, output_path)