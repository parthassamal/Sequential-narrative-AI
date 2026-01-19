"""
NLP Service for Sequential Narrative AI
Handles natural language processing of user queries and narrative generation.
Supports both local processing and AI integration (OpenRouter/OpenAI).
"""
import re
from typing import Dict, List, Optional, Tuple
from app.models import NLPIntent, IntentAction, ContentMood, Content, UserProfile
from app.config import settings
from app.services.ai_client import ai_client

# Mood keyword mappings
MOOD_KEYWORDS: Dict[str, ContentMood] = {
    "exciting": ContentMood.EXCITING,
    "thrilling": ContentMood.THRILLING,
    "action": ContentMood.EXCITING,
    "adventure": ContentMood.EXCITING,
    "relaxing": ContentMood.RELAXING,
    "chill": ContentMood.RELAXING,
    "calm": ContentMood.RELAXING,
    "unwind": ContentMood.RELAXING,
    "funny": ContentMood.COMEDIC,
    "comedy": ContentMood.COMEDIC,
    "laugh": ContentMood.COMEDIC,
    "hilarious": ContentMood.COMEDIC,
    "romantic": ContentMood.ROMANTIC,
    "love": ContentMood.ROMANTIC,
    "romance": ContentMood.ROMANTIC,
    "scary": ContentMood.DARK,
    "horror": ContentMood.DARK,
    "dark": ContentMood.DARK,
    "creepy": ContentMood.DARK,
    "mystery": ContentMood.MYSTERIOUS,
    "mysterious": ContentMood.MYSTERIOUS,
    "suspense": ContentMood.MYSTERIOUS,
    "heartwarming": ContentMood.HEARTWARMING,
    "feel good": ContentMood.HEARTWARMING,
    "wholesome": ContentMood.HEARTWARMING,
    "uplifting": ContentMood.UPLIFTING,
    "inspiring": ContentMood.UPLIFTING,
    "motivating": ContentMood.UPLIFTING,
    "thought-provoking": ContentMood.THOUGHT_PROVOKING,
    "deep": ContentMood.THOUGHT_PROVOKING,
    "intellectual": ContentMood.THOUGHT_PROVOKING,
    "mind-bending": ContentMood.THOUGHT_PROVOKING,
}

# Genre keyword mappings
GENRE_KEYWORDS: Dict[str, List[str]] = {
    "action": ["Action", "Thriller"],
    "drama": ["Drama"],
    "comedy": ["Comedy"],
    "horror": ["Horror", "Psychological"],
    "sci-fi": ["Sci-Fi"],
    "scifi": ["Sci-Fi"],
    "science fiction": ["Sci-Fi"],
    "documentary": ["Documentary"],
    "doc": ["Documentary"],
    "romance": ["Romance"],
    "romantic": ["Romance"],
    "anime": ["Anime"],
    "animation": ["Anime"],
    "crime": ["Crime", "Thriller"],
    "mystery": ["Mystery"],
    "thriller": ["Thriller"],
    "family": ["Family"],
    "nature": ["Nature", "Documentary"],
    "space": ["Space", "Sci-Fi"],
    "cooking": ["Cooking", "Reality"],
    "food": ["Cooking", "Reality"],
    "sports": ["Sports"],
    "adventure": ["Adventure"],
}

