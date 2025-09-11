import os
import h5py

from mp_api.client import MPRester
from pymatgen.core import Composition, Structure
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

from src import ASSETS_DIR
from src.embedding import MaterialsEmbedding, InputType

MPR_API_KEY = os.getenv("MPR_API_KEY")


class SearchAPI:
    def __init__(
        self,
        input_type: InputType,
        n_neighbors: int = 5,
    ):
        self.featurizer = MaterialsEmbedding(input_type=input_type)
        self.n_neighbors = n_neighbors

        # Load pre-computed MP dataset
        self.mp_data = self._load_mp_data()

        # Set up nearest neighbors model
        self._set_nearest_neighbors_model()

    def _load_mp_data(self):
        if self.featurizer.input_type == InputType.COMPOSITION:
            h5_file = ASSETS_DIR / "embedding" / "mp_dataset_composition_magpie.h5"
        elif self.featurizer.input_type == InputType.STRUCTURE:
            h5_file = ASSETS_DIR / "embedding" / "mp_dataset_structure_mace.h5"
        else:
            raise ValueError("Invalid input type.")
        print(f"Loading MP dataset from {h5_file}")

        with h5py.File(h5_file, "r") as f:
            features = f["features"][:]
            material_ids = f["material_ids"][:].astype("str")
            formulas = f["formulas"][:].astype("str")

        return {
            "features": features,
            "material_ids": material_ids,
            "formulas": formulas,
        }

    def _set_nearest_neighbors_model(self):
        self.scaler = StandardScaler().fit(self.mp_data["features"])
        mp_features_scaled = self.scaler.transform(self.mp_data["features"])
        self.nn_model = NearestNeighbors(
            n_neighbors=self.n_neighbors, metric="euclidean"
        ).fit(mp_features_scaled)

    def query(self, input_data: Composition | Structure):
        input_embedding = self.featurizer.get_embedding(input_data)
        input_embedding_scaled = self.scaler.transform(input_embedding)
        distances, indices = self.nn_model.kneighbors(input_embedding_scaled)
        distances = distances.squeeze()
        indices = indices.squeeze()

        # Collect results
        results = []
        for dist, idx in zip(distances, indices):
            results.append(
                {
                    "material_id": self.mp_data["material_ids"][idx],
                    "formula": self.mp_data["formulas"][idx],
                    "distance": dist,
                }
            )

        # get summarydoc for material ids
        material_ids = [res["material_id"] for res in results]
        print(self.mp_data["material_ids"][indices])
        print(self.mp_data["formulas"][indices])

        return results

    def query_synthesis_recipe(self, formulas: list[str]):
        """Query synthesis recipes for a list of formulas."""

        recipes = []
        with MPRester(MPR_API_KEY) as mpr:
            for formula in formulas:
                recipes += mpr.materials.synthesis.search(formulas=[formula])
        return recipes

    def query_summarydoc_from_material_id(self, material_id: str):

        with MPRester(MPR_API_KEY) as mpr:
            summary = mpr.materials.summary.get_data_by_id(material_id)
        return summary
