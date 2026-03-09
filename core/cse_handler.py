"""
CSE (Critical Sector Entity) input handler and validation system
Handles loading, validating, and processing CSE profiles for phishing account detection
"""
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import re
from datetime import datetime

from .models import CSEProfile


class CSEInputHandler:
    """Handles input and processing of Critical Sector Entity profiles"""
    
    def __init__(self):
        """Initialize CSE input handler"""
        self.supported_formats = {'.json', '.csv'}
        self.validation_errors = []


    
    def load_cse_profiles(self, input_source: Union[str, Path, Dict, List[Dict]]) -> List[CSEProfile]:
        """
        Load CSE profiles from various input sources
        
        Args:
            input_source: File path, dictionary, or list of dictionaries containing CSE data
            
        Returns:
            List of validated CSEProfile objects
            
        Raises:
            ValueError: If input format is unsupported or data is invalid
            FileNotFoundError: If file path doesn't exist
        """
        self.validation_errors.clear()
        
        # Handle different input types
        if isinstance(input_source, (str, Path)):
            return self._load_from_file(Path(input_source))
        elif isinstance(input_source, dict):
            return self._load_from_dict([input_source])
        elif isinstance(input_source, list):
            return self._load_from_dict(input_source)
        else:
            raise ValueError(f"Unsupported input source type: {type(input_source)}")
    
    def _load_from_file(self, file_path: Path) -> List[CSEProfile]:
        """Load CSE profiles from file"""
        if not file_path.exists():
            raise FileNotFoundError(f"CSE profile file not found: {file_path}")

        if file_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. "
                           f"Supported formats: {self.supported_formats}")

        try:
            if file_path.suffix.lower() == '.json':
                return self._load_from_json(file_path)
            elif file_path.suffix.lower() == '.csv':
                return self._load_from_csv(file_path)
        except Exception as e:
            raise ValueError(f"Error loading CSE profiles from {file_path}: {str(e)}")


    
    def _load_from_json(self, file_path: Path) -> List[CSEProfile]:
        """Load CSE profiles from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both single profile and list of profiles
        if isinstance(data, dict):
            if 'profiles' in data:
                # Format: {"profiles": [...]}
                profile_data = data['profiles']
            else:
                # Single profile format
                profile_data = [data]
        elif isinstance(data, list):
            profile_data = data
        else:
            raise ValueError("JSON must contain a dictionary or list of CSE profiles")
        
        return self._load_from_dict(profile_data)
    
    def _load_from_csv(self, file_path: Path) -> List[CSEProfile]:
        """Load CSE profiles from CSV file"""
        profiles = []
        
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                try:
                    # Parse complex fields that might be JSON strings in CSV
                    profile_data = dict(row)
                    
                    # Parse JSON fields if they exist as strings
                    json_fields = ['official_accounts', 'key_personnel', 'official_domains', 'search_keywords']
                    for field in json_fields:
                        if field in profile_data and profile_data[field]:
                            try:
                                profile_data[field] = json.loads(profile_data[field])
                            except json.JSONDecodeError:
                                # If not JSON, treat as comma-separated values for lists
                                if field in ['key_personnel', 'official_domains', 'search_keywords']:
                                    profile_data[field] = [item.strip() for item in profile_data[field].split(',')]
                                else:
                                    self.validation_errors.append(f"Row {row_num}: Invalid JSON in field '{field}'")
                                    continue
                    
                    profile = self._create_profile_from_dict(profile_data)
                    if profile:
                        profiles.append(profile)
                        
                except Exception as e:
                    self.validation_errors.append(f"Row {row_num}: {str(e)}")
        
        return profiles
    
    
    def _load_from_dict(self, profile_data: List[Dict]) -> List[CSEProfile]:
        """Load CSE profiles from dictionary data"""
        profiles = []
        
        for i, data in enumerate(profile_data):
            try:
                profile = self._create_profile_from_dict(data)
                if profile:
                    profiles.append(profile)
            except Exception as e:
                self.validation_errors.append(f"Profile {i + 1}: {str(e)}")
        
        return profiles
    
    def _create_profile_from_dict(self, data: Dict) -> Optional[CSEProfile]:
        """Create CSEProfile from dictionary data with validation"""
        try:
            # Ensure required fields have default values
            profile_data = {
                'entity_id': data.get('entity_id', ''),
                'entity_name': data.get('entity_name', ''),
                'entity_type': data.get('entity_type', 'other'),
                'official_accounts': data.get('official_accounts', {}),
                'key_personnel': data.get('key_personnel', []),
                'official_domains': data.get('official_domains', []),
                'sector_classification': data.get('sector_classification', 'unknown'),
                'search_keywords': data.get('search_keywords', []),
                'created_at': data.get('created_at', datetime.now().isoformat())
            }
            
            # Create and validate profile
            profile = CSEProfile(**profile_data)
            return profile
            
        except (ValueError, TypeError) as e:
            self.validation_errors.append(f"Invalid profile data: {str(e)}")
            return None
    
    def validate_cse_data(self, profile: CSEProfile) -> bool:
        """
        Validate CSE profile data
        
        Args:
            profile: CSEProfile object to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            return profile.is_valid()
        except Exception:
            return False
    
    def validate_batch_cse_data(self, profiles: List[CSEProfile]) -> Dict[str, Any]:
        """
        Validate a batch of CSE profiles
        
        Args:
            profiles: List of CSEProfile objects to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'total_profiles': len(profiles),
            'valid_profiles': 0,
            'invalid_profiles': 0,
            'validation_errors': [],
            'valid_profile_ids': [],
            'invalid_profile_ids': []
        }
        
        for profile in profiles:
            if self.validate_cse_data(profile):
                results['valid_profiles'] += 1
                results['valid_profile_ids'].append(profile.entity_id)
            else:
                results['invalid_profiles'] += 1
                results['invalid_profile_ids'].append(profile.entity_id)
                results['validation_errors'].append(f"Invalid profile: {profile.entity_id}")
        
        # Add any errors from loading process
        results['validation_errors'].extend(self.validation_errors)
        
        return results
    
    def extract_search_terms(self, profile: CSEProfile) -> List[str]:
        """
        Extract search terms from CSE profile data
        
        Args:
            profile: CSEProfile object to extract terms from
            
        Returns:
            List of search terms for account detection
        """
        search_terms = set()
        
        # Use existing search keywords if available
        if profile.search_keywords:
            search_terms.update([term.lower().strip() for term in profile.search_keywords])
        
        # Extract from entity name
        entity_name_terms = self._extract_terms_from_text(profile.entity_name)
        search_terms.update(entity_name_terms)
        
        # Extract from key personnel
        for person in profile.key_personnel:
            person_terms = self._extract_terms_from_text(person)
            search_terms.update(person_terms)
        
        # Extract from official account usernames
        for platform, username in profile.official_accounts.items():
            if username:
                # Add username variations
                search_terms.add(username.lower().strip())
                # Add username without platform-specific prefixes but keep underscores
                clean_username = username.replace('@', '').lower().strip()
                if clean_username:
                    search_terms.add(clean_username)
                # Also add version without _official suffix
                if '_official' in clean_username:
                    base_username = clean_username.replace('_official', '')
                    if base_username:
                        search_terms.add(base_username)
        
        # Extract from domain names
        for domain in profile.official_domains:
            domain_terms = self._extract_domain_terms(domain)
            search_terms.update(domain_terms)
        
        # Filter out short terms and common words
        filtered_terms = self._filter_search_terms(list(search_terms))
        
        return filtered_terms
    
    def _extract_terms_from_text(self, text: str) -> List[str]:
        """Extract meaningful terms from text"""
        if not text:
            return []
        
        # Clean and split text
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = cleaned_text.split()
        
        # Filter meaningful words
        meaningful_words = []
        for word in words:
            if len(word) > 2 and word.isalpha():
                meaningful_words.append(word)
        
        return meaningful_words
    
    def _extract_domain_terms(self, domain: str) -> List[str]:
        """Extract search terms from domain names"""
        if not domain:
            return []
        
        terms = []
        
        # Remove TLD and split by dots
        domain_parts = domain.lower().split('.')
        
        for part in domain_parts[:-1]:  # Exclude TLD
            if len(part) > 2:
                terms.append(part)
                
                # Split camelCase or underscore separated words
                sub_words = re.findall(r'[a-z]+', part)
                terms.extend([word for word in sub_words if len(word) > 2])
        
        return terms
    
    def _filter_search_terms(self, terms: List[str]) -> List[str]:
        """Filter search terms to remove common/stop words and short terms"""
        # Common stop words to exclude
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'www', 'com',
            'org', 'net', 'gov', 'edu', 'mil', 'int', 'official', 'main', 'home'
        }
        
        filtered = []
        for term in terms:
            term = term.strip().lower()
            if (len(term) > 2 and 
                term not in stop_words and 
                (term.isalpha() or '_' in term) and  # Allow underscores for usernames
                not term.isdigit()):
                filtered.append(term)
        
        # Remove duplicates and sort
        return sorted(list(set(filtered)))
    
    
    
    
    
    
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors from last operation"""
        return self.validation_errors.copy()
    
    def clear_validation_errors(self) -> None:
        """Clear validation errors"""
        self.validation_errors.clear()