# Query patterns for intent detection
QUERY_PATTERNS: List[Tuple[str, Dict]] = [
    (r"what should i watch", {"action": IntentAction.RECOMMEND, "context": "general_recommendation", "urgency": "normal"}),
    (r"show me something", {"action": IntentAction.RECOMMEND, "context": "casual_browse", "urgency": "relaxed"}),
    (r"i want to (relax|chill|unwind)", {"action": IntentAction.RECOMMEND, "context": "relaxation", "urgency": "relaxed"}),
    (r"something (exciting|thrilling|intense)", {"action": IntentAction.RECOMMEND, "context": "excitement", "urgency": "normal"}),
    (r"surprise me", {"action": IntentAction.RECOMMEND, "context": "discovery", "urgency": "immediate"}),
    (r"i('m| am) (bored|looking for)", {"action": IntentAction.RECOMMEND, "context": "engagement", "urgency": "immediate"}),
    (r"find me", {"action": IntentAction.SEARCH, "context": "specific_search", "urgency": "normal"}),
    (r"search for", {"action": IntentAction.SEARCH, "context": "specific_search", "urgency": "normal"}),
    (r"continue watching", {"action": IntentAction.CONTINUE, "context": "resume", "urgency": "immediate"}),
    (r"what's new", {"action": IntentAction.EXPLORE, "context": "new_releases", "urgency": "relaxed"}),
    (r"recommend", {"action": IntentAction.RECOMMEND, "context": "explicit_request", "urgency": "normal"}),
]

# Context-based narrative templates
NARRATIVE_TEMPLATES: Dict[str, str] = {
    "general_recommendation": "Based on your viewing history, I've curated these picks just for you.",
    "relaxation": "Time to unwind. Here are some perfect choices to help you relax.",
    "excitement": "Ready for a thrill? These will get your heart racing.",
    "discovery": "Let me surprise you with some hidden gems you might have missed.",
    "engagement": "I've found some captivating options to keep you entertained.",
    "evening_viewing": "Perfect picks for tonight's viewing session.",
    "casual_browse": "Here are some great options based on what you love.",
    "specific_search": "Here's what I found that matches your request.",
    "new_releases": "Fresh content just added that you might enjoy.",
    "explicit_request": "Here are my top recommendations for you.",
    "resume": "Ready to pick up where you left off?",
}


