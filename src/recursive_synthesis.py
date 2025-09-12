"""
Recursive Best-Guess Synthesis Search Algorithm

This module implements a confidence-based recursive search for synthesis recipes
when direct recipes are not available for a target material.
"""

import os
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np

from pymatgen.core import Composition
from mp_api.client import MPRester

from .schema import Neighbor, SynthesisRecipe
from .agent import SynthesisAgent


@dataclass
class RecipeCandidate:
    """Represents a potential synthesis recipe from a neighbor material."""
    material_id: str
    formula: str
    recipe: SynthesisRecipe
    confidence: float
    distance: float
    path_length: int  # How many hops from target
    reasoning: str = ""


@dataclass 
class SearchNode:
    """Node in the recursive search tree."""
    material_id: str
    formula: str
    confidence: float
    distance: float
    depth: int
    parent: Optional['SearchNode'] = None
    children: List['SearchNode'] = field(default_factory=list)
    
    def get_path(self) -> List[str]:
        """Get the path from root to this node."""
        path = []
        node = self
        while node:
            path.append(f"{node.formula} ({node.material_id})")
            node = node.parent
        return list(reversed(path))


class RecursiveSynthesisSearch:
    """
    Implements recursive best-guess algorithm for finding synthesis recipes.
    
    The algorithm works by:
    1. Starting with a target material
    2. If no direct recipe, search neighbors with high confidence
    3. Recursively explore neighbors of neighbors with decreasing confidence threshold
    4. Aggregate found recipes weighted by confidence
    5. Synthesize best guess based on chemical similarity
    """
    
    def __init__(
        self,
        synthesis_agent: Optional[SynthesisAgent] = None,
        mpr: Optional[MPRester] = None,
        max_depth: int = 3,
        min_confidence: float = 0.7,
        confidence_decay: float = 0.85,
        max_neighbors_per_level: int = 10,
        verbose: bool = True
    ):
        """
        Initialize the recursive synthesis search.
        
        Args:
            synthesis_agent: Agent for similarity search and recipe retrieval
            mpr: Materials Project client
            max_depth: Maximum recursion depth
            min_confidence: Minimum confidence threshold to explore
            confidence_decay: How much to reduce confidence threshold per level
            max_neighbors_per_level: Max neighbors to explore at each level
            verbose: Print search progress
        """
        self.agent = synthesis_agent or SynthesisAgent()
        self.mpr = mpr or MPRester(api_key=os.getenv("MP_API_KEY"))
        self.max_depth = max_depth
        self.min_confidence = min_confidence
        self.confidence_decay = confidence_decay
        self.max_neighbors_per_level = max_neighbors_per_level
        self.verbose = verbose
        
        # Track visited materials to avoid cycles
        self.visited: Set[str] = set()
        self.recipe_candidates: List[RecipeCandidate] = []
        
    def search(
        self, 
        target_formula: str,
        n_initial_neighbors: int = 30
    ) -> Dict:
        """
        Main entry point for recursive synthesis search.
        
        Args:
            target_formula: Target material composition
            n_initial_neighbors: Number of initial neighbors to consider
            
        Returns:
            Dictionary with search results and best guess synthesis
        """
        self.visited.clear()
        self.recipe_candidates.clear()
        
        if self.verbose:
            print(f"🔍 Starting recursive synthesis search for {target_formula}")
        
        # Create root node
        root = SearchNode(
            material_id="target",
            formula=target_formula,
            confidence=1.0,
            distance=0.0,
            depth=0
        )
        
        # Start recursive search
        self._recursive_search(
            node=root,
            n_neighbors=n_initial_neighbors,
            confidence_threshold=1.0
        )
        
        # Aggregate and synthesize results
        results = self._synthesize_results(target_formula)
        
        return results
    
    def _recursive_search(
        self,
        node: SearchNode,
        n_neighbors: int,
        confidence_threshold: float
    ):
        """
        Recursive depth-first search for synthesis recipes.
        
        Args:
            node: Current search node
            n_neighbors: Number of neighbors to explore
            confidence_threshold: Current confidence threshold
        """
        # Check termination conditions
        if node.depth >= self.max_depth:
            if self.verbose:
                print(f"  {'  ' * node.depth}⛔ Max depth reached at {node.formula}")
            return
        
        if node.confidence < self.min_confidence:
            if self.verbose:
                print(f"  {'  ' * node.depth}⛔ Confidence too low ({node.confidence:.3f}) for {node.formula}")
            return
        
        if node.material_id in self.visited and node.material_id != "target":
            if self.verbose:
                print(f"  {'  ' * node.depth}🔄 Already visited {node.formula}")
            return
        
        # Mark as visited
        if node.material_id != "target":
            self.visited.add(node.material_id)
        
        if self.verbose:
            print(f"  {'  ' * node.depth}📍 Exploring {node.formula} (conf={node.confidence:.3f}, depth={node.depth})")
        
        # Try to get recipes for current node
        if node.material_id != "target":
            self._check_recipes(node)
        
        # Get neighbors
        try:
            neighbors = self.agent.find_similar_materials_by_composition(
                node.formula, 
                n_neighbors=n_neighbors
            )
        except Exception as e:
            if self.verbose:
                print(f"  {'  ' * node.depth}❌ Error getting neighbors: {e}")
            return
        
        # Filter and sort neighbors by confidence
        filtered_neighbors = [
            n for n in neighbors 
            if n.confidence >= confidence_threshold * self.confidence_decay
            and n.material_id not in self.visited
        ]
        
        # Limit neighbors per level
        filtered_neighbors = filtered_neighbors[:self.max_neighbors_per_level]
        
        if self.verbose and filtered_neighbors:
            print(f"  {'  ' * node.depth}🔗 Found {len(filtered_neighbors)} promising neighbors")
        
        # Recursively explore neighbors
        for neighbor in filtered_neighbors:
            child = SearchNode(
                material_id=neighbor.material_id,
                formula=neighbor.formula,
                confidence=neighbor.confidence,
                distance=neighbor.distance,
                depth=node.depth + 1,
                parent=node
            )
            node.children.append(child)
            
            # Recursive call with decayed threshold
            self._recursive_search(
                node=child,
                n_neighbors=max(5, n_neighbors // 2),  # Reduce neighbors as we go deeper
                confidence_threshold=confidence_threshold * self.confidence_decay
            )
    
    def _check_recipes(self, node: SearchNode):
        """
        Check if a material has synthesis recipes.
        
        Args:
            node: Search node to check
        """
        try:
            # Try to get recipes
            recipes = self.agent.get_synthesis_recipes_by_formula(node.formula)
            
            if recipes and len(recipes) > 0:
                if self.verbose:
                    print(f"  {'  ' * node.depth}✅ Found {len(recipes)} recipe(s) for {node.formula}")
                
                # Add each recipe as a candidate
                for recipe in recipes[:3]:  # Limit to top 3 recipes per material
                    candidate = RecipeCandidate(
                        material_id=node.material_id,
                        formula=node.formula,
                        recipe=recipe,
                        confidence=node.confidence,
                        distance=node.distance,
                        path_length=node.depth,
                        reasoning=f"Found via path: {' → '.join(node.get_path())}"
                    )
                    self.recipe_candidates.append(candidate)
                    
        except Exception as e:
            if self.verbose:
                print(f"  {'  ' * node.depth}⚠️ Could not check recipes for {node.formula}: {e}")
    
    def _synthesize_results(self, target_formula: str) -> Dict:
        """
        Aggregate and synthesize the search results into a best guess.
        
        Args:
            target_formula: Original target formula
            
        Returns:
            Dictionary with synthesis recommendations
        """
        if not self.recipe_candidates:
            return {
                "status": "no_recipes_found",
                "target": target_formula,
                "message": "No synthesis recipes found in recursive search",
                "visited_materials": len(self.visited),
                "recommendations": []
            }
        
        # Sort candidates by weighted score
        for candidate in self.recipe_candidates:
            # Weight by confidence and inverse path length
            candidate.score = candidate.confidence / (1 + 0.2 * candidate.path_length)
        
        self.recipe_candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Group recipes by material
        recipes_by_material = defaultdict(list)
        for candidate in self.recipe_candidates:
            recipes_by_material[candidate.formula].append(candidate)
        
        # Create synthesis recommendations
        recommendations = []
        for formula, candidates in list(recipes_by_material.items())[:5]:  # Top 5 materials
            best_candidate = candidates[0]
            
            # Calculate adaptation strategy
            adaptation = self._calculate_adaptation(target_formula, formula)
            
            recommendations.append({
                "source_material": formula,
                "material_id": best_candidate.material_id,
                "confidence": best_candidate.confidence,
                "distance": best_candidate.distance,
                "path_length": best_candidate.path_length,
                "score": best_candidate.score,
                "num_recipes": len(candidates),
                "adaptation_strategy": adaptation,
                "reasoning": best_candidate.reasoning
            })
        
        return {
            "status": "success",
            "target": target_formula,
            "visited_materials": len(self.visited),
            "total_candidates": len(self.recipe_candidates),
            "unique_materials_with_recipes": len(recipes_by_material),
            "recommendations": recommendations,
            "best_guess": self._generate_best_guess(target_formula, recommendations)
        }
    
    def _calculate_adaptation(self, target: str, source: str) -> Dict:
        """
        Calculate how to adapt a source recipe for the target material.
        
        Args:
            target: Target formula
            source: Source formula with known recipe
            
        Returns:
            Adaptation strategy dictionary
        """
        target_comp = Composition(target)
        source_comp = Composition(source)
        
        # Get elemental differences
        target_elements = set(target_comp.elements)
        source_elements = set(source_comp.elements)
        
        added_elements = target_elements - source_elements
        removed_elements = source_elements - target_elements
        common_elements = target_elements & source_elements
        
        # Calculate stoichiometry changes
        stoich_changes = {}
        for el in common_elements:
            target_ratio = target_comp.get_atomic_fraction(el)
            source_ratio = source_comp.get_atomic_fraction(el)
            change = (target_ratio - source_ratio) / source_ratio if source_ratio > 0 else 0
            stoich_changes[str(el)] = {
                "target": target_ratio,
                "source": source_ratio,
                "change_percent": change * 100
            }
        
        return {
            "added_elements": [str(el) for el in added_elements],
            "removed_elements": [str(el) for el in removed_elements],
            "common_elements": [str(el) for el in common_elements],
            "stoichiometry_changes": stoich_changes,
            "similarity_score": len(common_elements) / max(len(target_elements), len(source_elements))
        }
    
    def _generate_best_guess(self, target: str, recommendations: List[Dict]) -> Dict:
        """
        Generate a best guess synthesis procedure based on found recipes.
        
        Args:
            target: Target formula
            recommendations: List of recipe recommendations
            
        Returns:
            Best guess synthesis dictionary
        """
        if not recommendations:
            return {"message": "No recommendations available"}
        
        best = recommendations[0]
        
        # Determine synthesis approach based on confidence
        if best["confidence"] > 0.95:
            approach = "direct_adaptation"
            confidence_level = "very_high"
        elif best["confidence"] > 0.85:
            approach = "minor_modification"
            confidence_level = "high"
        elif best["confidence"] > 0.75:
            approach = "guided_exploration"
            confidence_level = "moderate"
        else:
            approach = "experimental_optimization"
            confidence_level = "exploratory"
        
        return {
            "approach": approach,
            "confidence_level": confidence_level,
            "primary_reference": best["source_material"],
            "adaptation_required": best["adaptation_strategy"],
            "key_considerations": [
                f"Based on {best['source_material']} with {best['confidence']:.1%} confidence",
                f"Requires adapting for: {', '.join(best['adaptation_strategy']['added_elements'])}",
                f"Path length: {best['path_length']} hops from target",
                f"Explored {len(recommendations)} potential routes"
            ],
            "recommended_validation": [
                "Start with small-scale test synthesis",
                "Verify phase purity with XRD",
                "Adjust stoichiometry based on initial results",
                "Consider alternative precursors for added elements"
            ]
        }