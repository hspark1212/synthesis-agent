# SKY - Synthesis Analysis Agent

**SKY** is an **LLM-powered agent** for materials synthesis analysis and recommendation.  
It leverages **similarity search on synthesis recipes** from the [Materials Project](https://materialsproject.org/) database to help researchers discover related compounds, structures, and synthesis pathways.

---

## 🚀 Features

- 🔍 **Composition-based similarity search** – find materials with similar chemical formulas.  
- 🏗️ **Structure-based similarity search** – identify related compounds by crystal structure.  
- 📜 **Synthesis recipe retrieval** – access known synthesis procedures for materials.  
- 📊 **Property lookup** – fetch summaries and structural data from the Materials Project.  
- 🤖 **LLM-enhanced synthesis recommendations** – analyze and recommend synthesis recipes from similar materials using AI reasoning.

---

## 🛠️ Installation

```bash
# Clone repository
git clone <repository-url>
cd synthesis-agent

# Install dependencies (requires Python 3.11+)
uv sync

# Set up environment variables (MP_API_KEY, OPENAI_API_KEY)
cp .env.example .env
```

> ⚠️ You will need a valid [Materials Project API key](https://materialsproject.org/open) (`MP_API_KEY`) and an OpenAI API key (`OPENAI_API_KEY`).

---

## 📒 Quick Start

Check out the tutorial notebook for a hands-on introduction:  
👉 [tutorial.ipynb](tutorial.ipynb)

---

## 🧰 CLI (sky)

After installation, the SKY CLI is available as the `sky` command:

```bash
# Verify environment and data
sky setup

# Composition-based search
sky search Fe2O3

# Structure-based search from a CIF file
sky search path/to/material.cif

# Interactive chat mode
sky chat

# Show help
sky --help
```

Note: SKY uses OPENAI_API_KEY (or OPENAI_MDG_API_KEY) and optionally MP_API_KEY from your environment.

---

### Usage 1: Find similar materials by **composition**

```python
from src.agent import SynthesisAgent

# Initialize agent
agent = SynthesisAgent()

# Find similar materials by composition
results = agent.find_similar_materials_by_composition("Fe2O3", n_neighbors=5)
print(results)
```

---

### Usage 2: Find similar materials by **structure**

```python
from pymatgen.core import Structure
from src.agent import SynthesisAgent

# Initialize agent
agent = SynthesisAgent()

# Load structure file
structure = Structure.from_file("material.cif")

# Structure-based similarity search
results = agent.find_similar_materials_by_structure(structure, n_neighbors=5)
print(results)

# Get synthesis recipes for a formula
recipes = agent.get_synthesis_recipes_by_formula("Fe2O3")
print(recipes)
```

---

## ⚙️ Core API

### `SynthesisAgent` (src/agent.py)

```python
from src.agent import SynthesisAgent
from pymatgen.core import Structure

# Initialize agent (requires MP_API_KEY)
agent = SynthesisAgent()

# --- Composition-based similarity search ---
results = agent.find_similar_materials_by_composition("Fe2O3", n_neighbors=5)
# Returns: list[Neighbor] with {material_id, formula, distance, confidence}

# --- Structure-based similarity search ---
structure = Structure.from_file("material.cif")
results = agent.find_similar_materials_by_structure(structure, n_neighbors=5)

# --- Synthesis recipes ---
recipes = agent.get_synthesis_recipes_by_formula("Fe2O3")
# Returns: list[SynthesisRecipe] from Materials Project

# --- Material properties ---
summary = agent.get_summarydoc_by_material_id("mp-1234")
structure = agent.get_structure_by_material_id("mp-1234")
```

---

## 📂 Project Structure

```text
synthesis-agent/
│── src/
│   ├── agent.py         # Core SynthesisAgent API
│   ├── utils/           # Helper functions
│── tutorial.ipynb       # Quick start tutorial
│── .env.example         # Environment variable template
│── README.md            # Project documentation
```

---

## 🔑 Environment Variables

Create a `.env` file based on `.env.example`:

```bash
MP_API_KEY=your_materials_project_api_key
OPENAI_API_KEY=your_openai_api_key
```

---

## 📚 References

- [Materials Project](https://materialsproject.org/)  
- [pymatgen](https://pymatgen.org/)  
- [OpenAI API](https://platform.openai.com/)  

---

## 📜 License

This project is licensed under the **MIT License**.  
See the [LICENSE](LICENSE) file for details.
