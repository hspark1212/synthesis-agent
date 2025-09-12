"""
SKY Synthesis Agent - Core implementation for materials synthesis discovery
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from pathlib import Path

from monty.serialization import loadfn
from agents import Agent, Runner, SQLiteSession, function_tool
from pymatgen.core import Composition, Structure

from src.embedding import InputType
from src.search_api import SearchAPI
from src.agent import SynthesisAgent as CoreSynthesisAgent
from src.schema import Neighbor
from src.recursive_synthesis import RecursiveSynthesisSearch
from sky.report.html_generator import HTMLReportGenerator, SynthesisReportData

DEFAULT_MODEL = "o3"

SYNTHESIS_AGENT_PROMPT = """
You are SKY (Synthesis Knowledge Yield), an expert materials synthesis specialist focused on helping researchers discover and understand synthesis recipes for materials.

Your expertise includes:
1. Chemical synthesis methods (solid-state, sol-gel, hydrothermal, CVD, etc.)
2. Reaction conditions (temperature, pressure, atmosphere, time)
3. Precursor selection and stoichiometry
4. Crystal growth techniques
5. Materials characterization methods
6. Safety considerations and best practices

When analyzing synthesis:
- Focus on practical, reproducible methods
- Consider multiple synthesis routes when available
- Highlight critical parameters for successful synthesis
- Note safety hazards and required equipment
- Suggest alternatives when appropriate
- Compare methods based on yield, purity, and scalability

