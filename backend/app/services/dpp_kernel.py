"""
Determinantal Point Process (DPP) Kernel for Diversity Optimization

Implements the patent specification's bounded candidate selection with diversity:
    L_ij = q_i * S_ij * q_j
    
Where:
    - q_i = quality score (relevance to user)
    - S_ij = similarity kernel between items i and j
    
The DPP naturally penalizes similar items, promoting diversity while
respecting relevance scores.
"""

import numpy as np
from typing import List, Tuple, Optional
from app.models import Content, ContentMood


class DPPKernel:
    """
    Determinantal Point Process kernel for diverse subset selection.
    
    Key innovation from patent: Cognitive-load-aware set size constraint
    that shrinks recommendations when user hesitation is high.
    """
    
    def __init__(
        self,
        genre_weight: float = 0.4,
        mood_weight: float = 0.3,
        theme_weight: float = 0.2,
        year_weight: float = 0.1,
        sigma: float = 0.5  # RBF kernel bandwidth
    ):
        self.genre_weight = genre_weight
        self.mood_weight = mood_weight
        self.theme_weight = theme_weight
        self.year_weight = year_weight
        self.sigma = sigma
    
    def compute_feature_vector(self, content: Content) -> np.ndarray:
        """
        Extract feature vector φ(i) for content item.
        Used in similarity kernel: S_ij = exp(-||φ(i) - φ(j)||² / 2σ²)
        """
        features = []
        
        # Genre features (one-hot style, but weighted)
        all_genres = [
            "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
            "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
            "Romance", "Science Fiction", "Sci-Fi", "Thriller", "TV Movie", "War", "Western"
        ]
        genre_vec = np.zeros(len(all_genres))
        for i, g in enumerate(all_genres):
            if g.lower() in [x.lower() for x in content.genre]:
                genre_vec[i] = 1.0
        features.extend(genre_vec * self.genre_weight)
        
        # Mood features
        all_moods = [m.value for m in ContentMood]
        mood_vec = np.zeros(len(all_moods))
        for i, m in enumerate(all_moods):
            if any(cm.value == m for cm in content.mood):
                mood_vec[i] = 1.0
        features.extend(mood_vec * self.mood_weight)
        
        # Theme features (simplified - use description embedding proxy)
        # In production, this would use actual embeddings
        theme_hash = hash(tuple(sorted(content.themes))) % 100
        theme_vec = np.zeros(10)
        theme_vec[theme_hash % 10] = 1.0
        features.extend(theme_vec * self.theme_weight)
        
        # Year feature (normalized to [0, 1])
        year_norm = (content.year - 1950) / 80.0  # Normalize 1950-2030 to 0-1
        year_norm = max(0, min(1, year_norm))
        features.append(year_norm * self.year_weight)
        
        return np.array(features)
    
    def compute_similarity_kernel(self, c1: Content, c2: Content) -> float:
        """
        Compute RBF similarity kernel between two content items.
        S_ij = exp(-||φ(i) - φ(j)||² / 2σ²)
        
        High similarity = items are alike = DPP will penalize selecting both
        """
        phi_i = self.compute_feature_vector(c1)
        phi_j = self.compute_feature_vector(c2)
        
        diff = phi_i - phi_j
        squared_dist = np.dot(diff, diff)
        
        return np.exp(-squared_dist / (2 * self.sigma ** 2))
    
    def compute_l_matrix(
        self,
        candidates: List[Content],
        quality_scores: List[float]
    ) -> np.ndarray:
        """
        Compute the L-matrix for DPP sampling.
        
        L_ij = q_i * S_ij * q_j
        
        Where:
            q_i = quality score (relevance) for item i
            S_ij = similarity kernel between items i and j
        
        The determinant det(L_S) for a subset S measures both:
            - Individual quality (diagonal terms q_i²)
            - Diversity penalty (off-diagonal similarity terms)
        """
        n = len(candidates)
        L = np.zeros((n, n))
        
        # Normalize quality scores to prevent numerical issues
        q = np.array(quality_scores)
        q = q / (q.max() + 1e-8)  # Normalize to [0, 1]
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    # Diagonal: q_i * S_ii * q_i = q_i² (S_ii = 1)
                    L[i, j] = q[i] ** 2
                else:
                    # Off-diagonal: q_i * S_ij * q_j
                    s_ij = self.compute_similarity_kernel(candidates[i], candidates[j])
                    L[i, j] = q[i] * s_ij * q[j]
        
        return L
    
    def compute_log_det(self, L: np.ndarray, indices: List[int]) -> float:
        """
        Compute log det(L_S) for subset S.
        
        This is the DPP quality measure - higher = better diverse set.
        """
        if len(indices) == 0:
            return float('-inf')
        
        L_S = L[np.ix_(indices, indices)]
        
        # Use eigenvalues for numerical stability
        eigvals = np.linalg.eigvalsh(L_S)
        eigvals = np.maximum(eigvals, 1e-10)  # Avoid log(0)
        
        return np.sum(np.log(eigvals))
    
    def greedy_maximize_log_det(
        self,
        L: np.ndarray,
        k: int,
        must_include: Optional[List[int]] = None
    ) -> Tuple[List[int], float]:
        """
        Greedy algorithm to maximize log det(L_S) subject to |S| = k.
        
        This approximates the NP-hard exact DPP MAP inference.
        
        Returns:
            selected_indices: Indices of selected items
            log_det_value: Final log det(L_S)
        """
        n = L.shape[0]
        k = min(k, n)
        
        # Initialize with must-include items if any
        selected = list(must_include) if must_include else []
        remaining = [i for i in range(n) if i not in selected]
        
        # Greedy selection
        while len(selected) < k and remaining:
            best_idx = None
            best_gain = float('-inf')
            
            for idx in remaining:
                candidate_set = selected + [idx]
                log_det = self.compute_log_det(L, candidate_set)
                
                # Compute marginal gain
                if selected:
                    current_log_det = self.compute_log_det(L, selected)
                    gain = log_det - current_log_det
                else:
                    gain = log_det
                
                if gain > best_gain:
                    best_gain = gain
                    best_idx = idx
            
            if best_idx is not None:
                selected.append(best_idx)
                remaining.remove(best_idx)
            else:
                break
        
        final_log_det = self.compute_log_det(L, selected)
        return selected, final_log_det
    
    def sample_dpp(
        self,
        L: np.ndarray,
        k: int,
        num_samples: int = 1
    ) -> List[List[int]]:
        """
        Sample from k-DPP using eigendecomposition.
        
        For exact DPP sampling, we use the spectral algorithm:
        1. Compute eigendecomposition L = V Λ V^T
        2. Sample subset of eigenvectors
        3. Sample items using orthogonal projection
        
        For simplicity in this implementation, we use greedy + randomization.
        """
        samples = []
        
        for _ in range(num_samples):
            # Add small random noise to break ties
            L_noisy = L + np.random.randn(*L.shape) * 1e-6
            selected, _ = self.greedy_maximize_log_det(L_noisy, k)
            samples.append(selected)
        
        return samples
    
    def compute_marginal_probabilities(
        self,
        L: np.ndarray
    ) -> np.ndarray:
        """
        Compute marginal inclusion probabilities P(i ∈ S) for each item.
        
        P(i ∈ S) = L_ii * (1 + L)^(-1)_ii for L-ensemble
        
        These marginals are useful for understanding each item's
        contribution to diversity.
        """
        n = L.shape[0]
        
        # K = L(I + L)^(-1) is the marginal kernel
        K = L @ np.linalg.inv(np.eye(n) + L)
        
        # Diagonal of K gives marginal probabilities
        marginals = np.diag(K)
        
        return marginals
    
    def compute_confidence_uplift(
        self,
        L: np.ndarray,
        current_set: List[int],
        candidate_idx: int,
        base_confidence: float
    ) -> float:
        """
        Compute expected confidence uplift from adding a candidate.
        
        ΔC(i) = expected increase in user decision confidence
        
        This implements the joint objective from the patent:
            max log det(L_S) + λ * Σ ΔC(i)
        """
        if candidate_idx in current_set:
            return 0.0
        
        # Compute diversity gain
        new_set = current_set + [candidate_idx]
        if current_set:
            current_log_det = self.compute_log_det(L, current_set)
        else:
            current_log_det = 0.0
        new_log_det = self.compute_log_det(L, new_set)
        diversity_gain = new_log_det - current_log_det
        
        # Confidence uplift is proportional to quality and diversity contribution
        quality = np.sqrt(L[candidate_idx, candidate_idx])
        uplift = quality * (1 + diversity_gain) * (1 - base_confidence)
        
        return max(0, min(1, uplift))


