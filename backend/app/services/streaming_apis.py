"""
Streaming Service API Integrations
Connects to real streaming platforms for content data.
"""
import httpx
import os
from typing import Optional
from abc import ABC, abstractmethod

from app.config import settings


class StreamingProvider(ABC):
    """Base class for streaming service integrations"""
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        pass
    
    @abstractmethod
    async def get_trending(self, limit: int = 20) -> list[dict]:
        pass
    
    @abstractmethod
    async def get_details(self, content_id: str) -> Optional[dict]:
        pass


class TMDbProvider(StreamingProvider):
    """
    The Movie Database (TMDb) API Integration
    Free API with 100K+ movies and TV shows
    Sign up at: https://www.themoviedb.org/settings/api
    """
    
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("TMDB_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=10.0, verify=False)
    
    def _transform_movie(self, movie: dict) -> dict:
        """Transform TMDb movie to our format"""
        return {
            "id": f"tmdb_movie_{movie['id']}",
            "external_id": movie["id"],
            "title": movie.get("title", "Unknown"),
            "type": "movie",
            "genre": self._get_genre_names(movie.get("genre_ids", [])),
            "year": int(movie.get("release_date", "0000")[:4]) if movie.get("release_date") else 0,
            "rating": round(movie.get("vote_average", 0), 1),
            "duration": "2h",  # TMDb doesn't include runtime in search
            "poster_url": f"{self.IMAGE_BASE}/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "backdrop_url": f"{self.IMAGE_BASE}/w1280{movie['backdrop_path']}" if movie.get("backdrop_path") else None,
            "description": movie.get("overview", ""),
            "provider": "tmdb",
            "popularity": movie.get("popularity", 0),
        }
    
    def _transform_tv(self, show: dict) -> dict:
        """Transform TMDb TV show to our format"""
        return {
            "id": f"tmdb_tv_{show['id']}",
            "external_id": show["id"],
            "title": show.get("name", "Unknown"),
            "type": "series",
            "genre": self._get_genre_names(show.get("genre_ids", [])),
            "year": int(show.get("first_air_date", "0000")[:4]) if show.get("first_air_date") else 0,
            "rating": round(show.get("vote_average", 0), 1),
            "duration": "Series",
            "poster_url": f"{self.IMAGE_BASE}/w500{show['poster_path']}" if show.get("poster_path") else None,
            "backdrop_url": f"{self.IMAGE_BASE}/w1280{show['backdrop_path']}" if show.get("backdrop_path") else None,
            "description": show.get("overview", ""),
            "provider": "tmdb",
            "popularity": show.get("popularity", 0),
        }
    
    def _get_genre_names(self, genre_ids: list[int]) -> list[str]:
        """Map TMDb genre IDs to names"""
        genre_map = {
            28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
            80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
            14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
            9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie",
            53: "Thriller", 10752: "War", 37: "Western",
            10759: "Action & Adventure", 10762: "Kids", 10763: "News",
            10764: "Reality", 10765: "Sci-Fi & Fantasy", 10766: "Soap",
            10767: "Talk", 10768: "War & Politics"
        }
        return [genre_map.get(gid, "Other") for gid in genre_ids if gid in genre_map]
    
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search for movies and TV shows"""
        if not self.api_key:
            return []
        
        results = []
        try:
            # Search movies
            response = await self.client.get(
                f"{self.BASE_URL}/search/movie",
                params={"api_key": self.api_key, "query": query, "page": 1}
            )
            if response.status_code == 200:
                data = response.json()
                results.extend([self._transform_movie(m) for m in data.get("results", [])[:limit//2]])
            
            # Search TV shows
            response = await self.client.get(
                f"{self.BASE_URL}/search/tv",
                params={"api_key": self.api_key, "query": query, "page": 1}
            )
            if response.status_code == 200:
                data = response.json()
                results.extend([self._transform_tv(s) for s in data.get("results", [])[:limit//2]])
        except Exception as e:
            print(f"TMDb search error: {e}")
        
        return results[:limit]
    
    async def get_trending(self, limit: int = 20) -> list[dict]:
        """Get trending movies and TV shows"""
        if not self.api_key:
            return []
        
        results = []
        try:
            # Trending movies
            response = await self.client.get(
                f"{self.BASE_URL}/trending/movie/week",
                params={"api_key": self.api_key}
            )
            if response.status_code == 200:
                data = response.json()
                results.extend([self._transform_movie(m) for m in data.get("results", [])[:limit//2]])
            
            # Trending TV
            response = await self.client.get(
                f"{self.BASE_URL}/trending/tv/week",
                params={"api_key": self.api_key}
            )
            if response.status_code == 200:
                data = response.json()
                results.extend([self._transform_tv(s) for s in data.get("results", [])[:limit//2]])
        except Exception as e:
            print(f"TMDb trending error: {e}")
        
        return results[:limit]
    
    async def get_details(self, content_id: str) -> Optional[dict]:
        """Get detailed info for a specific item"""
        if not self.api_key:
            return None
        
        try:
            parts = content_id.split("_")
            media_type = parts[1]  # movie or tv
            tmdb_id = parts[2]
            
            response = await self.client.get(
                f"{self.BASE_URL}/{media_type}/{tmdb_id}",
                params={"api_key": self.api_key, "append_to_response": "credits,videos"}
            )
            if response.status_code == 200:
                data = response.json()
                if media_type == "movie":
                    result = self._transform_movie(data)
                    result["duration"] = f"{data.get('runtime', 120)}m"
                    result["cast"] = [c["name"] for c in data.get("credits", {}).get("cast", [])[:5]]
                    result["director"] = next(
                        (c["name"] for c in data.get("credits", {}).get("crew", []) if c["job"] == "Director"),
                        "Unknown"
                    )
                else:
                    result = self._transform_tv(data)
                    result["duration"] = f"{data.get('number_of_seasons', 1)} Seasons"
                    result["cast"] = [c["name"] for c in data.get("credits", {}).get("cast", [])[:5]]
                return result
        except Exception as e:
            print(f"TMDb details error: {e}")
        
        return None


class YouTubeProvider(StreamingProvider):
    """
    YouTube Data API Integration
    Get API key at: https://console.cloud.google.com/apis/credentials
    Enable: YouTube Data API v3
    """
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=10.0, verify=False)
    
    def _transform_video(self, video: dict, details: dict = None) -> dict:
        """Transform YouTube video to our format"""
        snippet = video.get("snippet", {})
        statistics = details.get("statistics", {}) if details else {}
        content_details = details.get("contentDetails", {}) if details else {}
        
        # Parse duration (ISO 8601 to human readable)
        duration = self._parse_duration(content_details.get("duration", "PT0M"))
        
        # Handle both search results (id is object) and video list (id is string)
        video_id_raw = video.get("id", "")
        if isinstance(video_id_raw, dict):
            video_id = video_id_raw.get("videoId", "")
        else:
            video_id = video_id_raw
        
        return {
            "id": f"youtube_{video_id}",
            "external_id": video_id,
            "title": snippet.get("title", "Unknown"),
            "type": "video",
            "genre": ["YouTube"],
            "year": int(snippet.get("publishedAt", "0000")[:4]) if snippet.get("publishedAt") else 0,
            "rating": self._calculate_rating(statistics),
            "duration": duration,
            "poster_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "backdrop_url": snippet.get("thumbnails", {}).get("maxres", snippet.get("thumbnails", {}).get("high", {})).get("url"),
            "description": snippet.get("description", "")[:500],
            "provider": "youtube",
            "channel": snippet.get("channelTitle", ""),
            "view_count": int(statistics.get("viewCount", 0)),
            "watch_url": f"https://www.youtube.com/watch?v={video_id}"
        }
    
    def _parse_duration(self, iso_duration: str) -> str:
        """Parse ISO 8601 duration to human readable"""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
        if not match:
            return "0:00"
        hours, minutes, seconds = match.groups()
        hours = int(hours or 0)
        minutes = int(minutes or 0)
        seconds = int(seconds or 0)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m {seconds}s"
    
    def _calculate_rating(self, statistics: dict) -> float:
        """Calculate rating from likes/views"""
        likes = int(statistics.get("likeCount", 0))
        views = int(statistics.get("viewCount", 1))
        if views == 0:
            return 5.0
        # Simple engagement-based rating
        engagement = (likes / views) * 100
        return min(10.0, round(5.0 + engagement * 50, 1))
    
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search YouTube videos"""
        if not self.api_key:
            return []
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/search",
                params={
                    "key": self.api_key,
                    "q": query,
                    "part": "snippet",
                    "type": "video",
                    "maxResults": limit,
                    "videoDuration": "medium",  # 4-20 minutes
                    "videoDefinition": "high"
                }
            )
            if response.status_code == 200:
                data = response.json()
                videos = data.get("items", [])
                
                # Get detailed stats for each video
                if videos:
                    video_ids = ",".join([v["id"]["videoId"] for v in videos])
                    details_response = await self.client.get(
                        f"{self.BASE_URL}/videos",
                        params={
                            "key": self.api_key,
                            "id": video_ids,
                            "part": "statistics,contentDetails"
                        }
                    )
                    details_map = {}
                    if details_response.status_code == 200:
                        for item in details_response.json().get("items", []):
                            details_map[item["id"]] = item
                    
                    return [
                        self._transform_video(v, details_map.get(v["id"]["videoId"]))
                        for v in videos
                    ]
                return [self._transform_video(v) for v in videos]
        except Exception as e:
            print(f"YouTube search error: {e}")
        
        return []
    
    async def get_trending(self, limit: int = 20) -> list[dict]:
        """Get trending YouTube videos"""
        if not self.api_key:
            return []
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/videos",
                params={
                    "key": self.api_key,
                    "part": "snippet,statistics,contentDetails",
                    "chart": "mostPopular",
                    "regionCode": "US",
                    "maxResults": limit
                }
            )
            if response.status_code == 200:
                data = response.json()
                return [self._transform_video({"id": v["id"], "snippet": v["snippet"]}, v) 
                        for v in data.get("items", [])]
        except Exception as e:
            print(f"YouTube trending error: {e}")
        
        return []
    
    async def get_details(self, content_id: str) -> Optional[dict]:
        """Get detailed info for a YouTube video"""
        if not self.api_key:
            return None
        
        try:
            video_id = content_id.replace("youtube_", "")
            response = await self.client.get(
                f"{self.BASE_URL}/videos",
                params={
                    "key": self.api_key,
                    "id": video_id,
                    "part": "snippet,statistics,contentDetails"
                }
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items:
                    item = items[0]
                    return self._transform_video({"id": item["id"], "snippet": item["snippet"]}, item)
        except Exception as e:
            print(f"YouTube details error: {e}")
        
        return None


class ParamountPlusProvider(StreamingProvider):
    """
    Paramount+ API Integration (Enterprise/Partner Only)
    
    NOTE: This is a placeholder implementation.
    Real integration requires:
    1. Enterprise partnership agreement with Paramount
    2. API credentials and whitelisting
    3. OAuth 2.0 authentication for user data
    4. Content licensing agreement
    
    Contact: https://www.paramount.com/partner
    """
    
    BASE_URL = "https://api.paramountplus.com/v1"  # Hypothetical
    
    def __init__(self, api_key: str = None, client_id: str = None, client_secret: str = None):
        self.api_key = api_key or os.getenv("PARAMOUNT_API_KEY", "")
        self.client_id = client_id or os.getenv("PARAMOUNT_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("PARAMOUNT_CLIENT_SECRET", "")
        self.client = httpx.AsyncClient(timeout=10.0)
        self._access_token = None
    
    async def _authenticate(self) -> bool:
        """
        OAuth 2.0 authentication flow for Paramount+ API
        This would be implemented when real credentials are available
        """
        if not self.client_id or not self.client_secret:
            return False
        
        # Placeholder - real implementation would:
        # 1. Call /oauth/token with client credentials
        # 2. Store access_token and refresh_token
        # 3. Handle token refresh
        return False
    
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search Paramount+ catalog
        
        Real endpoint would be something like:
        GET /content/search?q={query}&limit={limit}
        Headers: Authorization: Bearer {access_token}
        """
        if not self.api_key:
            # Return mock data for demo
            return self._get_mock_paramount_content(query, limit)
        
        # Real implementation placeholder
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/content/search",
                params={"q": query, "limit": limit},
                headers={"Authorization": f"Bearer {self._access_token}"}
            )
            if response.status_code == 200:
                return self._transform_results(response.json())
        except Exception as e:
            print(f"Paramount+ API error: {e}")
        
        return []
    
    async def get_trending(self, limit: int = 20) -> list[dict]:
        """Get trending content on Paramount+"""
        if not self.api_key:
            return self._get_mock_paramount_content("trending", limit)
        
        return []
    
    async def get_details(self, content_id: str) -> Optional[dict]:
        """Get content details from Paramount+"""
        return None
    
    def _get_mock_paramount_content(self, query: str, limit: int) -> list[dict]:
        """Mock Paramount+ content for demo purposes - QUERY AWARE"""
        # Extended catalog with genre tags for query matching
        mock_catalog = [
            # Horror / Thriller
            {
                "id": "paramount_horror_1",
                "title": "Scream VI",
                "type": "movie",
                "genre": ["Horror", "Thriller", "Mystery"],
                "year": 2023,
                "rating": 7.0,
                "duration": "2h 3m",
                "poster_url": "https://images.unsplash.com/photo-1509248961895-b4c5ee5eb1d4?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1509248961895-b4c5ee5eb1d4?w=1280",
                "description": "The survivors of the Ghostface killings leave Woodsboro behind for a fresh start in New York City.",
                "provider": "paramount",
                "keywords": ["horror", "scary", "thriller", "slasher", "scream", "ghost"]
            },
            {
                "id": "paramount_horror_2",
                "title": "A Quiet Place: Day One",
                "type": "movie",
                "genre": ["Horror", "Sci-Fi", "Thriller"],
                "year": 2024,
                "rating": 7.5,
                "duration": "1h 39m",
                "poster_url": "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?w=1280",
                "description": "Experience the day the world went quiet in this terrifying prequel.",
                "provider": "paramount",
                "keywords": ["horror", "scary", "quiet", "thriller", "alien", "survival"]
            },
            {
                "id": "paramount_horror_3",
                "title": "Evil Dead Rise",
                "type": "movie",
                "genre": ["Horror"],
                "year": 2023,
                "rating": 6.9,
                "duration": "1h 36m",
                "poster_url": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1280",
                "description": "A twisted tale of two estranged sisters whose reunion is cut short by the discovery of a mysterious book.",
                "provider": "paramount",
                "keywords": ["horror", "scary", "evil", "demon", "supernatural", "blood"]
            },
            # Comedy / Romantic Comedy
            {
                "id": "paramount_comedy_1",
                "title": "80 for Brady",
                "type": "movie",
                "genre": ["Comedy", "Drama"],
                "year": 2023,
                "rating": 6.3,
                "duration": "1h 38m",
                "poster_url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=1280",
                "description": "Four best friends live life to the fullest when they take a wild trip to Super Bowl LI.",
                "provider": "paramount",
                "keywords": ["comedy", "funny", "friends", "feel good", "sports", "heartwarming"]
            },
            {
                "id": "paramount_comedy_2",
                "title": "Grease",
                "type": "movie",
                "genre": ["Comedy", "Romance", "Musical"],
                "year": 1978,
                "rating": 7.2,
                "duration": "1h 50m",
                "poster_url": "https://images.unsplash.com/photo-1534809027769-b00d750a6bac?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1534809027769-b00d750a6bac?w=1280",
                "description": "Good girl Sandy and greaser Danny fall in love in this classic romantic musical.",
                "provider": "paramount",
                "keywords": ["comedy", "romance", "romantic", "love", "musical", "classic", "funny"]
            },
            {
                "id": "paramount_comedy_3",
                "title": "Mean Girls",
                "type": "movie",
                "genre": ["Comedy"],
                "year": 2024,
                "rating": 6.8,
                "duration": "1h 52m",
                "poster_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1280",
                "description": "A new student navigates the treacherous waters of high school cliques.",
                "provider": "paramount",
                "keywords": ["comedy", "funny", "teen", "school", "musical", "friendship"]
            },
            # Action / Adventure / Exciting
            {
                "id": "paramount_action_1",
                "title": "Mission: Impossible - Dead Reckoning",
                "type": "movie",
                "genre": ["Action", "Thriller"],
                "year": 2023,
                "rating": 7.8,
                "duration": "2h 43m",
                "poster_url": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=1280",
                "description": "Ethan Hunt and his IMF team must track down a dangerous weapon before it falls into the wrong hands.",
                "provider": "paramount",
                "keywords": ["action", "exciting", "thriller", "spy", "adventure", "mission", "intense", "epic", "thrilling"]
            },
            {
                "id": "paramount_action_2",
                "title": "Top Gun: Maverick",
                "type": "movie",
                "genre": ["Action", "Drama"],
                "year": 2022,
                "rating": 8.3,
                "duration": "2h 11m",
                "poster_url": "https://images.unsplash.com/photo-1559128010-7c1ad6e1b6a5?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1559128010-7c1ad6e1b6a5?w=1280",
                "description": "After thirty years, Maverick is still pushing the envelope as a top naval aviator.",
                "provider": "paramount",
                "keywords": ["action", "exciting", "adventure", "military", "planes", "thrilling", "intense", "epic", "adrenaline"]
            },
            {
                "id": "paramount_action_3",
                "title": "Transformers: Rise of the Beasts",
                "type": "movie",
                "genre": ["Action", "Sci-Fi", "Adventure"],
                "year": 2023,
                "rating": 6.5,
                "duration": "2h 7m",
                "poster_url": "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=1280",
                "description": "The Maximals, Predacons, and Terrorcons join forces with the Autobots in an epic battle.",
                "provider": "paramount",
                "keywords": ["action", "sci-fi", "robots", "exciting", "adventure", "epic", "thrilling", "intense"]
            },
            {
                "id": "paramount_action_4",
                "title": "Sonic the Hedgehog 2",
                "type": "movie",
                "genre": ["Action", "Adventure", "Comedy"],
                "year": 2022,
                "rating": 6.5,
                "duration": "2h 2m",
                "poster_url": "https://images.unsplash.com/photo-1560472355-536de3962603?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1560472355-536de3962603?w=1280",
                "description": "Sonic teams up with Tails to stop Dr. Robotnik and new villain Knuckles.",
                "provider": "paramount",
                "keywords": ["action", "exciting", "adventure", "fun", "family", "thrilling", "fast"]
            },
            # Drama / Western
            {
                "id": "paramount_drama_1",
                "title": "Yellowstone",
                "type": "series",
                "genre": ["Drama", "Western"],
                "year": 2018,
                "rating": 8.7,
                "duration": "5 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1280",
                "description": "A ranching family in Montana faces off against land developers and an expanding town.",
                "provider": "paramount",
                "keywords": ["drama", "western", "family", "ranch", "intense", "thought-provoking"]
            },
            {
                "id": "paramount_drama_2",
                "title": "1883",
                "type": "series",
                "genre": ["Drama", "Western", "History"],
                "year": 2021,
                "rating": 8.7,
                "duration": "1 Season",
                "poster_url": "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=1280",
                "description": "The Dutton family's origin story, following their journey west through the Great Plains.",
                "provider": "paramount",
                "keywords": ["drama", "western", "history", "family", "journey", "survival"]
            },
            # Sci-Fi
            {
                "id": "paramount_scifi_1",
                "title": "Star Trek: Strange New Worlds",
                "type": "series",
                "genre": ["Sci-Fi", "Adventure"],
                "year": 2022,
                "rating": 8.4,
                "duration": "2 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=1280",
                "description": "Captain Pike leads the USS Enterprise on new missions exploring strange new worlds.",
                "provider": "paramount",
                "keywords": ["sci-fi", "space", "adventure", "star trek", "exploration", "thought-provoking"]
            },
            {
                "id": "paramount_scifi_2",
                "title": "Halo",
                "type": "series",
                "genre": ["Sci-Fi", "Action"],
                "year": 2022,
                "rating": 7.0,
                "duration": "2 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1280",
                "description": "Master Chief leads the Spartans against the Covenant in this epic sci-fi series.",
                "provider": "paramount",
                "keywords": ["sci-fi", "action", "space", "military", "epic", "adventure"]
            },
            # Documentary
            {
                "id": "paramount_doc_1",
                "title": "The Real Criminal Minds",
                "type": "series",
                "genre": ["Documentary", "Crime"],
                "year": 2022,
                "rating": 7.5,
                "duration": "1 Season",
                "poster_url": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1280",
                "description": "Real FBI profilers discuss the cases that inspired the hit TV series.",
                "provider": "paramount",
                "keywords": ["documentary", "true crime", "crime", "fbi", "investigation", "real", "great"]
            },
            {
                "id": "paramount_doc_2",
                "title": "60 Minutes",
                "type": "series",
                "genre": ["Documentary", "News"],
                "year": 1968,
                "rating": 7.9,
                "duration": "56 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1280",
                "description": "America's premier newsmagazine, delivering investigative journalism for decades.",
                "provider": "paramount",
                "keywords": ["documentary", "news", "investigation", "journalism", "real", "great"]
            },
            {
                "id": "paramount_doc_3",
                "title": "48 Hours",
                "type": "series",
                "genre": ["Documentary", "Crime", "News"],
                "year": 1988,
                "rating": 7.2,
                "duration": "36 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1516321497487-e288fb19713f?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1516321497487-e288fb19713f?w=1280",
                "description": "In-depth investigations into the most intriguing crime stories.",
                "provider": "paramount",
                "keywords": ["documentary", "true crime", "crime", "mystery", "investigation", "real", "great"]
            },
            # Popular / Trending / What to Watch
            {
                "id": "paramount_popular_1",
                "title": "NCIS",
                "type": "series",
                "genre": ["Drama", "Crime", "Action"],
                "year": 2003,
                "rating": 7.8,
                "duration": "21 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=1280",
                "description": "Naval Criminal Investigative Service agents solve crimes involving the Navy and Marine Corps.",
                "provider": "paramount",
                "keywords": ["popular", "trending", "recommended", "crime", "drama", "watch"]
            },
            {
                "id": "paramount_popular_2",
                "title": "Criminal Minds",
                "type": "series",
                "genre": ["Drama", "Crime", "Thriller"],
                "year": 2005,
                "rating": 8.1,
                "duration": "15 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1509281373149-e957c6296406?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1509281373149-e957c6296406?w=1280",
                "description": "An elite team of FBI profilers analyze the country's most twisted criminal minds.",
                "provider": "paramount",
                "keywords": ["popular", "trending", "recommended", "thriller", "crime", "watch"]
            },
            # Relaxing / Feel Good
            {
                "id": "paramount_relax_1",
                "title": "SpongeBob SquarePants",
                "type": "series",
                "genre": ["Animation", "Comedy", "Family"],
                "year": 1999,
                "rating": 8.2,
                "duration": "13 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1534423861386-85a16f5d13fd?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1534423861386-85a16f5d13fd?w=1280",
                "description": "The adventures of a yellow sea sponge who lives in a pineapple under the sea.",
                "provider": "paramount",
                "keywords": ["relax", "feel good", "comedy", "animation", "family", "fun", "happy", "cozy", "calm"]
            },
            {
                "id": "paramount_relax_2",
                "title": "Paw Patrol: The Mighty Movie",
                "type": "movie",
                "genre": ["Animation", "Family", "Adventure"],
                "year": 2023,
                "rating": 6.2,
                "duration": "1h 32m",
                "poster_url": "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1280",
                "description": "The PAW Patrol pups gain superpowers after a meteor strikes Adventure City.",
                "provider": "paramount",
                "keywords": ["relax", "family", "kids", "animation", "fun", "feel good", "cozy", "happy"]
            },
            {
                "id": "paramount_relax_3",
                "title": "The Good Fight",
                "type": "series",
                "genre": ["Drama", "Comedy"],
                "year": 2017,
                "rating": 8.4,
                "duration": "6 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?w=1280",
                "description": "A sophisticated legal drama with witty dialogue and compelling characters.",
                "provider": "paramount",
                "keywords": ["relax", "drama", "legal", "smart", "calm", "cozy"]
            },
            {
                "id": "paramount_relax_4",
                "title": "Blue Bloods",
                "type": "series",
                "genre": ["Drama", "Crime", "Family"],
                "year": 2010,
                "rating": 7.5,
                "duration": "14 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?w=1280",
                "description": "A multi-generational family of cops navigating crime and family dinners in NYC.",
                "provider": "paramount",
                "keywords": ["relax", "drama", "family", "cozy", "procedural", "calm"]
            },
            # Surprise / Mystery / Twist
            {
                "id": "paramount_surprise_1",
                "title": "Poker Face",
                "type": "series",
                "genre": ["Mystery", "Comedy", "Crime"],
                "year": 2023,
                "rating": 7.9,
                "duration": "1 Season",
                "poster_url": "https://images.unsplash.com/photo-1596566229443-12f93c8f0e24?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1596566229443-12f93c8f0e24?w=1280",
                "description": "A mystery of the week with a human lie detector traveling the country solving murders.",
                "provider": "paramount",
                "keywords": ["surprise", "mystery", "twist", "unexpected", "detective", "whodunit"]
            },
            {
                "id": "paramount_surprise_2",
                "title": "Rabbit Hole",
                "type": "series",
                "genre": ["Thriller", "Drama"],
                "year": 2023,
                "rating": 7.5,
                "duration": "1 Season",
                "poster_url": "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?w=1280",
                "description": "A master of deception goes down a rabbit hole of espionage filled with twists.",
                "provider": "paramount",
                "keywords": ["surprise", "twist", "thriller", "unexpected", "spy", "mystery"]
            },
            # Mind-Blowing / Thought-Provoking
            {
                "id": "paramount_mind_1",
                "title": "Arrival",
                "type": "movie",
                "genre": ["Sci-Fi", "Drama", "Mystery"],
                "year": 2016,
                "rating": 7.9,
                "duration": "1h 56m",
                "poster_url": "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=1280",
                "description": "A linguist works with the military to communicate with alien lifeforms, discovering a mind-bending truth about time.",
                "provider": "paramount",
                "keywords": ["mind-bending", "thought-provoking", "sci-fi", "twist", "deep", "meaningful", "psychological"]
            },
            {
                "id": "paramount_mind_2",
                "title": "Interstellar",
                "type": "movie",
                "genre": ["Sci-Fi", "Adventure", "Drama"],
                "year": 2014,
                "rating": 8.7,
                "duration": "2h 49m",
                "poster_url": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=1280",
                "description": "A team of explorers travel through a wormhole in space to ensure humanity's survival.",
                "provider": "paramount",
                "keywords": ["mind-bending", "thought-provoking", "sci-fi", "epic", "deep", "space", "emotional"]
            },
            {
                "id": "paramount_mind_3",
                "title": "Shutter Island",
                "type": "movie",
                "genre": ["Mystery", "Thriller"],
                "year": 2010,
                "rating": 8.2,
                "duration": "2h 18m",
                "poster_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1280",
                "description": "A U.S. Marshal investigates a psychiatric facility on an island, but nothing is as it seems.",
                "provider": "paramount",
                "keywords": ["mind-bending", "twist", "psychological", "mystery", "thought-provoking", "thriller"]
            },
            {
                "id": "paramount_mind_4",
                "title": "Black Mirror",
                "type": "series",
                "genre": ["Sci-Fi", "Drama", "Thriller"],
                "year": 2011,
                "rating": 8.7,
                "duration": "6 Seasons",
                "poster_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1280",
                "description": "An anthology series exploring a twisted, high-tech multiverse where humanity's greatest innovations collide with darkest instincts.",
                "provider": "paramount",
                "keywords": ["mind-bending", "thought-provoking", "sci-fi", "twist", "dark", "technology", "psychological"]
            },
            # Documentary / Learn
            {
                "id": "paramount_doc_1",
                "title": "Planet Earth III",
                "type": "series",
                "genre": ["Documentary", "Nature"],
                "year": 2023,
                "rating": 9.4,
                "duration": "8 Episodes",
                "poster_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=1280",
                "description": "Explore the most spectacular habitats on Earth and the remarkable animals that call them home.",
                "provider": "paramount",
                "keywords": ["documentary", "nature", "educational", "learn", "animals", "planet", "real"]
            },
            {
                "id": "paramount_doc_2",
                "title": "The Last Dance",
                "type": "series",
                "genre": ["Documentary", "Sports"],
                "year": 2020,
                "rating": 9.1,
                "duration": "10 Episodes",
                "poster_url": "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=1280",
                "description": "A chronicle of Michael Jordan's last championship season with the Chicago Bulls.",
                "provider": "paramount",
                "keywords": ["documentary", "sports", "basketball", "learn", "history", "real", "inspiring"]
            },
            {
                "id": "paramount_doc_3",
                "title": "Our Universe",
                "type": "series",
                "genre": ["Documentary", "Science"],
                "year": 2022,
                "rating": 8.2,
                "duration": "6 Episodes",
                "poster_url": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=1280",
                "description": "Epic stories of Earth's extraordinary animals and their connection to the cosmos.",
                "provider": "paramount",
                "keywords": ["documentary", "science", "space", "learn", "educational", "nature", "real"]
            },
            {
                "id": "paramount_doc_4",
                "title": "Inside Job",
                "type": "movie",
                "genre": ["Documentary"],
                "year": 2010,
                "rating": 8.2,
                "duration": "1h 49m",
                "poster_url": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1280",
                "description": "An Oscar-winning documentary about the 2008 financial crisis and systemic corruption.",
                "provider": "paramount",
                "keywords": ["documentary", "finance", "investigation", "learn", "educational", "real", "true crime"]
            },
            {
                "id": "paramount_doc_5",
                "title": "March of the Penguins",
                "type": "movie",
                "genre": ["Documentary", "Nature"],
                "year": 2005,
                "rating": 7.5,
                "duration": "1h 20m",
                "poster_url": "https://images.unsplash.com/photo-1551986782-d0169b3f8fa7?w=500",
                "backdrop_url": "https://images.unsplash.com/photo-1551986782-d0169b3f8fa7?w=1280",
                "description": "A look at the annual journey of Emperor penguins as they march to their breeding ground.",
                "provider": "paramount",
                "keywords": ["documentary", "nature", "animals", "learn", "educational", "heartwarming", "real"]
            },
        ]
        
        # Score each item based on query match
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Determine content type filter from query
        content_type_filter = None
        if any(word in query_lower for word in ["movie", "movies", "film", "films"]):
            content_type_filter = "movie"
        elif any(word in query_lower for word in ["show", "shows", "series", "tv", "binge"]):
            content_type_filter = "series"
        
        # Expand common query terms with positive matches and negative exclusions
        # These map mood-based queries to content keywords
        query_expansions = {
            # Relaxing mood
            "relax": {"include": ["relax", "feel good", "cozy", "calm", "peaceful", "happy", "family", "animation", "heartwarming"], "exclude": ["horror", "thriller", "scary", "intense", "action", "violent"]},
            "calm": {"include": ["relax", "feel good", "cozy", "calm", "peaceful", "family", "heartwarming"], "exclude": ["horror", "thriller", "scary", "intense", "action"]},
            
            # Scary mood
            "scary": {"include": ["horror", "scary", "thriller", "creepy", "terrifying", "supernatural", "demon", "ghost"], "exclude": ["comedy", "family", "kids", "heartwarming"]},
            "thrill": {"include": ["horror", "scary", "thriller", "suspense", "intense"], "exclude": ["comedy", "family"]},
            
            # Exciting mood
            "exciting": {"include": ["action", "exciting", "thrilling", "adventure", "epic", "intense", "mission", "spy"], "exclude": ["relax", "calm", "documentary"]},
            "action": {"include": ["action", "exciting", "thrilling", "adventure", "epic", "mission", "spy"], "exclude": ["relax", "documentary"]},
            
            # Funny mood
            "funny": {"include": ["comedy", "funny", "humor", "laugh", "hilarious", "feel good"], "exclude": ["horror", "thriller", "scary"]},
            "laugh": {"include": ["comedy", "funny", "humor", "hilarious", "feel good"], "exclude": ["horror", "thriller"]},
            
            # Romantic mood
            "romantic": {"include": ["romance", "romantic", "love", "relationship", "heartwarming"], "exclude": ["horror", "action", "scary"]},
            "love": {"include": ["romance", "romantic", "love", "relationship"], "exclude": ["horror"]},
            
            # Mind-blowing / thought-provoking mood
            "mind": {"include": ["thought-provoking", "mind-bending", "sci-fi", "twist", "mystery", "psychological"], "exclude": ["comedy", "family"]},
            "blow": {"include": ["thought-provoking", "mind-bending", "sci-fi", "twist", "epic"], "exclude": []},
            "thought": {"include": ["thought-provoking", "drama", "documentary", "meaningful", "deep"], "exclude": ["action"]},
            "provok": {"include": ["thought-provoking", "drama", "documentary", "deep", "meaningful"], "exclude": []},
            
            # Documentary / Learning mood
            "documentary": {"include": ["documentary", "true crime", "real", "investigation", "educational", "nature"], "exclude": ["fiction", "animation", "action", "adventure", "sci-fi", "horror", "thriller", "comedy"]},
            "learn": {"include": ["documentary", "educational", "true crime", "real", "investigation", "nature", "history"], "exclude": ["fiction", "animation", "action", "horror", "comedy"]},
            
            # Surprise mood
            "surprise": {"include": ["mystery", "thriller", "unexpected", "twist", "adventure", "diverse"], "exclude": []},
            "unexpected": {"include": ["mystery", "twist", "thriller", "adventure", "diverse"], "exclude": []},
            
            # General terms
            "watch": {"include": ["popular", "trending", "recommended"], "exclude": []},
            "best": {"include": ["popular", "trending", "recommended"], "exclude": []},
            "great": {"include": ["popular", "trending", "recommended"], "exclude": []},
            "trending": {"include": ["popular", "trending", "recommended"], "exclude": []},
            "popular": {"include": ["popular", "trending", "recommended"], "exclude": []},
            "sports": {"include": ["sports", "football", "racing", "athletic"], "exclude": []},
            "live": {"include": ["live", "news", "event"], "exclude": []},
            "similar": {"include": ["popular", "trending"], "exclude": []},
            "personalize": {"include": ["popular", "trending", "recommended", "diverse"], "exclude": []},
        }
        
        # Detect which mood category the query is for (to require primary match)
        mood_primary_keywords = {
            "scary": {"horror", "scary", "creepy", "terrifying", "supernatural", "demon", "ghost", "slasher"},
            "funny": {"comedy", "funny", "humor", "laugh", "hilarious"},
            "romantic": {"romance", "romantic", "love"},
            "relaxing": {"relax", "cozy", "calm", "peaceful", "feel good", "heartwarming"},
            "exciting": {"action", "adventure", "epic", "mission", "spy", "adrenaline"},
            "mindblowing": {"mind-bending", "thought-provoking", "psychological", "twist", "deep"},
            "documentary": {"documentary", "educational", "real", "true crime", "nature", "history", "investigation"},
            "surprise": {"mystery", "unexpected", "twist", "whodunit", "detective"}
        }
        
        detected_mood = None
        mood_keywords = set()
        for mood, primaries in mood_primary_keywords.items():
            for keyword in primaries:
                if keyword in query_lower:
                    detected_mood = mood
                    mood_keywords = primaries
                    break
            if detected_mood:
                break
        
        exclude_keywords = set()
        for word in list(query_words):
            for key, config in query_expansions.items():
                if key in word:
                    query_words.update(config["include"])
                    exclude_keywords.update(config["exclude"])
        
        scored_content = []
        for item in mock_catalog:
            # Filter by content type if specified
            if content_type_filter:
                if content_type_filter == "movie" and item["type"] != "movie":
                    continue
                if content_type_filter == "series" and item["type"] != "series":
                    continue
            
            keywords = set(item.get("keywords", []))
            item_genres_lower = [g.lower() for g in item["genre"]]
            
            # Check for exclusions first - skip if matches excluded keywords
            if exclude_keywords:
                excluded = False
                for exc in exclude_keywords:
                    if exc in keywords or any(exc in g for g in item_genres_lower):
                        excluded = True
                        break
                if excluded:
                    continue
            
            # If a mood is detected, require at least one primary keyword match
            if detected_mood and mood_keywords:
                has_primary_match = bool(mood_keywords & keywords) or any(
                    any(pk in g for pk in mood_keywords) for g in item_genres_lower
                )
                if not has_primary_match:
                    continue
            
            score = 0
            
            # Check keywords
            keyword_matches = query_words & keywords
            score += len(keyword_matches) * 30
            
            # Check title
            if any(word in item["title"].lower() for word in query_words):
                score += 50
            
            # Check genre - give bonus for primary mood genre match
            for genre in item["genre"]:
                genre_lower = genre.lower()
                if genre_lower in query_lower or any(word in genre_lower for word in query_words):
                    score += 40
                # Extra bonus for primary mood genre match
                if detected_mood and any(pk in genre_lower for pk in mood_keywords):
                    score += 50
            
            # Check description
            desc_lower = item["description"].lower()
            for word in query_words:
                if word in desc_lower:
                    score += 10
            
            # Boost by rating for general queries
            if "best" in query_words or "great" in query_words or "top" in query_words:
                score += int(item["rating"] * 10)
            
            if score > 0:
                scored_content.append((item, score))
        
        # Sort by score (best matches first)
        scored_content.sort(key=lambda x: x[1], reverse=True)
        
        # Return top matches, or if no matches return diverse defaults
        if scored_content:
            result = [item.copy() for item, _ in scored_content[:limit]]
        else:
            # Default fallback - return diverse popular content (one from each category)
            import random
            defaults = []
            categories_seen = set()
            
            # Filter catalog by content type if specified
            filtered_catalog = mock_catalog
            if content_type_filter:
                filtered_catalog = [item for item in mock_catalog if item["type"] == content_type_filter]
            
            # If filter left nothing, use full catalog
            if not filtered_catalog:
                filtered_catalog = mock_catalog
                
            shuffled_catalog = list(filtered_catalog)
            random.shuffle(shuffled_catalog)
            
            for item in shuffled_catalog:
                # Get primary genre/category
                primary_genre = item["genre"][0] if item["genre"] else "Other"
                if primary_genre not in categories_seen:
                    categories_seen.add(primary_genre)
                    defaults.append(item.copy())
                if len(defaults) >= limit:
                    break
            
            # If still not enough, add highest rated from filtered catalog
            if len(defaults) < limit:
                by_rating = sorted(filtered_catalog, key=lambda x: x["rating"], reverse=True)
                for item in by_rating:
                    if item not in defaults:
                        defaults.append(item.copy())
                    if len(defaults) >= limit:
                        break
            
            result = defaults[:limit]
        
        # Remove keywords field before returning
        for item in result:
            item.pop("keywords", None)
        
        return result[:limit]


class UnifiedContentService:
    """
    Unified service that aggregates content from all streaming providers
    """
    
    def __init__(self):
        self.providers = {
            "tmdb": TMDbProvider(),
            "youtube": YouTubeProvider(),
            "paramount": ParamountPlusProvider(),
        }
    
    async def search_all(self, query: str, limit_per_provider: int = 5) -> list[dict]:
        """Search across all providers"""
        all_results = []
        
        for name, provider in self.providers.items():
            try:
                results = await provider.search(query, limit_per_provider)
                all_results.extend(results)
            except Exception as e:
                print(f"Error searching {name}: {e}")
        
        # Sort by rating/popularity
        all_results.sort(key=lambda x: x.get("rating", 0), reverse=True)
        return all_results
    
    async def get_trending_all(self, limit_per_provider: int = 10) -> list[dict]:
        """Get trending content from all providers"""
        all_results = []
        
        for name, provider in self.providers.items():
            try:
                results = await provider.get_trending(limit_per_provider)
                all_results.extend(results)
            except Exception as e:
                print(f"Error getting trending from {name}: {e}")
        
        # Shuffle to mix providers
        import random
        random.shuffle(all_results)
        return all_results
    
    async def search_provider(self, provider: str, query: str, limit: int = 10) -> list[dict]:
        """Search a specific provider"""
        if provider in self.providers:
            return await self.providers[provider].search(query, limit)
        return []
    
    def get_available_providers(self) -> list[dict]:
        """List available streaming providers"""
        return [
            {
                "id": "tmdb",
                "name": "TMDb",
                "description": "Movies & TV Shows Database",
                "status": "active" if os.getenv("TMDB_API_KEY") else "no_api_key",
                "content_types": ["movie", "series"]
            },
            {
                "id": "youtube",
                "name": "YouTube",
                "description": "Video Content Platform",
                "status": "active" if os.getenv("YOUTUBE_API_KEY") else "no_api_key",
                "content_types": ["video"]
            },
            {
                "id": "paramount",
                "name": "Paramount+",
                "description": "Premium Streaming (Enterprise)",
                "status": "demo_mode",
                "requires_partnership": True,
                "content_types": ["movie", "series"]
            }
        ]


# Singleton instance
content_service = UnifiedContentService()
