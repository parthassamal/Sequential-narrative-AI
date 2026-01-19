import { 
  Content, 
  UserProfile, 
  Recommendation, 
  NLPIntent, 
  RecommendationRequest, 
  RecommendationResponse,
  MicroPitch,
  ContentMood
} from '../types';
import { mockContent } from '../data/content';
import { processNaturalLanguageQuery, generateNarrativeFromIntent } from './nlpProcessor';

// Simulated AI Recommendation Engine
// Implements: Content-based filtering, collaborative filtering concepts, and sequence optimization

interface ScoringFactors {
  genreMatch: number;
  moodMatch: number;
  ratingBoost: number;
  recencyBoost: number;
  diversityPenalty: number;
  historyPenalty: number;
}

const DEFAULT_WEIGHTS: Record<keyof ScoringFactors, number> = {
  genreMatch: 0.35,
  moodMatch: 0.25,
  ratingBoost: 0.15,
  recencyBoost: 0.10,
  diversityPenalty: 0.10,
  historyPenalty: 0.05,
};

export function generateRecommendations(
  request: RecommendationRequest
): RecommendationResponse {
  const startTime = performance.now();
  
  const intent = request.query 
    ? processNaturalLanguageQuery(request.query)
    : { action: 'recommend' as const, context: 'general', preferences: [], urgency: 'normal' as const };
  
  // Score all content
  const scoredContent = mockContent
    .filter(content => !request.constraints?.excludeContentIds?.includes(content.id))
    .map(content => ({
      content,
      score: calculateContentScore(content, request.userProfile, intent)
    }))
    .sort((a, b) => b.score - a.score);

  // Apply sequence optimization (determinantal diversity)
  const maxResults = request.constraints?.maxResults || 5;
  const optimizedSequence = optimizeSequence(scoredContent, maxResults);
  
  // Generate recommendations with micro-pitches
  const recommendations: Recommendation[] = optimizedSequence.map((item, index) => ({
    content: item.content,
    matchScore: Math.round(item.score),
    reasoning: generateReasoning(item.content, request.userProfile, intent),
    microPitch: generateMicroPitch(item.content, request.userProfile, intent),
    sequencePosition: index,
    diversityContribution: calculateDiversityContribution(item.content, optimizedSequence.slice(0, index))
  }));

  const processingTime = performance.now() - startTime;
  
  return {
    recommendations,
    processingTime,
    confidence: calculateOverallConfidence(recommendations),
    diversityScore: calculateDiversityScore(recommendations),
    decisionSupportScore: calculateDecisionSupportScore(request.userProfile.decisionState, recommendations.length)
  };
}

function calculateContentScore(
  content: Content,
  userProfile: UserProfile,
  intent: NLPIntent
): number {
  const factors: ScoringFactors = {
    genreMatch: calculateGenreMatch(content, userProfile, intent),
    moodMatch: calculateMoodMatch(content, intent),
    ratingBoost: content.rating / 10 * 100,
    recencyBoost: calculateRecencyBoost(content.year),
    diversityPenalty: 0, // Applied during sequence optimization
    historyPenalty: calculateHistoryPenalty(content, userProfile)
  };

  let totalScore = 0;
  for (const [factor, value] of Object.entries(factors)) {
    totalScore += value * DEFAULT_WEIGHTS[factor as keyof ScoringFactors];
  }

  return Math.min(100, Math.max(0, totalScore));
}

function calculateGenreMatch(content: Content, userProfile: UserProfile, intent: NLPIntent): number {
  let score = 50; // Base score
  
  // Match against user's favorite genres
  const favoriteMatches = content.genre.filter(g => 
    userProfile.preferences.favoriteGenres.includes(g)
  ).length;
  score += favoriteMatches * 20;
  
  // Match against intent preferences
  if (intent.preferences.length > 0) {
    const intentMatches = content.genre.filter(g => 
      intent.preferences.includes(g)
    ).length;
    score += intentMatches * 25;
  }
  
  // Penalty for disliked genres
  const dislikedMatches = content.genre.filter(g =>
    userProfile.preferences.dislikedGenres.includes(g)
  ).length;
  score -= dislikedMatches * 30;
  
  return Math.min(100, Math.max(0, score));
}

