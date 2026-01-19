"""
AI Recommendation Engine for Sequential Narrative AI
Implements multi-factor scoring, diversity optimization, and sequence optimization.
AI-powered recommendation engine with diversity optimization.

Patent-aligned features:
- DPP kernel for diversity (L_ij = q_i * S_ij * q_j)
- Hazard-of-commit model for timing
- Cognitive-load aware set size
- Multi-head encoder integration
"""
import time
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import random

from app.models import (
    Content, UserProfile, Recommendation, NLPIntent, 
    RecommendationRequest, RecommendationResponse,
    MicroPitch, ContentMood, ContentType, TelemetryEvent
)
from app.config import settings
from app.data.content_db import get_all_content
from app.services.nlp_service import nlp_service
from app.services.streaming_apis import content_service
from app.services.dpp_kernel import dpp_selector, CognitiveDPPSelector
from app.services.survival_model import hazard_model, HazardOfCommitModel
from app.services.multi_head_encoder import multi_head_encoder, MultiHeadDecisionEncoder


class RecommendationEngine:
    """
    AI-powered recommendation engine implementing:
    - Multi-factor content scoring with patent-aligned metrics
    - Full DPP kernel (L_ij = q_i * S_ij * q_j) for diversity
    - Hazard-of-commit survival model for timing
    - Multi-head encoder for decision state
    - Cognitive-load aware recommendation count
    """
    
    def __init__(
        self,
        dpp_selector: CognitiveDPPSelector = dpp_selector,
        hazard_model: HazardOfCommitModel = hazard_model,
        encoder: MultiHeadDecisionEncoder = multi_head_encoder
    ):
        self.dpp_selector = dpp_selector
        self.hazard_model = hazard_model
        self.encoder = encoder
        
        self.weights = {
            "genre_match": settings.WEIGHT_GENRE_MATCH,
            "mood_match": settings.WEIGHT_MOOD_MATCH,
            "rating_boost": settings.WEIGHT_RATING_BOOST,
            "recency_boost": settings.WEIGHT_RECENCY_BOOST,
            "diversity_penalty": settings.WEIGHT_DIVERSITY_PENALTY,
            "history_penalty": settings.WEIGHT_HISTORY_PENALTY,
        }
    
    def _build_search_query(
        self, 
        raw_query: str, 
        intent: NLPIntent, 
        user_profile: UserProfile
    ) -> str:
        """Build an optimized search query from user input and preferences"""
        query_parts = []
        
        # Use raw query if provided
        if raw_query:
            query_parts.append(raw_query)
        
        # Add intent preferences
        if intent.preferences:
            query_parts.extend(intent.preferences[:2])
        
        # Add mood if specified
        if intent.mood:
            query_parts.append(intent.mood.value)
        
        # Add user's favorite genres if no specific query
        if not query_parts and user_profile.preferences.favorite_genres:
            query_parts.extend(user_profile.preferences.favorite_genres[:2])
        
        # Default fallback
        if not query_parts:
            query_parts = ["popular", "trending"]
        
        return " ".join(query_parts)
    
    async def _fetch_content_from_apis(
        self, 
        search_query: str, 
        intent: NLPIntent
    ) -> List[Content]:
        """Fetch content from streaming APIs (TMDb, YouTube, Paramount+)"""
        all_content: List[Content] = []
        
        try:
            # Search all providers with higher limit
            results = await content_service.search_all(search_query, limit_per_provider=10)
            
            # Convert API results to Content objects
            for item in results:
                content = self._api_result_to_content(item)
                if content:
                    all_content.append(content)
            
            # Only add trending if we have very few results (< 3)
            # AND the query is generic (not specific like "documentary")
            generic_queries = {"watch", "surprise", "trending", "popular", "recommend"}
            query_words = set(search_query.lower().split())
            is_generic = bool(generic_queries & query_words) or len(search_query.split()) <= 2
            
            if len(all_content) < 3 and is_generic:
                trending = await content_service.get_trending_all(limit_per_provider=3)
                for item in trending:
                    content = self._api_result_to_content(item)
                    if content and content.id not in [c.id for c in all_content]:
                        all_content.append(content)
        
        except Exception as e:
            print(f"Error fetching from streaming APIs: {e}")
        
        return all_content
    
    def _api_result_to_content(self, item: dict) -> Optional[Content]:
        """Convert streaming API result to Content model"""
        try:
            # Determine content type
            item_type = item.get("type", "movie")
            if item_type == "video":
                content_type = ContentType.VIDEO
            elif item_type == "series":
                content_type = ContentType.SERIES
            else:
                content_type = ContentType.MOVIE
            
            # Map moods based on genres
            moods = self._infer_moods_from_genres(item.get("genre", []))
            
            return Content(
                id=item.get("id", ""),
                title=item.get("title", "Unknown"),
                type=content_type,
                genre=item.get("genre", []),
                year=item.get("year", 2024),
                rating=float(item.get("rating", 7.0)),
                duration=item.get("duration", "2h"),
                poster_url=item.get("poster_url"),
                backdrop_url=item.get("backdrop_url"),
                description=item.get("description", ""),
                cast=item.get("cast", []),
                director=item.get("director", ""),
                themes=self._infer_themes_from_description(item.get("description", "")),
                mood=moods,
                standout_scenes=[],
                fun_facts=[],
                streaming_url=item.get("watch_url") or item.get("streaming_url"),
                provider=item.get("provider", "unknown")
            )
        except Exception as e:
            print(f"Error converting API result: {e}")
            return None
    
    def _infer_moods_from_genres(self, genres: List[str]) -> List[ContentMood]:
        """Infer content moods from genres"""
        mood_map = {
            "Action": ContentMood.INTENSE,
            "Thriller": ContentMood.INTENSE,
            "Horror": ContentMood.INTENSE,
            "Comedy": ContentMood.UPLIFTING,
            "Romance": ContentMood.ROMANTIC,
            "Drama": ContentMood.THOUGHT_PROVOKING,
            "Documentary": ContentMood.THOUGHT_PROVOKING,
            "Sci-Fi": ContentMood.THOUGHT_PROVOKING,
            "Fantasy": ContentMood.ESCAPIST,
            "Adventure": ContentMood.ESCAPIST,
            "Animation": ContentMood.UPLIFTING,
            "Family": ContentMood.COZY,
            "Mystery": ContentMood.THOUGHT_PROVOKING,
        }
        
        moods = set()
        for genre in genres:
            for key, mood in mood_map.items():
                if key.lower() in genre.lower():
                    moods.add(mood)
        
        return list(moods) if moods else [ContentMood.UPLIFTING]
    
    def _infer_themes_from_description(self, description: str) -> List[str]:
        """Extract themes from description"""
        theme_keywords = {
            "family": "family",
            "love": "love",
            "friendship": "friendship",
            "revenge": "revenge",
            "survival": "survival",
            "justice": "justice",
            "power": "power",
            "identity": "identity",
            "redemption": "redemption",
            "adventure": "adventure",
        }
        
        themes = []
        desc_lower = description.lower()
        for keyword, theme in theme_keywords.items():
            if keyword in desc_lower:
                themes.append(theme)
        
        return themes[:3]
    
    async def generate_recommendations(
        self, 
        request: RecommendationRequest,
        telemetry_events: Optional[List[TelemetryEvent]] = None
    ) -> RecommendationResponse:
        """
        Generate personalized recommendations based on user query and profile.
        
        Uses patent-aligned architecture:
        1. Multi-head encoder for decision state
        2. DPP kernel for diversity optimization
        3. Hazard model for timing-aware selection
        
        Args:
            request: RecommendationRequest with query, user profile, and constraints
            telemetry_events: Optional recent telemetry for enhanced state
            
        Returns:
            RecommendationResponse with ranked, diverse recommendations
        """
        start_time = time.time()
        
        # ========== Multi-Head Decision State Encoding ==========
        # Get enhanced decision state from multi-head encoder
        telemetry = telemetry_events or []
        time_in_session = request.user_profile.contextual_signals.session_duration
        
        enhanced_state = self.encoder.create_enhanced_decision_state(
            request.user_profile.decision_state,
            telemetry,
            time_in_session
        )
        
        # Get survival predictions
        survival_pred = self.hazard_model.predict_time_to_commit(
            request.user_profile.decision_state,
            time_in_session
        )
        
        # ========== Query Processing ==========
        # Parse query intent if provided
        intent = None
        if request.query:
            intent = await nlp_service.process_query(request.query)
        else:
            intent = NLPIntent(
                action="recommend",
                context="general",
                preferences=[],
                raw_query=""
            )
        
        # Build search query from intent and user preferences
        search_query = self._build_search_query(request.query, intent, request.user_profile)
        
        # Fetch content from real streaming APIs
        all_content = await self._fetch_content_from_apis(search_query, intent)
        
        # Fallback to mock data if no results from APIs
        if not all_content:
            all_content = get_all_content()
        
        exclude_ids = set(request.constraints.get("exclude_content_ids", []) if request.constraints else [])
        
        # Add recently watched to exclusions
        for record in request.user_profile.viewing_history[-5:]:
            exclude_ids.add(record.content_id)
        
        available_content = [c for c in all_content if c.id not in exclude_ids]
        
        # ========== Content Scoring ==========
        # Score all content (quality scores for DPP)
        scored_content = [
            (content, self._calculate_score(content, request.user_profile, intent))
            for content in available_content
        ]
        scored_content.sort(key=lambda x: x[1], reverse=True)
        
        # ========== DPP-Based Diversity Selection ==========
        # Use cognitive-load aware set size from enhanced state
        optimal_count = enhanced_state.optimal_set_size
        max_results = request.constraints.get("max_results", optimal_count) if request.constraints else optimal_count
        max_results = min(max_results, settings.MAX_RECOMMENDATIONS)
        max_results = max(max_results, settings.MIN_RECOMMENDATIONS)
        
        # Apply full DPP kernel for diversity
        if len(scored_content) > max_results:
            candidates = [c for c, _ in scored_content[:20]]  # Top 20 candidates
            quality_scores = [s for _, s in scored_content[:20]]
            
            # DPP selection with hesitation-aware sizing
            selected_indices, dpp_log_det, confidence_uplifts = self.dpp_selector.select_diverse_recommendations(
                candidates,
                quality_scores,
                hesitation_score=enhanced_state.hesitation_score,
                base_confidence=enhanced_state.confidence_score
            )
            
            # Get marginal probabilities for all candidates
            marginals = self.dpp_selector.get_marginal_probabilities(candidates, quality_scores)
            
            diverse_selection = [
                (candidates[i], quality_scores[i]) 
                for i in selected_indices
            ]
        else:
            diverse_selection = scored_content[:max_results]
            dpp_log_det = 0.0
            confidence_uplifts = [0.0] * len(diverse_selection)
            marginals = [0.5] * len(diverse_selection)
        
        # Reorder for engagement (strong start, variety, strong end)
        optimized_sequence = self._optimize_sequence(diverse_selection)
        
        # ========== Generate Recommendations ==========
        recommendations: List[Recommendation] = []
        for idx, (content, score) in enumerate(optimized_sequence):
            micro_pitch_data = await nlp_service.generate_micro_pitch(
                content, request.user_profile, intent
            )
            
            micro_pitch = MicroPitch(
                script=micro_pitch_data["script"],
                headline=micro_pitch_data["headline"],
                hook=micro_pitch_data["hook"],
                personalized_reason=micro_pitch_data["personalized_reason"],
                standout_moment=micro_pitch_data["standout_moment"],
                fun_fact=micro_pitch_data["fun_fact"],
                call_to_action=micro_pitch_data["call_to_action"],
                estimated_duration_seconds=micro_pitch_data.get("estimated_duration_seconds", 8.0)
            )
            
            # Find original index for DPP metrics
            orig_idx = next(
                (i for i, (c, _) in enumerate(diverse_selection) if c.id == content.id),
                0
            )
            
            recommendation = Recommendation(
                content=content,
                match_score=round(score, 1),
                reasoning=self._generate_reasoning(content, request.user_profile, intent),
                micro_pitch=micro_pitch,
                sequence_position=idx,
                diversity_contribution=self._calculate_diversity_contribution(
                    content, 
                    [r.content for r in recommendations]
                ),
                # Patent-aligned DPP metrics
                quality_score=score / 100.0,  # Normalize to [0, 1]
                dpp_marginal=marginals[orig_idx] if orig_idx < len(marginals) else 0.5,
                confidence_uplift=confidence_uplifts[orig_idx] if orig_idx < len(confidence_uplifts) else 0.0
            )
            recommendations.append(recommendation)
        
        # ========== Calculate Response Metrics ==========
        processing_time = (time.time() - start_time) * 1000  # ms
        confidence = self._calculate_confidence(recommendations)
        diversity_score = self._calculate_diversity_score(recommendations)
        decision_support = self._calculate_decision_support(
            request.user_profile.decision_state, 
            len(recommendations)
        )
        
        # Generate narrative intro
        narrative_intro = nlp_service.generate_narrative_intro(intent)
        
        return RecommendationResponse(
            recommendations=recommendations,
            processing_time_ms=round(processing_time, 2),
            confidence=confidence,
            diversity_score=diversity_score,
            decision_support_score=decision_support,
            narrative_intro=narrative_intro,
            # Patent-aligned metrics
            dpp_log_det=dpp_log_det,
            hesitation_adjusted=enhanced_state.should_reduce_choices,
            optimal_set_size_used=len(recommendations),
            hazard_rate_at_generation=survival_pred.hazard_rate,
            predicted_commit_probability=enhanced_state.commit_probability
        )
    
    def _calculate_score(
        self, 
        content: Content, 
        user_profile: UserProfile, 
        intent: NLPIntent
    ) -> float:
        """Calculate multi-factor content score"""
        factors = {
            "genre_match": self._score_genre_match(content, user_profile, intent),
            "mood_match": self._score_mood_match(content, intent),
            "rating_boost": self._score_rating(content),
            "recency_boost": self._score_recency(content),
            "history_penalty": self._score_history(content, user_profile),
        }
        
        total_score = sum(
            factors[key] * self.weights[key] 
            for key in factors
        )
        
        return min(100, max(0, total_score))
    
    def _score_genre_match(
        self, 
        content: Content, 
        user_profile: UserProfile, 
        intent: NLPIntent
    ) -> float:
        """Score based on genre match with user preferences and intent"""
        score = 50  # Base score
        
        # Match against user's favorite genres
        favorite_matches = len([
            g for g in content.genre 
            if g in user_profile.preferences.favorite_genres
        ])
        score += favorite_matches * 20
        
        # Match against intent preferences
        if intent.preferences:
            intent_matches = len([
                g for g in content.genre 
                if g in intent.preferences
            ])
            score += intent_matches * 25
        
        # Penalty for disliked genres
        disliked_matches = len([
            g for g in content.genre 
            if g in user_profile.preferences.disliked_genres
        ])
        score -= disliked_matches * 30
        
        return min(100, max(0, score))
    
    def _score_mood_match(self, content: Content, intent: NLPIntent) -> float:
        """Score based on mood match with intent"""
        if not intent.mood:
            return 50
        return 100 if intent.mood in content.mood else 30
    
    def _score_rating(self, content: Content) -> float:
        """Score based on content rating"""
        return content.rating / 10 * 100
    
    def _score_recency(self, content: Content) -> float:
        """Score based on content recency"""
        current_year = datetime.now().year
        age = current_year - content.year
        
        if age <= 1:
            return 100
        elif age <= 3:
            return 80
        elif age <= 5:
            return 60
        return 40
    
    def _score_history(self, content: Content, user_profile: UserProfile) -> float:
        """Score penalty for already watched content"""
        watched_ids = {r.content_id for r in user_profile.viewing_history}
        return 0 if content.id in watched_ids else 100
    
    def _optimize_diversity(
        self, 
        scored_content: List[Tuple[Content, float]], 
        max_items: int
    ) -> List[Tuple[Content, float]]:
        """
        Apply Determinantal Point Process (DPP) inspired diversity optimization.
        Balances relevance with diversity to avoid filter bubbles.
        """
        if len(scored_content) <= max_items:
            return scored_content
        
        selected: List[Tuple[Content, float]] = []
        remaining = list(scored_content)
        
        while len(selected) < max_items and remaining:
            if not selected:
                # First item: pick highest score
                selected.append(remaining.pop(0))
                continue
            
            # For subsequent items, balance relevance with diversity
            best_idx = 0
            best_combined_score = -float('inf')
            
            for i, (candidate, score) in enumerate(remaining[:10]):  # Check top 10
                diversity_bonus = self._calculate_diversity_bonus(
                    candidate, 
                    [s[0] for s in selected]
                )
                combined_score = score * 0.7 + diversity_bonus * 0.3
                
                if combined_score > best_combined_score:
                    best_combined_score = combined_score
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        return selected
    
    def _calculate_diversity_bonus(
        self, 
        candidate: Content, 
        selected: List[Content]
    ) -> float:
        """Calculate diversity bonus for a candidate relative to selected items"""
        if not selected:
            return 0
        
        bonus = 0
        for item in selected:
            # Genre diversity
            genre_overlap = len(set(candidate.genre) & set(item.genre))
            bonus += (len(candidate.genre) - genre_overlap) * 10
            
            # Mood diversity
            mood_overlap = len(set(candidate.mood) & set(item.mood))
            bonus += (len(candidate.mood) - mood_overlap) * 10
            
            # Type diversity
            if candidate.type != item.type:
                bonus += 20
        
        return min(100, bonus / len(selected))
    
    def _optimize_sequence(
        self, 
        items: List[Tuple[Content, float]]
    ) -> List[Tuple[Content, float]]:
        """
        Optimize sequence for engagement:
        - Start strong (hook user)
        - Middle variety (maintain interest)
        - End strong (leave impression)
        """
        if len(items) <= 2:
            return items
        
        sorted_items = sorted(items, key=lambda x: x[1], reverse=True)
        
        # Start with highest score
        result = [sorted_items[0]]
        
        # Middle items (variety)
        for item in sorted_items[2:]:
            result.append(item)
        
        # End with second highest
        if len(sorted_items) > 1:
            result.append(sorted_items[1])
        
        return result
    
    def _calculate_optimal_count(self, decision_state) -> int:
        """
        Calculate optimal recommendation count based on decision state.
        Uses patent formula: n = max(2, min(5, round(5 - 3 * η)))
        
        High hesitation/stress = fewer options to reduce cognitive load.
        """
        # Use hesitation score if available (enhanced state)
        hesitation = getattr(decision_state, 'hesitation_score', None)
        
        if hesitation is not None:
            # Patent formula
            return self.dpp_selector.compute_optimal_set_size(hesitation)
        
        # Fallback to stress-based calculation
        stress = decision_state.stress_level
        
        if stress > settings.STRESS_HIGH_THRESHOLD:
            return settings.MIN_RECOMMENDATIONS  # 2 options for high stress
        elif stress > settings.STRESS_LOW_THRESHOLD:
            return 3  # Moderate options
        else:
            return settings.DEFAULT_RECOMMENDATIONS  # Normal options
    
    def _generate_reasoning(
        self, 
        content: Content, 
        user_profile: UserProfile, 
        intent: NLPIntent
    ) -> str:
        """Generate human-readable reasoning for recommendation"""
        reasons = []
        
        # Genre match reasoning
        matched_genres = [
            g for g in content.genre 
            if g in user_profile.preferences.favorite_genres or g in intent.preferences
        ]
        if matched_genres:
            reasons.append(f"matches your love for {' and '.join(matched_genres)}")
        
        # Mood match reasoning
        if intent.mood and intent.mood in content.mood:
            reasons.append(f"delivers the {intent.mood.value} experience you're looking for")
        
        # Rating reasoning
        if content.rating >= 8.5:
            reasons.append(f"critically acclaimed with a {content.rating} rating")
        
        # Theme reasoning
        if content.themes:
            reasons.append(f"explores themes of {' and '.join(content.themes[:2])}")
        
        if reasons:
            return f"This {', and '.join(reasons)}."
        return f"A highly recommended {content.type.value} that we think you'll enjoy."
    
    def _calculate_diversity_contribution(
        self, 
        content: Content, 
        previous: List[Content]
    ) -> float:
        """Calculate how much this content contributes to diversity"""
        if not previous:
            return 0
        return self._calculate_diversity_bonus(content, previous)
    
    def _calculate_confidence(self, recommendations: List[Recommendation]) -> float:
        """Calculate overall confidence in recommendations"""
        if not recommendations:
            return 0
        avg_score = sum(r.match_score for r in recommendations) / len(recommendations)
        return round(avg_score, 1)
    
    def _calculate_diversity_score(self, recommendations: List[Recommendation]) -> float:
        """Calculate diversity score for the recommendation set"""
        if len(recommendations) <= 1:
            return 100
        
        all_genres = set()
        all_moods = set()
        types = set()
        
        for r in recommendations:
            all_genres.update(r.content.genre)
            all_moods.update(r.content.mood)
            types.add(r.content.type)
        
        genre_diversity = len(all_genres) / (len(recommendations) * 2) * 100
        mood_diversity = len(all_moods) / (len(recommendations) * 2) * 100
        type_diversity = len(types) / 3 * 100
        
        return round((genre_diversity + mood_diversity + type_diversity) / 3, 1)
    
    def _calculate_decision_support(
        self, 
        decision_state, 
        num_recommendations: int
    ) -> float:
        """Calculate how well this helps reduce decision stress"""
        stress_reduction = (1 - decision_state.stress_level) * 40
        optimal_quantity = 30 if 2 <= num_recommendations <= 5 else 15
        confidence_boost = decision_state.confidence_score * 30
        
        return round(stress_reduction + optimal_quantity + confidence_boost, 1)


# Singleton instance
recommendation_engine = RecommendationEngine()