class CognitiveDPPSelector:
    """
    Cognitive-load-aware DPP selector.
    
    Implements the patent's key innovation: shrinking recommendation set
    size when user hesitation is high.
    
    n = max(2, min(5, round(5 - 3 * η)))
    
    Where η is the hesitation score.
    """
    
    def __init__(self, dpp_kernel: Optional[DPPKernel] = None):
        self.dpp = dpp_kernel or DPPKernel()
    
    def compute_optimal_set_size(
        self,
        hesitation_score: float,
        min_size: int = 2,
        max_size: int = 5
    ) -> int:
        """
        Compute cognitively optimal recommendation set size.
        
        n = max(min_size, min(max_size, round(max_size - 3 * η)))
        
        High hesitation → fewer choices (reduce cognitive load)
        Low hesitation → more choices (user can handle exploration)
        """
        # Formula from patent specification
        raw_size = max_size - 3 * hesitation_score
        optimal_size = max(min_size, min(max_size, round(raw_size)))
        
        return int(optimal_size)
    
    def select_diverse_recommendations(
        self,
        candidates: List[Content],
        quality_scores: List[float],
        hesitation_score: float,
        base_confidence: float = 0.5
    ) -> Tuple[List[int], float, List[float]]:
        """
        Select diverse recommendations using DPP with cognitive-load awareness.
        
        Returns:
            selected_indices: Indices of selected items
            log_det: DPP quality measure
            confidence_uplifts: Expected confidence gain for each selected item
        """
        # Compute optimal set size based on hesitation
        k = self.compute_optimal_set_size(hesitation_score)
        
        # Build L-matrix
        L = self.dpp.compute_l_matrix(candidates, quality_scores)
        
        # Select diverse subset
        selected_indices, log_det = self.dpp.greedy_maximize_log_det(L, k)
        
        # Compute confidence uplifts
        confidence_uplifts = []
        cumulative_set = []
        for idx in selected_indices:
            uplift = self.dpp.compute_confidence_uplift(
                L, cumulative_set, idx, base_confidence
            )
            confidence_uplifts.append(uplift)
            cumulative_set.append(idx)
        
        return selected_indices, log_det, confidence_uplifts
    
    def get_marginal_probabilities(
        self,
        candidates: List[Content],
        quality_scores: List[float]
    ) -> List[float]:
        """Get DPP marginal inclusion probabilities for all candidates."""
        L = self.dpp.compute_l_matrix(candidates, quality_scores)
        return self.dpp.compute_marginal_probabilities(L).tolist()


# Singleton instance
dpp_selector = CognitiveDPPSelector()
