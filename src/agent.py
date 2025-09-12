import os

from pymatgen.core import Composition, Structure
from mp_api.client import MPRester


from src.embedding import InputType
from src.search_api import SearchAPI
from src.schema import Neighbor, SynthesisRecipe, SummaryDoc

MP_API_KEY = os.getenv("MP_API_KEY")
if MP_API_KEY is None:
    raise ValueError("MP_API_KEY environment variable not set.")


class SynthesisAgent:
    def __init__(self):
        self.search_api_composition = SearchAPI(
            input_type=InputType.COMPOSITION, max_neighbors=100
        )
        self.search_api_structure = SearchAPI(
            input_type=InputType.STRUCTURE, max_neighbors=100
        )
        self.mpr = MPRester(api_key=MP_API_KEY)

    def find_similar_materials_by_composition(
        self, composition_str: str, n_neighbors: int = 10
    ) -> list[Neighbor]:
        composition = Composition(composition_str)
        results = self.search_api_composition.query(
            composition, n_neighbors=n_neighbors
        )
        return results

    def find_similar_materials_by_structure(
        self, structure: Structure, n_neighbors: int = 10
    ) -> list[Neighbor]:
        results = self.search_api_structure.query(structure, n_neighbors=n_neighbors)
        return results

    def get_synthesis_recipes_by_formula(self, formula: str) -> list[SynthesisRecipe]:
        recipes = self.mpr.materials.synthesis.search(target_formula=formula)
        return recipes

    def get_summarydoc_by_material_id(self, material_id: str) -> list[SummaryDoc]:
        summarydoc = self.mpr.materials.summary.search(material_ids=[material_id])
        return summarydoc

    def get_structure_by_material_id(self, material_id: str) -> Structure:
        structure = self.mpr.materials.get_structure_by_material_id(material_id)
        return structure


class SynthesisLLMAgent(SynthesisAgent):
    pass
