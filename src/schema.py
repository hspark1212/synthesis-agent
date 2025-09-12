from pydantic import BaseModel
from emmet.core.synthesis import SynthesisRecipe
from emmet.core.summary import SummaryDoc


class Neighbor(BaseModel):
    neighbor_index: int
    material_id: str
    formula: str
    distance: float


__all__ = ["Neighbor", "SynthesisRecipe", "SummaryDoc"]
