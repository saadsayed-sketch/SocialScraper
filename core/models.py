"""
Simplified data models for social media scraper
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import re


@dataclass
class CSEProfile:
    """Critical Sector Entity profile for comparison"""
    entity_id: str
    entity_name: str
    entity_type: str = "other"
    official_accounts: Dict[str, str] = field(default_factory=dict)
    key_personnel: List[str] = field(default_factory=list)
    official_domains: List[str] = field(default_factory=list)
    sector_classification: str = "other"
    search_keywords: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        """Validate CSE profile data after initialization"""
        self._validate_entity_data()
        if not self.search_keywords:
            self.search_keywords = self._generate_search_keywords()
    
    def _validate_entity_data(self) -> None:
        """Validate required CSE profile fields"""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("entity_id is required and cannot be empty")
        
        if not self.entity_name or not self.entity_name.strip():
            raise ValueError("entity_name is required and cannot be empty")
        
        valid_entity_types = {"government", "infrastructure", "financial", "healthcare", "education", "defense", "other"}
        if self.entity_type not in valid_entity_types:
            raise ValueError(f"entity_type must be one of: {valid_entity_types}")
        
        if not self.official_domains:
            # Auto-generate a domain if none provided
            domain_guess = self.entity_name.lower().replace(' ', '') + '.com'
            self.official_domains = [domain_guess]
        
        # Validate domain formats
        domain_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$')
        for domain in self.official_domains:
            if not domain_pattern.match(domain):
                raise ValueError(f"Invalid domain format: {domain}")
    
    def _generate_search_keywords(self) -> List[str]:
        """Generate search keywords from entity data"""
        keywords = []
        
        # Add entity name variations
        keywords.append(self.entity_name.lower())
        
        # Add individual words from entity name
        name_words = self.entity_name.lower().split()
        keywords.extend([word for word in name_words if len(word) > 2])
        
        # Add key personnel names
        for person in self.key_personnel:
            keywords.append(person.lower())
            # Add individual names
            person_words = person.lower().split()
            keywords.extend([word for word in person_words if len(word) > 2])
        
        # Add domain names without TLD
        for domain in self.official_domains:
            domain_name = domain.split('.')[0]
            if len(domain_name) > 2:
                keywords.append(domain_name.lower())
        
        # Remove duplicates and return
        return list(set(keywords))
    
    def is_valid(self) -> bool:
        """Check if CSE profile is valid"""
        try:
            self._validate_entity_data()
            return True
        except ValueError:
            return False