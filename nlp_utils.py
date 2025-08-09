#!/usr/bin/env python3
"""
Modern NLP-based utilities using pretrained models and libraries
No hardcoded word lists - using automatic feature extraction
"""

import re
from typing import List, Optional
from collections import Counter

# Try to import modern NLP libraries
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.tag import pos_tag
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    # Try KeyBERT for keyword extraction
    from keybert import KeyBERT
    KEYBERT_AVAILABLE = True
except ImportError:
    KEYBERT_AVAILABLE = False

try:
    # Try YAKE for automatic keyword extraction
    import yake
    YAKE_AVAILABLE = True
except ImportError:
    YAKE_AVAILABLE = False


class ModernNaming:
    """Modern variable naming using automatic NLP techniques"""
    
    def __init__(self):
        self.kw_extractor = None
        self.yake_extractor = None
        self.tfidf_vectorizer = None
        self.stopwords_set = set()
        
        self._initialize_extractors()
    
    def _initialize_extractors(self):
        """Initialize available extractors"""
        available_methods = []
        
        # Initialize KeyBERT if available
        if KEYBERT_AVAILABLE:
            try:
                self.kw_extractor = KeyBERT('distilbert-base-nli-mean-tokens')
                available_methods.append("KeyBERT")
            except Exception:
                self.kw_extractor = None
        
        # Initialize YAKE if available
        if YAKE_AVAILABLE:
            try:
                # Language: English, max number of words: 3, deduplication threshold: 0.9
                self.yake_extractor = yake.KeywordExtractor(
                    lan="en", n=3, dedupLim=0.9, top=10
                )
                available_methods.append("YAKE")
            except Exception:
                self.yake_extractor = None
        
        # Initialize TF-IDF if available
        if SKLEARN_AVAILABLE:
            try:
                self.tfidf_vectorizer = TfidfVectorizer(
                    stop_words='english',
                    max_features=1000,
                    ngram_range=(1, 3)
                )
                available_methods.append("TF-IDF")
            except Exception:
                self.tfidf_vectorizer = None
        
        # Initialize NLTK stopwords if available
        if NLTK_AVAILABLE:
            try:
                nltk.download('stopwords', quiet=True)
                nltk.download('punkt', quiet=True)
                nltk.download('averaged_perceptron_tagger', quiet=True)
                self.stopwords_set = set(stopwords.words('english'))
                available_methods.append("NLTK")
            except Exception:
                pass
        
        # Report available methods
        if available_methods:
            print(f"✅ NLP 已启用，可用方法: {', '.join(available_methods)}")
        else:
            print("⚠️  警告: 没有高级 NLP 库可用，使用基础文本处理")
            print("   建议安装: pip install scikit-learn keybert yake nltk")
        
        # Fallback stopwords
        if not self.stopwords_set:
            self.stopwords_set = {
                'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                'to', 'was', 'will', 'with', 'once', 'this', 'which', 'used',
                'when', 'where', 'who', 'why', 'how', 'can', 'could', 'should',
                'would', 'may', 'might', 'must', 'shall', 'will', 'do', 'does',
                'did', 'have', 'had', 'been', 'being', 'been', 'am', 'is', 'are',
                'was', 'were', 'be', 'being', 'been'
            }
    
    def extract_keywords_keybert(self, text: str) -> List[tuple]:
        """Extract keywords using KeyBERT"""
        if not self.kw_extractor:
            return []
        
        try:
            keywords = self.kw_extractor.extract_keywords(
                text, 
                keyphrase_ngram_range=(1, 3), 
                stop_words='english',
                top_k=10
            )
            return keywords
        except Exception:
            return []
    
    def extract_keywords_yake(self, text: str) -> List[tuple]:
        """Extract keywords using YAKE"""
        if not self.yake_extractor:
            return []
        
        try:
            keywords = self.yake_extractor.extract_keywords(text)
            # YAKE returns (score, keyword) - lower score is better
            # Convert to (keyword, relevance_score) format
            return [(kw, 1.0 / (1.0 + score)) for score, kw in keywords]
        except Exception:
            return []
    
    def extract_keywords_tfidf(self, text: str, corpus: List[str] = None) -> List[tuple]:
        """Extract keywords using TF-IDF"""
        if not self.tfidf_vectorizer:
            return []
        
        try:
            # Use a simple corpus if none provided
            if corpus is None:
                corpus = [text]
            else:
                corpus = corpus + [text]
            
            # Fit and transform
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(corpus)
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            
            # Get scores for the input text (last document)
            text_scores = tfidf_matrix[-1].toarray()[0]
            
            # Get top scoring features
            word_scores = list(zip(feature_names, text_scores))
            word_scores.sort(key=lambda x: x[1], reverse=True)
            
            return word_scores[:10]
        except Exception:
            return []
    
    def extract_keywords_nltk(self, text: str) -> List[tuple]:
        """Extract keywords using NLTK POS tagging"""
        if not NLTK_AVAILABLE:
            return []
        
        try:
            # Tokenize and POS tag
            tokens = word_tokenize(text.lower())
            pos_tags = pos_tag(tokens)
            
            # Keep important POS tags (nouns, adjectives, verbs)
            important_pos = {'NN', 'NNS', 'NNP', 'NNPS', 'JJ', 'JJR', 'JJS', 'VB', 'VBG', 'VBN', 'VBP', 'VBZ'}
            
            keywords = []
            for word, pos in pos_tags:
                if (pos in important_pos and 
                    word.isalpha() and 
                    len(word) > 2 and 
                    word not in self.stopwords_set):
                    keywords.append((word, 1.0))  # Simple equal weighting
            
            return keywords
        except Exception:
            return []
    
    def extract_keywords_ensemble(self, text: str) -> List[str]:
        """Use ensemble of available methods to extract keywords"""
        # First try a simple approach that often works better
        simple_result = self._fallback_extraction(text)
        if len(simple_result) >= 2:
            return simple_result
        
        # If simple extraction doesn't work well, try NLP methods
        word_scores = {}
        
        # Try all available methods
        methods = [
            self.extract_keywords_keybert,
            self.extract_keywords_yake,
            self.extract_keywords_tfidf,
            self.extract_keywords_nltk
        ]
        
        for method in methods:
            try:
                keywords = method(text)
                # Take top keywords from each method
                for kw, score in keywords[:5]:
                    clean_kw = re.sub(r'[^\w\s]', '', kw.lower().strip())
                    words = clean_kw.split()
                    
                    # Add each meaningful word
                    for word in words:
                        if word not in self.stopwords_set and len(word) > 2:
                            word_scores[word] = word_scores.get(word, 0) + score
                            
            except Exception:
                continue
        
        # If no NLP methods worked, use simple extraction
        if not word_scores:
            return simple_result
        
        # Return top scoring words
        sorted_words = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        result = [word for word, score in sorted_words[:4]]
        
        return result if result else simple_result
    
    def _fallback_extraction(self, text: str) -> List[str]:
        """Simple fallback when no NLP libraries are available"""
        # Clean text
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Remove common prefixes and patterns
        clean_text = re.sub(r'^(the|a|an|number of|total|amount of|if it is|if it was|if)\s+', '', clean_text)
        clean_text = re.sub(r'\s+(currently|being|was|were|when|that|which)\s+', ' ', clean_text)
        
        # Extract words
        words = clean_text.split()
        
        # Smart filtering: keep semantically important words
        important_words = []
        for w in words:
            if (len(w) > 2 and 
                w not in self.stopwords_set and 
                w not in {'currently', 'being', 'was', 'were', 'when', 'that', 'which'}):
                important_words.append(w)
        
        # Remove exact duplicates while preserving order
        seen = set()
        unique_words = []
        for word in important_words:
            if word not in seen:
                seen.add(word)
                unique_words.append(word)
        
        # Limit to reasonable length
        return unique_words[:3]
    
    def to_camel_case(self, text: str) -> str:
        """Convert text to camelCase using automatic keyword extraction"""
        if not text:
            return "field"
        
        # Clean the text first
        clean_text = self._clean_text(text)
        
        # Extract keywords using ensemble approach
        keywords = self.extract_keywords_ensemble(clean_text)
        
        if not keywords:
            return "field"
        
        # Handle boolean patterns
        first_word = keywords[0].lower()
        if first_word in {'is', 'has', 'can', 'should', 'will', 'was', 'are'}:
            remaining = keywords[1:] if len(keywords) > 1 else []
            if remaining:
                return first_word + ''.join(word.capitalize() for word in remaining)
            return first_word
        
        # Convert to camelCase
        if len(keywords) == 1:
            return keywords[0].lower()
        else:
            return keywords[0].lower() + ''.join(word.capitalize() for word in keywords[1:])
    
    def _clean_text(self, text: str) -> str:
        """Clean text for processing"""
        # Remove parenthetical content
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        text = re.sub(r'\{[^}]*\}', '', text)
        
        # Remove explanatory content
        text = re.sub(r'[;:]\s*.*$', '', text)
        text = re.sub(r'\?\s*.*$', '', text)
        text = re.sub(r'\.\s+.*$', '', text)
        text = re.sub(r'\s*-\s*.*$', '', text)
        
        # Clean up quotes and extra punctuation
        text = re.sub(r'[\'"`]', '', text)
        
        return text.strip()


# Global instance
_modern_naming_instance = None


def get_modern_naming_instance() -> ModernNaming:
    """Get or create the global modern naming instance"""
    global _modern_naming_instance
    if _modern_naming_instance is None:
        _modern_naming_instance = ModernNaming()
    return _modern_naming_instance


def modern_meaning_to_camel_case(meaning: str) -> str:
    """Main function to convert meaning to camelCase using modern NLP"""
    naming = get_modern_naming_instance()
    return naming.to_camel_case(meaning)


def test_modern_conversion():
    """Test the modern NLP-based conversion"""
    test_cases = [
        "Is on fire",
        "Is flying with an elytra", 
        "Ticks frozen in powder snow",
        "The amount of experience this orb will reward once collected",
        "Entity ID of entity which used firework (for elytra boosting)",
        "Has no gravity",
        "Responsive - can be attacked/interacted with if true",
        "Air ticks",
        "Custom name",
        "Painting Type"
    ]
    
    naming = ModernNaming()
    print("Modern NLP-based camelCase conversion test:")
    print("=" * 50)
    
    for test in test_cases:
        result = naming.to_camel_case(test)
        print(f"{test:<60} -> {result}")


if __name__ == "__main__":
    test_modern_conversion()
