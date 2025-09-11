from enum import Enum

import numpy as np
from pymatgen.core import Structure, Composition
from matminer.featurizers.composition import ElementProperty
from mace.calculators import mace_mp


class InputType(Enum):
    COMPOSITION = "composition"
    STRUCTURE = "structure"


class MaterialsEmbedding:
    def __init__(self, input_type: InputType):
        self.input_type = input_type
        self._magpie_featurizer = None
        self._mace_calculator = None

    def _get_composition_embedding(self, composition: Composition) -> np.ndarray:
        if self._magpie_featurizer is None:
            self._magpie_featurizer = ElementProperty.from_preset("magpie")

        return np.array([self._magpie_featurizer.featurize(composition)])

    def _get_structure_embedding(self, structure: Structure) -> np.ndarray:
        if self._mace_calculator is None:
            self._mace_calculator = mace_mp()

        return np.array(
            [
                self._mace_calculator.get_descriptors(structure.to_ase_atoms()).mean(
                    axis=0
                )
            ]
        )

    def get_embedding(self, input_data: Composition | Structure) -> np.ndarray:
        if self.input_type == InputType.COMPOSITION:
            if not isinstance(input_data, Composition):
                raise ValueError("Input data must be a Composition.")
            return self._get_composition_embedding(input_data)
        elif self.input_type == InputType.STRUCTURE:
            if not isinstance(input_data, Structure):
                raise ValueError("Input data must be a Structure.")
            return self._get_structure_embedding(input_data)
        else:
            raise ValueError("Invalid input type.")
