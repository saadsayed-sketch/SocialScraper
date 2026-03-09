"""
Utility modules for social media scraper
"""
from .similarity import (
    levenshtein_distance,
    similarity_ratio,
    calculate_account_similarity,
    filter_accounts_by_similarity,
    is_likely_phishing,
    get_abbreviation
)

__all__ = [
    'levenshtein_distance',
    'similarity_ratio',
    'calculate_account_similarity',
    'filter_accounts_by_similarity',
    'is_likely_phishing',
    'get_abbreviation'
]
