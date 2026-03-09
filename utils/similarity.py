"""
Similarity and filtering utilities for phishing detection
"""
from typing import List, Dict
import re


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Levenshtein distance (number of edits needed)
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """
    Calculate similarity ratio between two strings (0.0 to 1.0)
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Similarity ratio (1.0 = identical, 0.0 = completely different)
    """
    distance = levenshtein_distance(s1.lower(), s2.lower())
    max_len = max(len(s1), len(s2))
    
    if max_len == 0:
        return 1.0
    
    return 1.0 - (distance / max_len)


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison by removing special characters and spaces
    
    Args:
        name: Name to normalize
        
    Returns:
        Normalized name (lowercase, no spaces/special chars)
    """
    # Convert to lowercase
    name = name.lower()
    
    # Remove common words that don't add meaning
    remove_words = ['official', 'verified', 'real', 'authentic', 'the', 'bank', 'of']
    for word in remove_words:
        name = re.sub(r'\b' + word + r'\b', '', name)
    
    # Remove all non-alphanumeric characters
    name = re.sub(r'[^a-z0-9]', '', name)
    
    return name


def calculate_account_similarity(account_username: str, cse_name: str) -> float:
    """
    Calculate similarity between an account username and CSE name
    
    Args:
        account_username: Instagram/social media username
        cse_name: Official CSE name
        
    Returns:
        Similarity score (0.0 to 1.0)
    """
    # Normalize both names
    norm_username = normalize_name(account_username)
    norm_cse = normalize_name(cse_name)
    
    # Calculate similarity
    return similarity_ratio(norm_username, norm_cse)


def filter_accounts_by_similarity(
    accounts: List[Dict], 
    cse_name: str, 
    min_similarity: float = 0.3,
    max_similarity: float = 1.0
) -> List[Dict]:
    """
    Filter accounts based on lexicographic similarity to CSE name
    
    Args:
        accounts: List of account dictionaries with 'username' key
        cse_name: Official CSE name to compare against
        min_similarity: Minimum similarity threshold (0.0 to 1.0)
        max_similarity: Maximum similarity threshold (0.0 to 1.0)
        
    Returns:
        Filtered list of accounts with similarity scores added
    """
    filtered_accounts = []
    
    for account in accounts:
        username = account.get('username', '')
        
        # Calculate similarity
        similarity = calculate_account_similarity(username, cse_name)
        
        # Filter based on threshold
        if min_similarity <= similarity <= max_similarity:
            # Add similarity score to account
            account['similarity_score'] = round(similarity, 3)
            filtered_accounts.append(account)
    
    # Sort by similarity (highest first)
    filtered_accounts.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    return filtered_accounts


def get_abbreviation(name: str) -> str:
    """
    Get abbreviation from a name (e.g., "State Bank of India" -> "SBI")
    
    Args:
        name: Full name
        
    Returns:
        Abbreviation
    """
    # Split by spaces and take first letter of each word
    words = name.split()
    
    # Filter out common words
    skip_words = ['of', 'the', 'and', 'for', 'in', 'on', 'at']
    significant_words = [w for w in words if w.lower() not in skip_words]
    
    # Create abbreviation
    abbr = ''.join([w[0].upper() for w in significant_words if w])
    
    return abbr


def is_likely_phishing(account: Dict, cse_name: str) -> Dict[str, any]:
    """
    Analyze if an account is likely a phishing account
    
    Args:
        account: Account dictionary with username and display_name
        cse_name: Official CSE name
        
    Returns:
        Dictionary with analysis results
    """
    username = account.get('username', '').lower()
    display_name = account.get('display_name', '').lower()
    
    # Calculate similarities
    username_similarity = calculate_account_similarity(username, cse_name)
    display_similarity = calculate_account_similarity(display_name, cse_name)
    
    # Check for suspicious patterns
    suspicious_indicators = []
    
    # Pattern 1: Contains numbers (common in fake accounts)
    if re.search(r'\d{2,}', username):
        suspicious_indicators.append('multiple_numbers')
    
    # Pattern 2: Contains "official", "verified", "real" but not verified
    suspicious_words = ['official', 'verified', 'real', 'authentic']
    for word in suspicious_words:
        if word in username or word in display_name:
            suspicious_indicators.append(f'claims_{word}')
    
    # Pattern 3: Very similar but not exact (typosquatting)
    if 0.7 <= username_similarity < 0.95:
        suspicious_indicators.append('typosquatting_risk')
    
    # Pattern 4: Contains abbreviation with numbers
    abbr = get_abbreviation(cse_name).lower()
    if abbr in username and re.search(r'\d', username):
        suspicious_indicators.append('abbr_with_numbers')
    
    # Calculate risk score
    risk_score = 0.0
    
    # High similarity but not exact = suspicious
    if 0.6 <= username_similarity < 0.95:
        risk_score += 0.3
    
    # Has suspicious indicators
    risk_score += len(suspicious_indicators) * 0.15
    
    # Very low similarity = probably not related
    if username_similarity < 0.3:
        risk_score = 0.0
    
    risk_score = min(risk_score, 1.0)
    
    return {
        'username_similarity': round(username_similarity, 3),
        'display_similarity': round(display_similarity, 3),
        'suspicious_indicators': suspicious_indicators,
        'risk_score': round(risk_score, 3),
        'is_suspicious': risk_score > 0.4
    }