function calculateMoodMatch(content: Content, intent: NLPIntent): number {
  if (!intent.mood) return 50;
  
  const hasMood = content.mood.includes(intent.mood);
  return hasMood ? 100 : 30;
}

function calculateRecencyBoost(year: number): number {
  const currentYear = new Date().getFullYear();
  const age = currentYear - year;
  
  if (age <= 1) return 100;
  if (age <= 3) return 80;
  if (age <= 5) return 60;
  return 40;
}

function calculateHistoryPenalty(content: Content, userProfile: UserProfile): number {
  const hasWatched = userProfile.viewingHistory.some(
    record => record.contentId === content.id
  );
  return hasWatched ? 0 : 100;
}

// Determinantal Point Process inspired sequence optimization
// Ensures diversity while maintaining relevance
function optimizeSequence(
  scoredContent: { content: Content; score: number }[],
  maxItems: number
): { content: Content; score: number }[] {
  const selected: { content: Content; score: number }[] = [];
  const remaining = [...scoredContent];
  
  while (selected.length < maxItems && remaining.length > 0) {
    // For first item, pick highest score
    if (selected.length === 0) {
      selected.push(remaining.shift()!);
      continue;
    }
    
    // For subsequent items, balance relevance with diversity
    let bestIndex = 0;
    let bestCombinedScore = -Infinity;
    
    for (let i = 0; i < Math.min(remaining.length, 10); i++) {
      const candidate = remaining[i];
      const diversityBonus = calculateDiversityBonus(candidate.content, selected);
      const combinedScore = candidate.score * 0.7 + diversityBonus * 0.3;
      
      if (combinedScore > bestCombinedScore) {
        bestCombinedScore = combinedScore;
        bestIndex = i;
      }
    }
    
    selected.push(remaining.splice(bestIndex, 1)[0]);
  }
  
  // Reorder for optimal engagement (start strong, build variety, end strong)
  return reorderForEngagement(selected);
}

function calculateDiversityBonus(candidate: Content, selected: { content: Content }[]): number {
  let bonus = 0;
  
  for (const item of selected) {
    // Genre diversity
    const genreOverlap = candidate.genre.filter(g => item.content.genre.includes(g)).length;
    bonus += (candidate.genre.length - genreOverlap) * 10;
    
    // Mood diversity
    const moodOverlap = candidate.mood.filter(m => item.content.mood.includes(m)).length;
    bonus += (candidate.mood.length - moodOverlap) * 10;
    
    // Type diversity
    if (candidate.type !== item.content.type) {
      bonus += 20;
    }
  }
  
  return Math.min(100, bonus / selected.length);
}

function reorderForEngagement(items: { content: Content; score: number }[]): { content: Content; score: number }[] {
  if (items.length <= 2) return items;
  
  // Sort by score
  const sorted = [...items].sort((a, b) => b.score - a.score);
  
  // Start with highest score (hook)
  const result = [sorted[0]];
  
  // Add middle items (variety)
  for (let i = 2; i < sorted.length; i++) {
    result.push(sorted[i]);
  }
  
  // End with second highest (strong finish)
  if (sorted.length > 1) {
    result.push(sorted[1]);
  }
  
  return result;
}

