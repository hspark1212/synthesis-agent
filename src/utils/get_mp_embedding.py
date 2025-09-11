from pathlib import Path
import h5py
import numpy as np

from monty.serialization import loadfn
from matminer.featurizers.composition import ElementProperty


dir_assets = Path(".").resolve().parent.parent / "assets/embedding"
mp_data = loadfn(dir_assets / "mp_dataset_only_GGA.json.gz")
print(f"Read {len(mp_data)} materials from mp_dataset_only_GGA.json.gz")

# Composition Embedding
comps = [d["structure"].composition for d in mp_data]
formulas = [d["formula_pretty"] for d in mp_data]
material_ids = [d["material_id"] for d in mp_data]
featurizer = ElementProperty.from_preset("magpie")
features = np.array(featurizer.featurize_many(comps))
print(f"Shape of features: {features.shape}")

h5_file = dir_assets / "mp_dataset_composition_magpie.h5"
with h5py.File(h5_file, "w") as f:
    f.create_dataset("features", data=features, compression="gzip")
    f.create_dataset("material_ids", data=material_ids, compression="gzip")
    f.create_dataset("formulas", data=formulas, compression="gzip")
print(f"Saved features and material_ids to {h5_file}")
# with h5py.File(h5_file, "r") as f:
#     features = f["features"][:]
#     material_ids = f["material_ids"][:].astype("str")
#     formulas = f["formulas"][:].astype("str")
