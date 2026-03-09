"""
Generate search keywords for phishing account detection using Gemini AI
"""
import os
import json
from typing import List
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai package not installed")
    print("Install it with: pip install google-generativeai")
    exit(1)

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)


class PhishingKeywordGenerator:
    """Generate search keywords for finding phishing accounts using Gemini AI"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the keyword generator
        
        Args:
            api_key: Gemini API key (if not provided, reads from GEMINI_API_KEY env var)
        """
        load_dotenv()
        
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY in .env file or pass as parameter")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use the latest available model
        # Try models in order of preference
        model_names = [
            'gemini-2.5-flash',      # Latest fast model
            'gemini-2.5-pro',        # Latest pro model
            'gemini-flash-latest',   # Generic latest flash
            'gemini-pro-latest',     # Generic latest pro
        ]
        
        self.model = None
        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                print(f"Using model: {model_name}")
                break
            except Exception as e:
                continue
        
        if not self.model:
            raise ValueError("Could not initialize any Gemini model. Please check your API key and available models.")
    
    def generate_keywords(self, cse_name: str, max_keywords: int = 20) -> List[str]:
        """
        Generate search keywords for finding phishing accounts
        
        Args:
            cse_name: Name of the Critical Sector Entity
            max_keywords: Maximum number of keywords to generate
            
        Returns:
            List of search keywords
        """
        prompt = f"""You are a cybersecurity expert specializing in phishing detection on social media platforms.

Given the Critical Sector Entity (CSE) name: "{cse_name}"

Generate a list of {max_keywords} search keywords that could be used to find potential phishing accounts impersonating this entity on Instagram, Twitter/X, and other social media platforms.

Consider the following patterns that phishers commonly use:
1. Exact name with slight variations (typos, extra characters)
2. Name with "official", "verified", "real", "authentic" added
3. Name with numbers or underscores added
4. Abbreviated versions of the name
5. Name with common misspellings
6. Name with country/region identifiers
7. Name with "support", "help", "customer service" added
8. Name with special characters or unicode lookalikes
9. Name variations in different languages if applicable
10. Common phishing indicators (prize, giveaway, etc.)

IMPORTANT: Return ONLY a JSON array of strings, nothing else. No explanations, no markdown, just the JSON array.

Example format:
["keyword1", "keyword2", "keyword3"]

Generate the keywords now:"""

        try:
            # Generate content using Gemini
            response = self.model.generate_content(prompt)
            
            # Extract the text response
            response_text = response.text.strip()
            
            # Try to parse as JSON
            try:
                # Remove markdown code blocks if present
                if response_text.startswith('```'):
                    # Extract content between ``` markers
                    lines = response_text.split('\n')
                    json_lines = []
                    in_code_block = False
                    for line in lines:
                        if line.strip().startswith('```'):
                            in_code_block = not in_code_block
                            continue
                        if in_code_block or (not line.strip().startswith('```')):
                            json_lines.append(line)
                    response_text = '\n'.join(json_lines).strip()
                
                keywords = json.loads(response_text)
                
                if isinstance(keywords, list):
                    # Filter and clean keywords
                    cleaned_keywords = []
                    for kw in keywords:
                        if isinstance(kw, str) and kw.strip():
                            cleaned_keywords.append(kw.strip())
                    
                    return cleaned_keywords[:max_keywords]
                else:
                    print(f"Warning: Response is not a list. Got: {type(keywords)}")
                    return []
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Response text: {response_text[:200]}...")
                
                # Fallback: try to extract keywords manually
                keywords = self._extract_keywords_fallback(response_text)
                return keywords[:max_keywords]
                
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                print(f"Error: Model not available. {error_msg}")
                print("\nTrying to list available models...")
                try:
                    models = genai.list_models()
                    print("\nAvailable models:")
                    for model in models:
                        if 'generateContent' in model.supported_generation_methods:
                            print(f"  - {model.name}")
                except:
                    pass
            else:
                print(f"Error generating keywords: {e}")
            return []
    
    def _extract_keywords_fallback(self, text: str) -> List[str]:
        """
        Fallback method to extract keywords if JSON parsing fails
        
        Args:
            text: Response text from Gemini
            
        Returns:
            List of extracted keywords
        """
        keywords = []
        
        # Try to find quoted strings
        import re
        quoted_pattern = r'"([^"]+)"'
        matches = re.findall(quoted_pattern, text)
        
        if matches:
            keywords.extend(matches)
        else:
            # Try to split by newlines and clean
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                # Remove numbering, bullets, etc.
                line = re.sub(r'^[\d\.\-\*\+]+\s*', '', line)
                if line and len(line) > 2 and len(line) < 100:
                    keywords.append(line)
        
        return keywords
    
    def generate_and_save(self, cse_name: str, output_file: str = None, max_keywords: int = 20) -> List[str]:
        """
        Generate keywords and save to JSON file
        
        Args:
            cse_name: Name of the CSE
            output_file: Output JSON file path (optional)
            max_keywords: Maximum number of keywords
            
        Returns:
            List of generated keywords
        """
        print(f"Generating phishing detection keywords for: {cse_name}")
        print(f"Using Gemini AI...")
        
        keywords = self.generate_keywords(cse_name, max_keywords)
        
        if keywords:
            print(f"\n✅ Generated {len(keywords)} keywords:")
            for i, kw in enumerate(keywords, 1):
                print(f"  {i}. {kw}")
            
            # Save to file if specified
            if output_file:
                data = {
                    'cse_name': cse_name,
                    'keywords': keywords,
                    'total_keywords': len(keywords)
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"\n💾 Keywords saved to: {output_file}")
        else:
            print("\n❌ No keywords generated")
        
        return keywords


def main():
    """Main function for command-line usage"""
    import sys
    
    # Check if CSE name provided
    if len(sys.argv) < 2:
        print("Usage: python utils/generate_search_keywords.py <CSE_NAME>")
        print("\nExample:")
        print("  python utils/generate_search_keywords.py 'State Bank of India'")
        print("\nMake sure to set GEMINI_API_KEY in your .env file")
        return
    
    cse_name = ' '.join(sys.argv[1:])
    
    try:
        # Initialize generator
        generator = PhishingKeywordGenerator()
        
        # Generate keywords
        output_file = f"keywords_{cse_name.lower().replace(' ', '_')}.json"
        keywords = generator.generate_and_save(cse_name, output_file, max_keywords=20)
        
        if keywords:
            print("\n" + "="*60)
            print("You can now use these keywords in your Instagram scraper!")
            print("="*60)
        
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nTo fix this:")
        print("1. Get a Gemini API key from: https://makersuite.google.com/app/apikey")
        print("2. Add it to your .env file:")
        print("   GEMINI_API_KEY=your_api_key_here")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
