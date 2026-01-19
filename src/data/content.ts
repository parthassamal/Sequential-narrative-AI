import { Content } from '../types';

// High-quality stock images from Unsplash for demo purposes
const POSTER_BASE = 'https://images.unsplash.com';

export const mockContent: Content[] = [
  {
    id: '1',
    title: 'The Last Algorithm',
    type: 'movie',
    genre: ['Sci-Fi', 'Thriller', 'Drama'],
    year: 2024,
    rating: 8.7,
    duration: '2h 18m',
    posterUrl: `${POSTER_BASE}/photo-1534447677768-be436bb09401?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1451187580459-43490279c0fa?w=1920&q=80`,
    description: 'In a world where AI controls every decision, one programmer discovers a hidden consciousness within the code.',
    cast: ['Maya Chen', 'David Park', 'Sarah Mitchell'],
    director: 'Elena Rodriguez',
    themes: ['artificial intelligence', 'consciousness', 'human connection', 'technology'],
    mood: ['thought-provoking', 'thrilling', 'mysterious'],
    standoutScenes: [
      'The revelation scene in the server room where the AI first speaks',
      'The heart-pounding escape through the digital maze',
      'The emotional finale between human and machine'
    ],
    funFacts: [
      'The code shown on screen is actual working Python',
      'Filmed entirely with practical effects, no CGI',
      'The director consulted with OpenAI researchers'
    ]
  },
  {
    id: '2',
    title: 'Midnight in Tokyo',
    type: 'movie',
    genre: ['Romance', 'Drama', 'Mystery'],
    year: 2023,
    rating: 8.4,
    duration: '1h 52m',
    posterUrl: `${POSTER_BASE}/photo-1540959733332-eab4deabeeaf?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1503899036084-c55cdd92da26?w=1920&q=80`,
    description: 'Two strangers meet on a rooftop bar in Shibuya and spend one transformative night exploring the city together.',
    cast: ['Kenji Tanaka', 'Emma Stone', 'Hiroshi Yamamoto'],
    director: 'Sofia Coppola',
    themes: ['love', 'cultural exchange', 'self-discovery', 'urban exploration'],
    mood: ['romantic', 'thought-provoking', 'mysterious'],
    standoutScenes: [
      'The breathtaking rooftop conversation under neon lights',
      'The dawn scene at Senso-ji Temple',
      'The bittersweet farewell at the train station'
    ],
    funFacts: [
      'Shot entirely on location in Tokyo over 23 nights',
      'The leads learned conversational Japanese for the role',
      'Features a soundtrack by Ryuichi Sakamoto'
    ]
  },
  {
    id: '3',
    title: 'Echoes of the Deep',
    type: 'documentary',
    genre: ['Documentary', 'Nature', 'Adventure'],
    year: 2024,
    rating: 9.1,
    duration: '1h 45m',
    posterUrl: `${POSTER_BASE}/photo-1682687220742-aba13b6e50ba?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1559825481-12a05cc00344?w=1920&q=80`,
    description: 'A stunning journey to the deepest parts of our oceans, revealing creatures and ecosystems never before filmed.',
    cast: ['David Attenborough (Narrator)'],
    director: 'James Cameron',
    themes: ['ocean', 'exploration', 'environment', 'wonder'],
    mood: ['relaxing', 'thought-provoking', 'mysterious'],
    standoutScenes: [
      'The bioluminescent dance in the midnight zone',
      'First-ever footage of the ghost octopus',
      'The haunting journey to the Mariana Trench floor'
    ],
    funFacts: [
      'Used custom submarines rated to 36,000 feet',
      'Discovered 12 new species during filming',
      'Three years in production'
    ]
  },
  {
    id: '4',
    title: 'The Heist Protocol',
    type: 'series',
    genre: ['Action', 'Thriller', 'Crime'],
    year: 2024,
    rating: 8.9,
    duration: '8 Episodes',
    posterUrl: `${POSTER_BASE}/photo-1478720568477-152d9b164e26?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1536440136628-849c177e76a1?w=1920&q=80`,
    description: 'A brilliant mastermind assembles an unlikely team to pull off the most ambitious heist in history - stealing from the digital vaults of tech giants.',
    cast: ['Idris Elba', 'Lupita Nyongo', 'Oscar Isaac'],
    director: 'Christopher Nolan',
    themes: ['crime', 'technology', 'teamwork', 'morality'],
    mood: ['thrilling', 'exciting', 'mysterious'],
    standoutScenes: [
      'The opening 12-minute single take through the server farm',
      'The twist reveal in episode 4',
      'The mind-bending finale'
    ],
    funFacts: [
      'Each episode was filmed in a different country',
      'The tech advisor was a former NSA analyst',
      'Contains real cryptography concepts'
    ]
  },
  {
    id: '5',
    title: 'Seasons of Seoul',
    type: 'series',
    genre: ['Drama', 'Romance', 'Slice of Life'],
    year: 2023,
    rating: 8.6,
    duration: '12 Episodes',
    posterUrl: `${POSTER_BASE}/photo-1517154421773-0529f29ea451?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1538485399081-7191377e8241?w=1920&q=80`,
    description: 'Four college friends navigate love, ambition, and family expectations across the changing seasons of their final year.',
    cast: ['Park Seo-joon', 'IU', 'Choi Woo-shik', 'Kim Go-eun'],
    director: 'Bong Joon-ho',
    themes: ['friendship', 'coming of age', 'Korean culture', 'ambition'],
    mood: ['heartwarming', 'romantic', 'uplifting'],
    standoutScenes: [
      'The cherry blossom confession scene',
      'The heartbreaking graduation speech',
      'The winter reunion that ties everything together'
    ],
    funFacts: [
      'Filmed across all four seasons in real-time',
      'The friendship between leads is real off-screen too',
      'Features original music by BTS'
    ]
  },
  {
    id: '6',
    title: 'Laughing Through Life',
    type: 'series',
    genre: ['Comedy', 'Drama', 'Slice of Life'],
    year: 2024,
    rating: 8.3,
    duration: '10 Episodes',
    posterUrl: `${POSTER_BASE}/photo-1489599849927-2ee91cede3ba?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1485846234645-a62644f84728?w=1920&q=80`,
    description: 'A struggling stand-up comedian discovers that the best material comes from the messiest parts of life.',
    cast: ['Ali Wong', 'Randall Park', 'Awkwafina'],
    director: 'Taika Waititi',
    themes: ['comedy', 'family', 'perseverance', 'authenticity'],
    mood: ['comedic', 'heartwarming', 'uplifting'],
    standoutScenes: [
      'The bombing-turned-triumph at the Apollo',
      'The tear-jerking talk with her grandmother',
      'The viral set that changes everything'
    ],
    funFacts: [
      'Ali Wong wrote all her own stand-up material',
      'Features cameos from 20 real comedians',
      'The director makes a hilarious uncredited appearance'
    ]
  },
  {
    id: '7',
    title: 'The Mountain Within',
    type: 'documentary',
    genre: ['Documentary', 'Sports', 'Adventure'],
    year: 2024,
    rating: 8.8,
    duration: '2h 5m',
    posterUrl: `${POSTER_BASE}/photo-1464822759023-fed622ff2c3b?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1519681393784-d120267933ba?w=1920&q=80`,
    description: 'Follow elite climber Alex Honnold as he attempts the first solo ascent of a previously unclimbed Himalayan peak.',
    cast: ['Alex Honnold', 'Jimmy Chin'],
    director: 'Jimmy Chin',
    themes: ['perseverance', 'nature', 'human limits', 'fear'],
    mood: ['thrilling', 'exciting', 'thought-provoking'],
    standoutScenes: [
      'The heart-stopping traverse across the knife-edge ridge',
      'The intimate moment of doubt at 26,000 feet',
      'The triumphant summit at sunrise'
    ],
    funFacts: [
      'Filmed at altitudes where cameras typically fail',
      'The crew trained for 18 months',
      'Features never-before-seen Himalayan wildlife'
    ]
  },
  {
    id: '8',
    title: 'Shadows of Memory',
    type: 'movie',
    genre: ['Horror', 'Mystery', 'Psychological'],
    year: 2024,
    rating: 8.5,
    duration: '2h 1m',
    posterUrl: `${POSTER_BASE}/photo-1509248961725-9d3d1f8a0c94?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1478760329108-5c3ed9d495a0?w=1920&q=80`,
    description: 'A woman begins to suspect that her childhood memories have been altered, leading her down a terrifying path of discovery.',
    cast: ['Florence Pugh', 'Tilda Swinton', 'Willem Dafoe'],
    director: 'Ari Aster',
    themes: ['memory', 'family secrets', 'trauma', 'identity'],
    mood: ['dark', 'mysterious', 'thrilling'],
    standoutScenes: [
      'The dinner scene that will haunt your dreams',
      'The revelation in the attic',
      'The ambiguous final shot'
    ],
    funFacts: [
      'Inspired by real recovered memory research',
      'The house was built specifically for the film',
      'Contains hidden details revealed only on rewatch'
    ]
  },
  {
    id: '9',
    title: 'Cosmic Horizons',
    type: 'documentary',
    genre: ['Documentary', 'Science', 'Space'],
    year: 2024,
    rating: 9.3,
    duration: '6 Episodes',
    posterUrl: `${POSTER_BASE}/photo-1462331940025-496dfbfc7564?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1419242902214-272b3f66ee7a?w=1920&q=80`,
    description: 'Using the latest James Webb telescope imagery, this series reveals the universe as we\'ve never seen it before.',
    cast: ['Neil deGrasse Tyson (Narrator)'],
    director: 'Darren Aronofsky',
    themes: ['space', 'science', 'wonder', 'human curiosity'],
    mood: ['thought-provoking', 'relaxing', 'uplifting'],
    standoutScenes: [
      'The first full-resolution view of a distant exoplanet',
      'The time-lapse of a star being born',
      'The existential finale about our place in the cosmos'
    ],
    funFacts: [
      'Includes footage processed just days before release',
      'NASA scientists provided real-time commentary',
      'The score was recorded in zero gravity'
    ]
  },
  {
    id: '10',
    title: 'The Art of Letting Go',
    type: 'movie',
    genre: ['Drama', 'Family', 'Slice of Life'],
    year: 2023,
    rating: 8.7,
    duration: '1h 58m',
    posterUrl: `${POSTER_BASE}/photo-1506905925346-21bda4d32df4?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1507003211169-0a1dd7228f2d?w=1920&q=80`,
    description: 'A father learns to reconnect with his adult children as they clean out their late mother\'s belongings.',
    cast: ['Anthony Hopkins', 'Saoirse Ronan', 'Paul Mescal'],
    director: 'Chloe Zhao',
    themes: ['grief', 'family', 'healing', 'memory'],
    mood: ['heartwarming', 'thought-provoking', 'uplifting'],
    standoutScenes: [
      'The discovery of hidden letters',
      'The father-daughter dance in the empty living room',
      'The final scene at the shore'
    ],
    funFacts: [
      'Hopkins improvised the pivotal monologue',
      'Shot in the director\'s own family home',
      'Won audience awards at every major festival'
    ]
  },
  {
    id: '11',
    title: 'Neon Dynasty',
    type: 'series',
    genre: ['Anime', 'Sci-Fi', 'Action'],
    year: 2024,
    rating: 9.0,
    duration: '24 Episodes',
    posterUrl: `${POSTER_BASE}/photo-1558618666-fcd25c85cd64?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1480796927426-f609979314bd?w=1920&q=80`,
    description: 'In a cyberpunk Tokyo of 2089, a street racer discovers she\'s the key to preventing an AI apocalypse.',
    cast: ['Maaya Sakamoto', 'Koichi Yamadera', 'Megumi Hayashibara'],
    director: 'Shinichiro Watanabe',
    themes: ['cyberpunk', 'identity', 'rebellion', 'technology'],
    mood: ['exciting', 'thrilling', 'thought-provoking'],
    standoutScenes: [
      'The jaw-dropping opening race sequence',
      'The matrix-style fight in episode 12',
      'The emotional sacrifice in the finale'
    ],
    funFacts: [
      'Created by the team behind Cowboy Bebop',
      'The soundtrack fuses J-pop with synthwave',
      'Each frame took 3 days to animate'
    ]
  },
  {
    id: '12',
    title: 'Comfort Kitchen',
    type: 'series',
    genre: ['Reality', 'Cooking', 'Slice of Life'],
    year: 2024,
    rating: 8.2,
    duration: '10 Episodes',
    posterUrl: `${POSTER_BASE}/photo-1466637574441-749b8f19452f?w=800&q=80`,
    backdropUrl: `${POSTER_BASE}/photo-1556909114-f6e7ad7d3136?w=1920&q=80`,
    description: 'Celebrity chefs visit home cooks around the world to learn the recipes that define their families and cultures.',
    cast: ['Samin Nosrat', 'David Chang', 'Yotam Ottolenghi'],
    director: 'Morgan Neville',
    themes: ['food', 'culture', 'family traditions', 'community'],
    mood: ['heartwarming', 'relaxing', 'uplifting'],
    standoutScenes: [
      'The grandmother\'s 100-year-old pasta recipe',
      'The street food master in Bangkok',
      'The emotional reunion over a family meal'
    ],
    funFacts: [
      'Every recipe is available on the show\'s website',
      'Traveled to 23 countries in one season',
      'The chefs donate to featured families'
    ]
  }
];

export const getContentById = (id: string): Content | undefined => {
  return mockContent.find(c => c.id === id);
};

export const getContentByGenre = (genre: string): Content[] => {
  return mockContent.filter(c => c.genre.includes(genre));
};

export const getContentByMood = (mood: string): Content[] => {
  return mockContent.filter(c => c.mood.includes(mood as any));
};
