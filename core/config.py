"""
Configuration classes for social media scraper
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ScrapingConfig:
    """Base configuration for scraping operations"""
    # Browser settings
    headless: bool = False  # Set to False to see browser activity
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    viewport: Dict[str, int] = None
    
    # Timing settings
    min_delay: float = 1.0
    max_delay: float = 3.0
    page_timeout: int = 30000
    
    # Scraping limits
    max_posts_per_session: int = 100
    max_concurrent_platforms: int = 3
    
    # Data extraction
    extract_media: bool = True
    expand_urls: bool = True
    extract_engagement: bool = True
    
    # Storage
    session_storage_path: str = "./sessions"
    output_format: str = "json"
    
    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1920, "height": 1080}


@dataclass
class RedditConfig:
    """Reddit-specific configuration"""
    base_url: str = "https://www.reddit.com"
    login_url: str = "https://www.reddit.com/login"
    
    # CSS selectors for Reddit elements
    login_selectors: Dict[str, str] = None
    post_selectors: Dict[str, str] = None
    search_selectors: Dict[str, str] = None
    
    # Reddit-specific settings
    default_sort: str = "hot"  # hot, new, top, rising
    max_posts_per_subreddit: int = 50
    
    def __post_init__(self):
        if self.login_selectors is None:
            self.login_selectors = {
                "username_field": "input[name='username']",
                "password_field": "input[name='password']",
                "login_button": "button:has-text('Log In')",
                "login_form": "div"  # Reddit doesn't use a traditional form element
            }
        
        if self.post_selectors is None:
            self.post_selectors = {
                "post_container": "[data-testid='post-container']",
                "post_title": "h3",
                "post_content": "[data-testid='post-content']",
                "author": "[data-testid='post-author']",
                "timestamp": "time",
                "upvotes": "[data-testid='upvote-button']",
                "comments": "[data-testid='comment-count']",
                "subreddit": "[data-testid='subreddit-name']"
            }
        
        if self.search_selectors is None:
            self.search_selectors = {
                "search_box": "input[name='q']",
                "search_button": "button[type='submit']",
                "results_container": "[data-testid='search-results']"
            }


@dataclass
class InstagramConfig:
    """Instagram-specific configuration"""
    base_url: str = "https://www.instagram.com"
    login_url: str = "https://www.instagram.com/accounts/login/"
    
    # CSS selectors for Instagram elements
    login_selectors: Dict[str, str] = None
    post_selectors: Dict[str, str] = None
    search_selectors: Dict[str, str] = None
    
    # Instagram-specific settings
    max_posts_per_user: int = 50
    story_timeout: int = 10  # seconds to wait for stories to load
    
    def __post_init__(self):
        if self.login_selectors is None:
            self.login_selectors = {
                "username_field": "input[name='username'], input[name='email'], input[type='text']",
                "password_field": "input[name='password'], input[name='pass'], input[type='password']",
                "login_button": "button[type='submit'], input[type='submit'], div[role='button']:has-text('Log'), button:has-text('Log in')",
                "login_form": "form, div[role='main']"
            }
        
        if self.post_selectors is None:
            self.post_selectors = {
                "post_container": "article",
                "post_content": "[data-testid='post-content']",
                "caption": "[data-testid='post-caption']",
                "author": "header a",
                "timestamp": "time",
                "likes": "[data-testid='like-count']",
                "comments": "[data-testid='comment-count']"
            }
        
        if self.search_selectors is None:
            self.search_selectors = {
                "search_box": "input[placeholder*='Search']",
                "search_button": "button[type='submit']",
                "results_container": "[role='main']"
            }


@dataclass
class LinkedinConfig:
    """LinkedIn-specific configuration"""
    base_url: str = "https://www.linkedin.com"
    login_url: str = "https://www.linkedin.com/login"
    
    # CSS selectors for LinkedIn elements
    login_selectors: Dict[str, str] = None
    post_selectors: Dict[str, str] = None
    search_selectors: Dict[str, str] = None
    
    # LinkedIn-specific settings
    max_posts_per_user: int = 50
    scroll_delay: float = 2.0  # seconds between scrolls
    
    def __post_init__(self):
        if self.login_selectors is None:
            self.login_selectors = {
                "username_field": "input[name='session_key'], input[id='username']",
                "password_field": "input[name='session_password'], input[id='password']",
                "login_button": "button[type='submit'], button[aria-label*='Sign in']",
                "login_form": "form"
            }
        
        if self.post_selectors is None:
            self.post_selectors = {
                "post_container": "div[data-id]",
                "post_content": ".feed-shared-update-v2__description",
                "author": ".feed-shared-actor__name",
                "timestamp": "time",
                "likes": ".social-details-social-counts__reactions-count",
                "comments": ".social-details-social-counts__comments"
            }
        
        if self.search_selectors is None:
            self.search_selectors = {
                "search_box": "input[placeholder*='Search'], .search-global-typeahead__input",
                "search_button": "button[type='submit']",
                "results_container": ".search-results-container"
            }

@dataclass
class FacebookConfig:
    """Facebook-specific configuration"""
    base_url: str = "https://www.facebook.com"
    login_url: str = "https://www.facebook.com/login"
    
    # CSS selectors for Facebook elements
    login_selectors: Dict[str, str] = None
    post_selectors: Dict[str, str] = None
    search_selectors: Dict[str, str] = None
    
    # Facebook-specific settings
    max_posts_per_page: int = 50
    scroll_delay: float = 2.0  # seconds between scrolls
    
    def __post_init__(self):
        if self.login_selectors is None:
            self.login_selectors = {
                "email_field": "input[name='email'], input[type='email'], input[type='text']",
                "password_field": "input[name='pass'], input[type='password']",
                "login_button": "button[name='login'], button[type='submit']",
                "login_form": "form"
            }
        
        if self.post_selectors is None:
            self.post_selectors = {
                "post_container": "div[role='article']",
                "post_content": "[data-ad-preview='message']",
                "author": "a[role='link']",
                "timestamp": "abbr",
                "likes": "[aria-label*='Like']",
                "comments": "[aria-label*='Comment']",
                "shares": "[aria-label*='Share']"
            }
        
        if self.search_selectors is None:
            self.search_selectors = {
                "search_box": "input[type='search'], input[placeholder*='Search']",
                "search_button": "button[type='submit']",
                "results_container": "[role='main']"
            }


@dataclass
class XConfig:
    """X (Twitter) specific configuration"""
    base_url: str = "https://x.com"
    login_url: str = "https://x.com/i/flow/login"
    
    # CSS selectors for X elements
    login_selectors: Dict[str, str] = None
    post_selectors: Dict[str, str] = None
    search_selectors: Dict[str, str] = None
    
    # X-specific settings
    max_tweets_per_search: int = 100
    scroll_delay: float = 2.0  # seconds between scrolls
    
    def __post_init__(self):
        if self.login_selectors is None:
            self.login_selectors = {
                "username_field": "input[name='text']",
                "password_field": "input[name='password']",
                "login_button": "[data-testid='LoginForm_Login_Button']",
                "next_button": "[role='button']:has-text('Next')"
            }
        
        if self.post_selectors is None:
            self.post_selectors = {
                "tweet_container": "[data-testid='tweet']",
                "tweet_content": "[data-testid='tweetText']",
                "author": "[data-testid='User-Name']",
                "handle": "[data-testid='User-Name'] span:last-child",
                "timestamp": "time",
                "likes": "[data-testid='like']",
                "retweets": "[data-testid='retweet']",
                "replies": "[data-testid='reply']"
            }
        
        if self.search_selectors is None:
            self.search_selectors = {
                "search_box": "[data-testid='SearchBox_Search_Input']",
                "search_button": "[data-testid='SearchBox_Search_Button']",
                "results_container": "[data-testid='primaryColumn']"
            }


class ConfigManager:
    """Manages configuration for different platforms"""
    
    def __init__(self):
        self.base_config = ScrapingConfig()
        self.reddit_config = RedditConfig()
        self.instagram_config = InstagramConfig()
        self.linkedin_config = LinkedinConfig()
        self.facebook_config = FacebookConfig()
        self.x_config = XConfig()
    
    def get_reddit_config(self) -> tuple[ScrapingConfig, RedditConfig]:
        """Get combined configuration for Reddit scraping"""
        return self.base_config, self.reddit_config
    
    def get_instagram_config(self) -> tuple[ScrapingConfig, InstagramConfig]:
        """Get combined configuration for Instagram scraping"""
        return self.base_config, self.instagram_config
    
    def get_linkedin_config(self) -> tuple[ScrapingConfig, LinkedinConfig]:
        """Get combined configuration for LinkedIn scraping"""
        return self.base_config, self.linkedin_config
    
    def get_facebook_config(self) -> tuple[ScrapingConfig, FacebookConfig]:
        """Get combined configuration for Facebook scraping"""
        return self.base_config, self.facebook_config
    
    def get_x_config(self) -> tuple[ScrapingConfig, XConfig]:
        """Get combined configuration for X scraping"""
        return self.base_config, self.x_config
    
    def update_base_config(self, **kwargs):
        """Update base scraping configuration"""
        for key, value in kwargs.items():
            if hasattr(self.base_config, key):
                setattr(self.base_config, key, value)
    
    def update_reddit_config(self, **kwargs):
        """Update Reddit-specific configuration"""
        for key, value in kwargs.items():
            if hasattr(self.reddit_config, key):
                setattr(self.reddit_config, key, value)
    
    def update_instagram_config(self, **kwargs):
        """Update Instagram-specific configuration"""
        for key, value in kwargs.items():
            if hasattr(self.instagram_config, key):
                setattr(self.instagram_config, key, value)
    
    def update_linkedin_config(self, **kwargs):
        """Update LinkedIn-specific configuration"""
        for key, value in kwargs.items():
            if hasattr(self.linkedin_config, key):
                setattr(self.linkedin_config, key, value)
    
    def update_facebook_config(self, **kwargs):
        """Update Facebook-specific configuration"""
        for key, value in kwargs.items():
            if hasattr(self.facebook_config, key):
                setattr(self.facebook_config, key, value)
    
    def update_x_config(self, **kwargs):
        """Update X-specific configuration"""
        for key, value in kwargs.items():
            if hasattr(self.x_config, key):
                setattr(self.x_config, key, value)