import { NLPIntent, ContentMood } from '../types';

// Simulated NLP Processing Engine
// In production, this would use a real NLP model (GPT, BERT, etc.)

interface QueryPatterns {
  pattern: RegExp;
  intent: Partial<NLPIntent>;
}

const MOOD_KEYWORDS: Record<string, ContentMood> = {
  'exciting': 'exciting',
  'thrilling': 'thrilling',
  'action': 'exciting',
  'adventure': 'exciting',
  'relaxing': 'relaxing',
  'chill': 'relaxing',
  'calm': 'relaxing',
  'unwind': 'relaxing',
  'funny': 'comedic',
  'comedy': 'comedic',
  'laugh': 'comedic',
  'romantic': 'romantic',
  'love': 'romantic',
  'romance': 'romantic',
  'scary': 'dark',
  'horror': 'dark',
  'dark': 'dark',
  'creepy': 'dark',
  'mystery': 'mysterious',
  'mysterious': 'mysterious',
  'suspense': 'mysterious',
  'heartwarming': 'heartwarming',
  'feel good': 'heartwarming',
  'uplifting': 'uplifting',
  'inspiring': 'uplifting',
  'thought-provoking': 'thought-provoking',
  'deep': 'thought-provoking',
  'intellectual': 'thought-provoking',
};

const GENRE_KEYWORDS: Record<string, string[]> = {
  'action': ['Action', 'Thriller'],
  'drama': ['Drama'],
  'comedy': ['Comedy'],
  'horror': ['Horror', 'Psychological'],
  'sci-fi': ['Sci-Fi'],
  'scifi': ['Sci-Fi'],
  'science fiction': ['Sci-Fi'],
  'documentary': ['Documentary'],
  'doc': ['Documentary'],
  'romance': ['Romance'],
  'romantic': ['Romance'],
  'anime': ['Anime'],
  'animation': ['Anime'],
  'crime': ['Crime', 'Thriller'],
  'mystery': ['Mystery'],
  'thriller': ['Thriller'],
  'family': ['Family'],
  'nature': ['Nature', 'Documentary'],
  'space': ['Space', 'Sci-Fi'],
  'cooking': ['Cooking', 'Reality'],
  'food': ['Cooking', 'Reality'],
};

const queryPatterns: QueryPatterns[] = [
  {
    pattern: /what should i watch/i,
    intent: { action: 'recommend', context: 'general_recommendation', urgency: 'normal' }
  },
  {
    pattern: /show me something/i,
    intent: { action: 'recommend', context: 'casual_browse', urgency: 'relaxed' }
  },
  {
    pattern: /i want to (relax|chill|unwind)/i,
    intent: { action: 'recommend', context: 'relaxation', urgency: 'relaxed' }
  },
  {
    pattern: /something (exciting|thrilling|intense)/i,
    intent: { action: 'recommend', context: 'excitement', urgency: 'normal' }
  },
  {
    pattern: /surprise me/i,
    intent: { action: 'recommend', context: 'discovery', urgency: 'immediate' }
  },
  {
    pattern: /i('m| am) (bored|looking for)/i,
    intent: { action: 'recommend', context: 'engagement', urgency: 'immediate' }
  },
  {
    pattern: /find me/i,
    intent: { action: 'search', context: 'specific_search', urgency: 'normal' }
  },
  {
    pattern: /continue watching/i,
    intent: { action: 'continue', context: 'resume', urgency: 'immediate' }
  },
];

export function processNaturalLanguageQuery(query: string): NLPIntent {
  const lowerQuery = query.toLowerCase();
  
  // Default intent
  let intent: NLPIntent = {
    action: 'recommend',
    context: 'general',
    preferences: [],
    urgency: 'normal'
  };

  // Match query patterns
  for (const { pattern, intent: patternIntent } of queryPatterns) {
    if (pattern.test(query)) {
      intent = { ...intent, ...patternIntent };
      break;
    }
  }

  // Extract mood from query
  for (const [keyword, mood] of Object.entries(MOOD_KEYWORDS)) {
    if (lowerQuery.includes(keyword)) {
      intent.mood = mood;
      break;
    }
  }

  // Extract genre preferences
  const genres: string[] = [];
  for (const [keyword, genreList] of Object.entries(GENRE_KEYWORDS)) {
    if (lowerQuery.includes(keyword)) {
      genres.push(...genreList);
    }
  }
  
  if (genres.length > 0) {
    intent.preferences = [...new Set(genres)];
  }

  // Extract time-based context
  if (lowerQuery.includes('tonight') || lowerQuery.includes('this evening')) {
    intent.context = 'evening_viewing';
  } else if (lowerQuery.includes('quick') || lowerQuery.includes('short')) {
    intent.constraints = [...(intent.constraints || []), 'short_duration'];
  } else if (lowerQuery.includes('binge') || lowerQuery.includes('series')) {
    intent.constraints = [...(intent.constraints || []), 'series_preferred'];
  }

  return intent;
}

export function generateNarrativeFromIntent(intent: NLPIntent): string {
  const contextPhrases: Record<string, string> = {
    'general_recommendation': 'Based on your viewing history, I\'ve curated these picks just for you.',
    'relaxation': 'Time to unwind. Here are some perfect choices to help you relax.',
    'excitement': 'Ready for a thrill? These will get your heart racing.',
    'discovery': 'Let me surprise you with some hidden gems you might have missed.',
    'engagement': 'I\'ve found some captivating options to keep you entertained.',
    'evening_viewing': 'Perfect picks for tonight\'s viewing session.',
    'casual_browse': 'Here are some great options based on what you love.',
  };

  return contextPhrases[intent.context] || 'Here are my top recommendations for you.';
}

export function extractKeywords(query: string): string[] {
  // Simple keyword extraction (in production, use proper NLP)
  const stopWords = new Set([
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
    'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
    'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'under', 'again', 'further', 'then', 'once',
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
    'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him',
    'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its',
    'itself', 'they', 'them', 'their', 'theirs', 'themselves',
    'what', 'which', 'who', 'whom', 'this', 'that', 'these',
    'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'want', 'watch',
    'something', 'show', 'find', 'looking'
  ]);

  return query
    .toLowerCase()
    .replace(/[^\w\s]/g, '')
    .split(/\s+/)
    .filter(word => word.length > 2 && !stopWords.has(word));
}