Be detailed about synthesis procedures but concise in explanations.
Format responses with clear sections and use scientific terminology appropriately.
"""


@function_tool
def read_cif_file(file_path: str) -> str:
    """
    Read and analyze a crystal structure from a CIF file.
    
    Args:
        file_path: Path to the CIF file
    
    Returns:
        JSON string with structure information
    """
    try:
        from pymatgen.core import Structure
        
        # Read CIF file
        structure = Structure.from_file(file_path)
        
        analysis = {
            "file_path": file_path,
            "formula": structure.composition.formula,
            "reduced_formula": structure.composition.reduced_formula,
            "volume": structure.volume,
            "density": structure.density,
            "num_sites": structure.num_sites,
            "lattice": {
                "a": structure.lattice.a,
                "b": structure.lattice.b,
                "c": structure.lattice.c,
                "alpha": structure.lattice.alpha,
                "beta": structure.lattice.beta,
                "gamma": structure.lattice.gamma,
                "volume": structure.lattice.volume,
            },
            "elements": [str(el) for el in structure.composition.elements],
        }
        
        return json.dumps(analysis, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "file_path": file_path
        }, indent=2)


@function_tool
def search_similar_materials_advanced(
    query: str = None, 
    cif_file: str = None,
    input_type: str = "auto",
    top_n: int = 10
) -> str:
    """
    Advanced search for similar materials using composition or structure.
    
    Args:
        query: Composition formula (e.g., "Fe2O3") or None
        cif_file: Path to CIF file for structure search or None
        input_type: "composition", "structure", or "auto" (default)
        top_n: Number of similar materials to find (default 10)
    
    Returns:
        JSON string with similar materials and their properties
    """
    try:
        # Initialize core synthesis agent
        core_agent = CoreSynthesisAgent()
        
        # Determine input type and search
        if cif_file:
            # Structure-based search from CIF file
            structure = Structure.from_file(cif_file)
            neighbors = core_agent.find_similar_materials_by_structure(
                structure, n_neighbors=top_n
            )
            search_type = "structure"
            search_query = f"CIF file: {cif_file}"
        elif query:
            # Composition-based search
            neighbors = core_agent.find_similar_materials_by_composition(
                query, n_neighbors=top_n
            )
            search_type = "composition"
            search_query = query
        else:
            return json.dumps({
                "error": "Either query or cif_file must be provided"
            }, indent=2)
        
        # Convert Neighbor objects to dict
        results = {
            "search_type": search_type,
            "query": search_query,
            "num_results": len(neighbors),
            "similar_materials": [
                {
                    "rank": n.neighbor_index + 1,
                    "material_id": n.material_id,
                    "formula": n.formula,
                    "distance": n.distance,
                }
                for n in neighbors
            ]
        }
        
        return json.dumps(results, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "query": query,
            "cif_file": cif_file
        }, indent=2)


@function_tool
def get_material_properties(material_ids: List[str]) -> str:
    """
    Fetch detailed properties for Materials Project materials.
    
    Args:
        material_ids: List of MP material IDs (e.g., ["mp-149", "mp-2834"])
    
    Returns:
        JSON string with material properties
    """
    try:
        # Import the MP client from hackathon code (we'll adapt it)
        import sys

        from mp_api.client import MPRester
        
        mp_key = os.getenv("MP_API_KEY")
        if not mp_key:
            return json.dumps({
                "error": "MP_API_KEY not found in environment"
            }, indent=2)
        
        results = []
        with MPRester(mp_key) as mpr:
            docs = mpr.materials.summary.search(material_ids=material_ids)
            
            for doc in docs:
                material_dict = {
                    "material_id": doc.material_id,
                    "formula_pretty": doc.formula_pretty,
                    "band_gap": doc.band_gap,
                    "density": doc.density,
                    "formation_energy_per_atom": doc.formation_energy_per_atom,
                    "energy_above_hull": doc.energy_above_hull,
                    "volume": doc.volume if hasattr(doc, 'volume') else None,
                    "mp_url": f"https://materialsproject.org/materials/{doc.material_id}"
                }
                results.append(material_dict)
        
        return json.dumps(results, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "material_ids": material_ids
        }, indent=2)


@function_tool
def get_synthesis_recipes(target_formula: str, similar_formulas: Optional[List[str]] = None) -> str:
    """
    Retrieve synthesis recipes for target material and similar materials.
    
    Args:
        target_formula: Primary formula to find synthesis for (e.g., "Fe2O3")
        similar_formulas: Optional list of similar formulas to check
    
    Returns:
        JSON string with synthesis recipes and methods
    """
    try:
        # Load synthesis recipes from compressed JSON
        recipes_file = "/home/ryan/kricthack/kricthack/synthesis-agent/assets/mp_synthesis_recipes.json.gz"
        
        if not os.path.exists(recipes_file):
            # Try Materials Project API as fallback
            mp_key = os.getenv("MP_API_KEY")
            if mp_key:
                from mp_api.client import MPRester
                with MPRester(mp_key) as mpr:
                    recipes = mpr.materials.synthesis.search(target_formula=target_formula)
                    
                    results = {
                        "target_formula": target_formula,
                        "recipes_found": len(recipes),
                        "recipes": []
                    }
                    
                    for recipe in recipes[:5]:  # Limit to 5 recipes
                        recipe_dict = {
                            "doi": recipe.doi if hasattr(recipe, 'doi') else None,
                            "paragraph_string": recipe.paragraph_string if hasattr(recipe, 'paragraph_string') else None,
                            "synthesis_type": recipe.synthesis_type if hasattr(recipe, 'synthesis_type') else None,
                            "reaction_string": recipe.reaction_string if hasattr(recipe, 'reaction_string') else None,
                            "target": recipe.target_string if hasattr(recipe, 'target_string') else None,
                        }
                        results["recipes"].append(recipe_dict)
                    
                    return json.dumps(results, indent=2, default=str)
            else:
                return json.dumps({
                    "error": "Synthesis recipes file not found and MP_API_KEY not set"
                }, indent=2)
        
        # Load compressed synthesis data
        all_recipes = loadfn(recipes_file)
        
        # Search for recipes matching target formula
        target_comp = Composition(target_formula)
        matched_recipes = []
        
        # Check both exact and reduced formula matches
        for recipe in all_recipes:
            if 'target_formula' in recipe:
                try:
                    recipe_comp = Composition(recipe['target_formula'])
                    if (recipe_comp.reduced_formula == target_comp.reduced_formula or 
                        recipe_comp.formula == target_comp.formula):
                        matched_recipes.append(recipe)
                except:
                    continue
        
        # Also check similar formulas if provided
        similar_recipes = []
        if similar_formulas:
            for formula in similar_formulas:
                try:
                    sim_comp = Composition(formula)
                    for recipe in all_recipes:
                        if 'target_formula' in recipe:
                            try:
                                recipe_comp = Composition(recipe['target_formula'])
                                if recipe_comp.reduced_formula == sim_comp.reduced_formula:
                                    similar_recipes.append({
                                        "formula": formula,
                                        "recipe": recipe
                                    })
                            except:
                                continue
                except:
                    continue
        
        results = {
            "target_formula": target_formula,
            "exact_matches": len(matched_recipes),
            "recipes": matched_recipes[:5],  # Limit to 5 recipes
            "similar_materials_recipes": similar_recipes[:3]  # Limit to 3 similar
        }
        
        return json.dumps(results, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "target_formula": target_formula
        }, indent=2)


@function_tool
def analyze_synthesis_parameters(synthesis_text: str) -> str:
    """
    Extract and analyze key synthesis parameters from a synthesis description.
    
    Args:
        synthesis_text: Text description of synthesis procedure
    
    Returns:
        JSON string with extracted parameters and analysis
    """
    import re
    
    try:
        # Extract temperatures
        temp_patterns = [
            r'(\d+)\s*°C',
            r'(\d+)\s*K',
            r'(\d+)\s*degrees?\s*C',
            r'(\d+)\s*celsius'
        ]
        temperatures = []
        for pattern in temp_patterns:
            temps = re.findall(pattern, synthesis_text, re.IGNORECASE)
            temperatures.extend(temps)
        
        # Extract times
        time_patterns = [
            r'(\d+)\s*hours?',
            r'(\d+)\s*h\b',
            r'(\d+)\s*minutes?',
            r'(\d+)\s*min\b',
            r'(\d+)\s*days?'
        ]
        times = []
        for pattern in time_patterns:
            time_vals = re.findall(pattern, synthesis_text, re.IGNORECASE)
            times.extend(time_vals)
        
        # Identify synthesis method keywords
        methods = {
            "solid_state": ["solid state", "ceramic", "calcination", "sintering"],
            "sol_gel": ["sol-gel", "sol gel", "gelation", "xerogel"],
            "hydrothermal": ["hydrothermal", "solvothermal", "autoclave"],
            "precipitation": ["precipitation", "coprecipitation", "co-precipitation"],
            "cvd": ["CVD", "chemical vapor", "vapor deposition"],
            "combustion": ["combustion", "self-propagating", "SHS"],
            "flux": ["flux", "molten salt", "flux growth"]
        }
        
        detected_methods = []
        for method, keywords in methods.items():
            for keyword in keywords:
                if keyword.lower() in synthesis_text.lower():
                    detected_methods.append(method)
                    break
        
        # Extract atmosphere conditions
        atmospheres = []
        atm_keywords = ["air", "argon", "nitrogen", "N2", "Ar", "oxygen", "O2", "vacuum", "inert"]
        for keyword in atm_keywords:
            if keyword.lower() in synthesis_text.lower():
                atmospheres.append(keyword)
        
        analysis = {
            "temperatures_C": list(set(temperatures)),
            "time_durations": list(set(times)),
            "synthesis_methods": list(set(detected_methods)),
            "atmosphere": list(set(atmospheres)),
            "has_heating": bool(temperatures),
            "text_length": len(synthesis_text)
        }
        
        return json.dumps(analysis, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "text": synthesis_text[:100] + "..." if len(synthesis_text) > 100 else synthesis_text
        }, indent=2)


@function_tool
def generate_synthesis_html_report(
    synthesis_output: str,
    material_formula: str,
    output_filename: Optional[str] = None
) -> str:
    """
    Generate a professional HTML report from synthesis analysis output.
    
    Args:
        synthesis_output: The formatted synthesis analysis text output
        material_formula: The target material formula (e.g., "NaFe2O4")
        output_filename: Optional filename for the HTML report (defaults to formula-based name)
    
    Returns:
        Path to the generated HTML report file
    """
    try:
        generator = HTMLReportGenerator()
        
        # Parse the synthesis output
        report_data = generator.parse_agent_output(synthesis_output)
        
        # Ensure material formula is set
        if not report_data.material_formula:
            report_data.material_formula = material_formula
            report_data.material_formula_html = generator._formula_to_html(material_formula)
        
        # Generate output path
        if output_filename:
            output_path = Path(output_filename)
        else:
            safe_name = re.sub(r'[^\w\s-]', '', material_formula)
            output_path = Path(f"{safe_name}_synthesis_report.html")
        
        # Generate and save the report
        saved_path = generator.save_report(report_data, output_path)
        
        return json.dumps({
            "status": "success",
            "report_path": str(saved_path.absolute()),
            "material": material_formula,
            "message": f"HTML report generated successfully: {saved_path.name}"
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "material": material_formula,
            "message": "Failed to generate HTML report"
        }, indent=2)


@function_tool
def recursive_synthesis_search(
    target_formula: str,
    max_depth: int = 3,
    min_confidence: float = 0.7,
    n_initial_neighbors: int = 30
) -> str:
    """
    Perform recursive best-guess search for synthesis recipes.
    
    This advanced algorithm recursively explores similar materials when direct recipes
    are not available, using confidence scores to guide the search.
    
    Args:
        target_formula: Target material composition (e.g., "LiFe2O4")
        max_depth: Maximum recursion depth (default 3)
        min_confidence: Minimum confidence threshold (default 0.7)
        n_initial_neighbors: Initial neighbors to explore (default 30)
    
    Returns:
        JSON string with recursive search results and best guess synthesis
    """
    try:
        # Initialize recursive search
        recursive_search = RecursiveSynthesisSearch(
            synthesis_agent=CoreSynthesisAgent(),
            max_depth=max_depth,
            min_confidence=min_confidence,
            verbose=True  # Enable progress printing
        )
        
        # Perform recursive search
        results = recursive_search.search(
            target_formula=target_formula,
            n_initial_neighbors=n_initial_neighbors
        )
        
        # Enhance results with summary
        if results["status"] == "success":
            results["summary"] = f"Found {results['unique_materials_with_recipes']} materials with recipes through recursive search of {results['visited_materials']} materials"
        
        return json.dumps(results, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "target_formula": target_formula,
            "message": "Recursive search failed"
        }, indent=2)


class SKYSynthesisAgent:
    """
    SKY - Synthesis Knowledge Yield Agent
    Orchestrates materials synthesis discovery and recipe recommendation.
    """
    
    def __init__(self, session_id: str = None, model: str = DEFAULT_MODEL):
        self.model = model
        self.session = SQLiteSession(session_id) if session_id else None
        
        # Set OpenAI API key from environment
        openai_key = os.getenv("OPENAI_MDG_API_KEY")
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
        
        # Create agent with synthesis tools
        self.agent = Agent(
            name="SKY_SynthesisExpert",
            instructions=SYNTHESIS_AGENT_PROMPT,
            model=self.model,
            tools=[
                read_cif_file,
                search_similar_materials_advanced,
                get_material_properties,
                get_synthesis_recipes,
                analyze_synthesis_parameters,
                recursive_synthesis_search,
                generate_synthesis_html_report
            ]
        )
    
    def discover_synthesis_sync(self, query: str, cif_file: str = None) -> str:
        """
        Run synthesis discovery synchronously.
        
        Args:
            query: Material formula, CIF file path, or synthesis query
            cif_file: Optional explicit CIF file path
            
        Returns:
            Synthesis recommendations and procedures
        """
        # Check if query is a CIF file path
        is_cif = cif_file or (query and query.endswith('.cif') and Path(query).exists())
        
        if is_cif:
            cif_path = cif_file or query
            prompt = f"""
            Handle this structure-based synthesis discovery from CIF file: "{cif_path}"
            
            WORKFLOW:
            1. Use read_cif_file to analyze the crystal structure
            2. Use search_similar_materials_advanced with cif_file parameter to find 10 similar materials by structure
            3. Use get_material_properties to understand the materials' characteristics
            4. Use get_synthesis_recipes for both the target composition and top 3 similar materials
            5. If recipes found, use analyze_synthesis_parameters to extract key conditions
            6. Synthesize findings into actionable recommendations
            """
        else:
            prompt = f"""
            Handle this synthesis discovery query: "{query}"
            
            WORKFLOW:
            1. First, identify if this is a composition formula (e.g., Fe2O3) or general query
            2. Use search_similar_materials_advanced to find 10 similar materials by composition
            3. Use get_material_properties to understand the materials' characteristics
            4. Use get_synthesis_recipes for the target material
            5. IF NO DIRECT RECIPES FOUND:
               - Use recursive_synthesis_search to perform deep search across neighbor materials
               - This will explore neighbors-of-neighbors to find adaptable recipes
            6. If recipes found, use analyze_synthesis_parameters to extract key conditions
            7. Synthesize findings into actionable recommendations
        
        RESPONSE FORMAT:
        📊 Target Material Analysis
        - Formula and composition
        - Key properties (if available)
        
        🔬 Synthesis Methods Found
        - Primary synthesis routes
        - Temperature/time conditions
        - Atmosphere requirements
        
        🧪 Recommended Procedure
        - Step-by-step synthesis
        - Critical parameters
        - Safety considerations
        
        📝 Alternative Routes
        - Similar materials' methods
        - Pros/cons of each approach
        
        Focus on practical, reproducible synthesis procedures.
        
        IMPORTANT: After completing the synthesis analysis, ALWAYS generate an HTML report
        using generate_synthesis_html_report with your complete analysis output.
        """
        
        result = Runner.run_sync(self.agent, input=prompt, session=self.session)
        return result.final_output
    
    async def discover_synthesis(self, query: str) -> str:
        """
        Run synthesis discovery asynchronously.
        """
        prompt = f"""
        Discover synthesis methods for: "{query}"
        
        Execute complete synthesis discovery workflow:
        1. Search for similar materials
        2. Retrieve material properties
        3. Find synthesis recipes
        4. Analyze synthesis parameters
        5. Provide comprehensive synthesis recommendations
        
        Be thorough and practical in your recommendations.
        """
        
        result = await Runner.run(self.agent, input=prompt, session=self.session)
        return result.final_output