class NLPService:
    """Natural Language Processing service for query understanding and narrative generation"""
    
    def __init__(self):
        self.ai_enabled = ai_client.is_available
    
    async def process_query(self, query: str, user_context: Optional[dict] = None) -> NLPIntent:
        """
        Process a natural language query and extract structured intent.
        
        Args:
            query: The user's natural language query
            user_context: Optional context about the user's current state
            
        Returns:
            NLPIntent with extracted action, context, preferences, and mood
        """
        lower_query = query.lower().strip()
        
        # Initialize default intent
        intent = NLPIntent(
            action=IntentAction.RECOMMEND,
            context="general",
            preferences=[],
            mood=None,
            urgency="normal",
            constraints=[],
            raw_query=query,
            confidence=0.8
        )
        
        # Match query patterns
        for pattern, intent_updates in QUERY_PATTERNS:
            if re.search(pattern, lower_query, re.IGNORECASE):
                intent.action = intent_updates.get("action", intent.action)
                intent.context = intent_updates.get("context", intent.context)
                intent.urgency = intent_updates.get("urgency", intent.urgency)
                intent.confidence = 0.9
                break
        
        # Extract mood from query
        for keyword, mood in MOOD_KEYWORDS.items():
            if keyword in lower_query:
                intent.mood = mood
                intent.confidence = min(intent.confidence + 0.05, 1.0)
                break
        
        # Extract genre preferences
        genres: List[str] = []
        for keyword, genre_list in GENRE_KEYWORDS.items():
            if keyword in lower_query:
                genres.extend(genre_list)
        intent.preferences = list(set(genres))
        
        # Extract time-based context
        if "tonight" in lower_query or "this evening" in lower_query:
            intent.context = "evening_viewing"
        elif "quick" in lower_query or "short" in lower_query:
            intent.constraints.append("short_duration")
        elif "binge" in lower_query or "series" in lower_query:
            intent.constraints.append("series_preferred")
        elif "movie" in lower_query or "film" in lower_query:
            intent.constraints.append("movie_preferred")
        
        # If AI is available and confidence is low, use it for better understanding
        if self.ai_enabled and intent.confidence < 0.7:
            enhanced_intent = await self._enhance_with_ai(query, intent)
            if enhanced_intent:
                intent = enhanced_intent
        
        return intent
    
    async def _enhance_with_ai(self, query: str, base_intent: NLPIntent) -> Optional[NLPIntent]:
        """Use AI (OpenRouter/OpenAI) to enhance intent understanding for complex queries"""
        try:
            result = await ai_client.generate_json(
                system_prompt="""You are an NLP intent parser for a streaming recommendation system.
                Extract the user's intent from their query and return JSON with:
                - action: "recommend", "search", "explore", or "continue"
                - context: brief description of what they're looking for
                - mood: one of "thrilling", "heartwarming", "thought-provoking", "relaxing", "exciting", "dark", "uplifting", "mysterious", "romantic", "comedic" or null
                - preferences: list of genres they might want
                - urgency: "relaxed", "normal", or "immediate"
                """,
                user_prompt=query,
                max_tokens=200
            )
            
            if not result:
                return None
            
            return NLPIntent(
                action=IntentAction(result.get("action", "recommend")),
                context=result.get("context", base_intent.context),
                preferences=result.get("preferences", base_intent.preferences),
                mood=ContentMood(result["mood"]) if result.get("mood") else None,
                urgency=result.get("urgency", "normal"),
                constraints=base_intent.constraints,
                raw_query=query,
                confidence=0.95
            )
        except Exception as e:
            print(f"AI enhancement failed: {e}")
            return None
    
    def generate_narrative_intro(self, intent: NLPIntent) -> str:
        """Generate a narrative introduction based on the parsed intent"""
        return NARRATIVE_TEMPLATES.get(intent.context, "Here are my top recommendations for you.")
    
    async def generate_micro_pitch(
        self, 
        content: Content, 
        user_profile: Optional[UserProfile] = None,
        intent: Optional[NLPIntent] = None
    ) -> dict:
        """
        Generate a 7-10 second micro-pitch for a content item.
        
        Args:
            content: The content to generate a pitch for
            user_profile: Optional user profile for personalization
            intent: Optional parsed intent for context
            
        Returns:
            Dictionary with micro-pitch components
        """
        # Generate using templates (fast, works offline)
        pitch = self._generate_template_pitch(content, user_profile, intent)
        
        # If AI is available, enhance with AI-generated content
        if self.ai_enabled:
            enhanced = await self._enhance_pitch_with_ai(content, user_profile, intent)
            if enhanced:
                pitch = enhanced
        
        return pitch
    
    def _generate_template_pitch(
        self, 
        content: Content, 
        user_profile: Optional[UserProfile],
        intent: Optional[NLPIntent]
    ) -> dict:
        """Generate a micro-pitch using templates (kept short for 7-10 seconds)"""
        import random
        
        # Varied opening hooks - never repetitive
        genre = content.genre[0].lower() if content.genre else "story"
        hooks = [
            f"Ever wonder what a perfect {genre} looks like? This is it.",
            f"Here's something special. {content.title}.",
            f"You'll want to clear your schedule for this one.",
            f"Trust me on {content.title}. It's worth every minute.",
            f"What if I told you this {content.type.value} has everything you love?",
            f"{content.title} is quietly one of the best out there.",
            f"I've got something good. Real good.",
            f"This might just become your new favorite.",
            f"Let me tell you about {content.title}.",
            f"Picture this, your perfect {genre}. Found it.",
        ]
        
        personalized_reasons = [
            f"It's exactly what you're looking for right now.",
            f"This matches your taste perfectly.",
            f"The vibe? Just right for you.",
            f"It hits all the right notes.",
            f"Made for someone with your taste.",
        ]
        
        call_to_actions = [
            "Give it a shot.",
            "You won't regret it.",
            "Start watching now.",
            "Go ahead, press play.",
            "Your call.",
        ]
        
        hook = random.choice(hooks)
        personalized = random.choice(personalized_reasons)
        cta = random.choice(call_to_actions)
        fun_fact = content.fun_facts[0] if content.fun_facts else ""
        
        # Keep script short and conversational
        if fun_fact:
            script = f"{hook} {fun_fact[:40]}. {cta}"
        else:
            script = f"{hook} {personalized} {cta}"
        
        return {
            "script": script,
            "headline": content.title,
            "hook": hook,
            "personalized_reason": personalized,
            "standout_moment": content.standout_scenes[0] if content.standout_scenes else "",
            "fun_fact": fun_fact,
            "call_to_action": cta,
            "estimated_duration_seconds": min(12.0, len(script.split()) / 2.5)
        }
    
    async def _enhance_pitch_with_ai(
        self, 
        content: Content,
        user_profile: Optional[UserProfile],
        intent: Optional[NLPIntent]
    ) -> Optional[dict]:
        """Generate an enhanced micro-pitch using AI (OpenRouter/OpenAI)"""
        try:
            user_context = ""
            if user_profile:
                genres = ", ".join(user_profile.preferences.favorite_genres[:3])
                moods = ", ".join([m.value for m in user_profile.preferences.preferred_moods[:3]])
                user_context = f"The user enjoys {genres} and prefers {moods} content."
            
            mood_context = ""
            if intent and intent.mood:
                mood_context = f"They're currently looking for something {intent.mood.value}."
            
            result = await ai_client.generate_json(
                system_prompt=f"""You are a creative, witty writer for a streaming platform. 
                Generate a compelling 7-10 second micro-pitch for content recommendations.
                {user_context} {mood_context}
                
                IMPORTANT RULES:
                - NEVER start with "Get ready", "Prepare yourself", "Buckle up", or similar clichés
                - Start with something unique: a question, a bold statement, or an intriguing fact
                - Be conversational like you're talking to a friend
                - Each pitch should feel fresh and different
                - Keep it under 25 words total
                - Use natural, flowing language that sounds good when spoken aloud
                
                Vary your openings with approaches like:
                - A surprising question
                - A bold claim about the content
                - An intriguing fact or statistic
                - A relatable scenario
                - A direct "You'll love this because..." statement
                
                Return JSON with: script, hook, personalized_reason, standout_moment, fun_fact, call_to_action""",
                user_prompt=f"""Generate a micro-pitch for:
                Title: {content.title}
                Type: {content.type.value}
                Genre: {', '.join(content.genre)}
                Description: {content.description}
                Rating: {content.rating}/10
                Standout scenes: {content.standout_scenes[0] if content.standout_scenes else 'N/A'}
                Fun facts: {content.fun_facts[0] if content.fun_facts else 'N/A'}""",
                max_tokens=300
            )
            
            if not result:
                return None
            
            # Truncate script if too long (keep under 25 words for ~10 seconds)
            script = result.get("script", "")
            words = script.split()
            if len(words) > 25:
                script = " ".join(words[:25]) + "..."
                result["script"] = script
                
            result["headline"] = content.title
            result["estimated_duration_seconds"] = min(12.0, len(script.split()) / 2.5)
            
            return result
        except Exception as e:
            print(f"AI pitch generation failed: {e}")
            return None
    
    def get_suggested_prompts(self, intent: NLPIntent) -> List[str]:
        """Generate follow-up prompt suggestions based on the current intent"""
        base_prompts = [
            "What should I watch?",
            "Show me something exciting",
            "I want to relax",
            "Surprise me",
        ]
        
        # Add context-specific prompts
        if intent.mood == ContentMood.THRILLING:
            base_prompts.extend([
                "Something even more intense",
                "More action-packed content",
            ])
        elif intent.mood == ContentMood.RELAXING:
            base_prompts.extend([
                "Something light and easy",
                "A feel-good documentary",
            ])
        
        return base_prompts[:6]


# Singleton instance
nlp_service = NLPService()