function generateReasoning(content: Content, userProfile: UserProfile, intent: NLPIntent): string {
  const reasons: string[] = [];
  
  // Genre match reasoning
  const matchedGenres = content.genre.filter(g => 
    userProfile.preferences.favoriteGenres.includes(g) || 
    intent.preferences.includes(g)
  );
  if (matchedGenres.length > 0) {
    reasons.push(`matches your love for ${matchedGenres.join(' and ')}`);
  }
  
  // Mood match reasoning
  if (intent.mood && content.mood.includes(intent.mood)) {
    reasons.push(`delivers the ${intent.mood} experience you're looking for`);
  }
  
  // Rating reasoning
  if (content.rating >= 8.5) {
    reasons.push(`critically acclaimed with a ${content.rating} rating`);
  }
  
  // Theme-based reasoning
  if (content.themes.length > 0) {
    reasons.push(`explores themes of ${content.themes.slice(0, 2).join(' and ')}`);
  }
  
  return reasons.length > 0 
    ? `This ${reasons.join(', and ')}.`
    : `A highly recommended ${content.type} that we think you'll enjoy.`;
}

function generateMicroPitch(content: Content, _userProfile: UserProfile, _intent: NLPIntent): MicroPitch {
  // Generate compelling 7-10 second micro-pitch
  const hooks = [
    `${content.title} isn't just ${content.type === 'movie' ? 'a film' : 'a show'}—it's an experience.`,
    `What if I told you ${content.title} would change how you see ${content.genre[0].toLowerCase()}?`,
    `From the moment ${content.title} begins, you won't be able to look away.`,
    `${content.title} is the ${content.genre[0].toLowerCase()} you didn't know you needed.`,
  ];
  
  const personalizedReasons = [
    `Based on your viewing history, this is exactly your kind of ${content.type}.`,
    `This matches the intensity and depth you love in your favorites.`,
    `The storytelling style here mirrors what keeps you engaged.`,
    `This has all the elements that make your top picks unforgettable.`,
  ];
  
  const callToActions = [
    `Tap to start your journey.`,
    `Ready to dive in?`,
    `Your next obsession awaits.`,
    `Press play and thank me later.`,
  ];
  
  const randomPick = <T>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)];
  
  const script = `${randomPick(hooks)} ${content.description.split('.')[0]}. ${content.funFacts[0]}. ${randomPick(callToActions)}`;
  
  return {
    script,
    headline: content.title,
    hook: randomPick(hooks),
    personalizedReason: randomPick(personalizedReasons),
    standoutMoment: content.standoutScenes[0],
    funFact: content.funFacts[0],
    callToAction: randomPick(callToActions)
  };
}

function calculateDiversityContribution(content: Content, previous: { content: Content }[]): number {
  if (previous.length === 0) return 0;
  return calculateDiversityBonus(content, previous);
}

function calculateOverallConfidence(recommendations: Recommendation[]): number {
  if (recommendations.length === 0) return 0;
  const avgScore = recommendations.reduce((sum, r) => sum + r.matchScore, 0) / recommendations.length;
  return Math.round(avgScore);
}

function calculateDiversityScore(recommendations: Recommendation[]): number {
  if (recommendations.length <= 1) return 100;
  
  const allGenres = new Set<string>();
  const allMoods = new Set<ContentMood>();
  const types = new Set<string>();
  
  recommendations.forEach(r => {
    r.content.genre.forEach(g => allGenres.add(g));
    r.content.mood.forEach(m => allMoods.add(m));
    types.add(r.content.type);
  });
  
  const genreDiversity = allGenres.size / (recommendations.length * 2) * 100;
  const moodDiversity = allMoods.size / (recommendations.length * 2) * 100;
  const typeDiversity = types.size / 3 * 100;
  
  return Math.round((genreDiversity + moodDiversity + typeDiversity) / 3);
}

function calculateDecisionSupportScore(
  decisionState: { stressLevel: number; confidenceScore: number },
  numRecommendations: number
): number {
  // Lower stress and optimal number of choices = better decision support
  const stressReduction = (1 - decisionState.stressLevel) * 40;
  const optimalQuantity = numRecommendations >= 2 && numRecommendations <= 5 ? 30 : 15;
  const confidenceBoost = decisionState.confidenceScore * 30;
  
  return Math.round(stressReduction + optimalQuantity + confidenceBoost);
}

// Export for use in components
export { generateNarrativeFromIntent };
