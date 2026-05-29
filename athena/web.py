"""
Web Search - Web search tools for Athena
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    score: float = 0.0


class WebSearcher:
    """
    Web search tool using DuckDuckGo (no API key required).
    
    Example:
        >>> searcher = WebSearcher()
        >>> results = searcher.search("Python programming", limit=5)
        >>> for r in results:
        ...     print(f"{r.title}: {r.url}")
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialize searcher.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        Search the web.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of search results
        """
        try:
            return self._search_ddg(query, limit)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _search_ddg(self, query: str, limit: int) -> List[SearchResult]:
        """Search using DuckDuckGo."""
        import httpx
        
        try:
            # DuckDuckGo instant answer API
            response = httpx.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_redirect": "1",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Abstract (main result)
            if data.get("Abstract"):
                results.append(SearchResult(
                    title=data.get("Heading", ""),
                    url=data.get("AbstractURL", ""),
                    snippet=data.get("Abstract", ""),
                    score=1.0,
                ))
            
            # Related topics
            for topic in data.get("RelatedTopics", [])[:limit - len(results)]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(SearchResult(
                        title=topic.get("Text", "")[:100],
                        url=topic.get("FirstURL", ""),
                        snippet=topic.get("Text", ""),
                        score=0.5,
                    ))
            
            return results[:limit]
        
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def search_news(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        Search for news.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of news results
        """
        # Use regular search for now
        return self.search(f"{query} news", limit)


class URLFetcher:
    """
    Fetch and extract content from URLs.
    
    Example:
        >>> fetcher = URLFetcher()
        >>> content = fetcher.fetch("https://example.com")
        >>> print(content[:500])
    """
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
    
    def fetch(self, url: str, max_length: int = 5000) -> Optional[str]:
        """
        Fetch URL content.
        
        Args:
            url: URL to fetch
            max_length: Maximum content length
            
        Returns:
            Extracted text content
        """
        import httpx
        
        try:
            response = httpx.get(
                url,
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Athena/1.0)"
                }
            )
            response.raise_for_status()
            
            # Simple text extraction
            content = response.text
            
            # Remove script and style tags
            import re
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            return content[:max_length] if content else None
        
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
