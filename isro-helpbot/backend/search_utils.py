"""
Advanced search utilities for MOSDAC content search
"""

import re
import math
from typing import List, Dict, Tuple, Set
from collections import Counter, defaultdict
# For reliability in constrained environments we disable NLTK by default.
# If you want NLTK features, set the environment variable USE_NLTK=1 and
# ensure the required data (punkt, stopwords) is installed.
import os
USE_NLTK = os.getenv('USE_NLTK', '0') == '1'
NLTK_AVAILABLE = False
if USE_NLTK:
    try:
        import nltk
        from nltk.corpus import stopwords
        from nltk.stem import PorterStemmer
        NLTK_AVAILABLE = True
    except Exception:
        NLTK_AVAILABLE = False

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

DEFAULT_STOPWORDS = set([
    'the', 'and', 'for', 'that', 'with', 'this', 'from', 'are', 'was', 'were',
    'have', 'has', 'had', 'not', 'but', 'you', 'your', 'our', 'their', 'they',
    'them', 'can', 'will', 'would', 'should', 'could', 'about', 'what', 'which',
    'when', 'where', 'how', 'why', 'all', 'any', 'each', 'other', 'more', 'some'
])

# We avoid automatic NLTK downloads at import time to prevent noisy logs.

class SearchEngine:
    def __init__(self):
        # PorterStemmer may not be available if NLTK failed to import
        self.stemmer = PorterStemmer() if NLTK_AVAILABLE else None
        try:
            self.stop_words = set(stopwords.words('english')) if NLTK_AVAILABLE else set()
        except Exception:
            self.stop_words = set()
        # Add domain-specific stop words
        self.stop_words.update(['mosdac', 'satellite', 'data', 'service', 'services', 'isro'])

    def preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for search indexing"""
        try:
            # Convert to lowercase
            text = (text or '').lower()
            # Remove special characters and extra whitespace
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            # Tokenize using nltk if available, otherwise simple split
            if NLTK_AVAILABLE:
                try:
                    tokens = nltk.word_tokenize(text)
                except Exception:
                    tokens = re.findall(r"\\b\\w+\\b", text)
            else:
                tokens = re.findall(r"\\b\\w+\\b", text)

            # Remove stop words and stem if stemmer is available
            processed_tokens: List[str] = []
            for token in tokens:
                if token not in self.stop_words and len(token) > 2:
                    t = token
                    if self.stemmer:
                        try:
                            t = self.stemmer.stem(token)
                        except Exception:
                            t = token
                    processed_tokens.append(t)

            return processed_tokens
        except Exception as e:
            print(f"NLTK preprocessing failed: {e}, falling back to simple processing")
            # Fallback: simple split and filter
            text2 = (text or '').lower()
            text2 = re.sub(r'[^\w\s]', ' ', text2)
            tokens = re.findall(r"\\b\\w+\\b", text2)
            return [token for token in tokens if len(token) > 2 and token not in self.stop_words]

    def calculate_tf_idf_score(self, query: str, documents: List[Dict]) -> List[Tuple[Dict, float]]:
        """Calculate TF-IDF scores for documents against query"""
        if not documents:
            return []

        # Prepare document texts
        doc_texts = []
        doc_metadata = []

        for doc in documents:
            content = doc.get('content', '')
            title = doc.get('title', '')
            # Combine title and content with title having higher weight
            combined_text = f"{title} {title} {content}"  # Title appears twice for higher weight
            doc_texts.append(combined_text)
            doc_metadata.append(doc)

        try:
            # Pre-check tokenization to avoid empty-vocabulary errors
            tokenized_docs = [self.preprocess_text(t) for t in doc_texts]
            total_tokens = sum(len(td) for td in tokenized_docs)
            if total_tokens == 0:
                # Nothing left after preprocessing; use fallback scoring
                # (this commonly happens when documents are very short or
                # consist only of stop words)
                # print a debug-level message instead of an alarming error
                print("TF-IDF skipped: no tokens after preprocessing; using simple scoring")
                return self.simple_score(query, documents)

            # Create TF-IDF vectorizer. Provide tokenizer that returns list of tokens
            # from the raw string, using our preprocess_text function.
            vectorizer = TfidfVectorizer(
                tokenizer=self.preprocess_text,
                preprocessor=None,
                token_pattern=None,  # ignored when tokenizer is provided
                max_features=1000
            )

            # Fit and transform documents
            tfidf_matrix = vectorizer.fit_transform(doc_texts)

            # Transform query
            query_vector = vectorizer.transform([query])

            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, tfidf_matrix)[0]

            # Combine with metadata
            results = []
            for i, similarity in enumerate(similarities):
                results.append((doc_metadata[i], float(similarity)))

            return results

        except Exception as e:
            print(f"TF-IDF calculation failed, falling back to simple scoring: {e}")
            # Fallback to simple scoring
            return self.simple_score(query, documents)

    def simple_score(self, query: str, documents: List[Dict]) -> List[Tuple[Dict, float]]:
        """Simple scoring fallback when TF-IDF fails"""
        results = []
        query_lower = query.lower()
        query_words = set(self.preprocess_text(query))

        for doc in documents:
            score = 0.0
            content = doc.get('content', '').lower()
            title = doc.get('title', '').lower()

            # Title matches (highest weight)
            if query_lower in title:
                score += 10.0
            for word in query_words:
                if word in title:
                    score += 5.0

            # Content matches
            if query_lower in content:
                score += 3.0
            for word in query_words:
                if word in content:
                    score += 1.0

            # Exact phrase bonus
            if query_lower in content:
                score += 2.0

            # Length normalization
            content_length = len(content.split())
            if content_length > 0:
                score = score / math.log(content_length + 1)

            results.append((doc, score))

        return results

    def apply_filters(self, documents: List[Dict], filters: Dict) -> List[Dict]:
        """Apply advanced filters to documents"""
        filtered_docs = []

        for doc in documents:
            include_doc = True

            # Content type filter
            if 'content_type' in filters and filters['content_type']:
                if doc.get('content_type') != filters['content_type']:
                    include_doc = False

            # Date range filters
            if include_doc and ('date_from' in filters or 'date_to' in filters):
                indexed_date = doc.get('indexed_at')
                if indexed_date:
                    try:
                        if isinstance(indexed_date, str):
                            doc_date = indexed_date.split('T')[0]  # Get date part
                        else:
                            doc_date = indexed_date.strftime('%Y-%m-%d')

                        if 'date_from' in filters and filters['date_from']:
                            if doc_date < filters['date_from']:
                                include_doc = False

                        if 'date_to' in filters and filters['date_to']:
                            if doc_date > filters['date_to']:
                                include_doc = False
                    except Exception as e:
                        print(f"Date filtering error: {e}")

            # Word count filters
            if include_doc and ('min_words' in filters or 'max_words' in filters):
                word_count = doc.get('word_count', 0)

                if 'min_words' in filters and filters['min_words']:
                    if word_count < int(filters['min_words']):
                        include_doc = False

                if 'max_words' in filters and filters['max_words']:
                    if word_count > int(filters['max_words']):
                        include_doc = False

            if include_doc:
                filtered_docs.append(doc)

        return filtered_docs

    def search(self, query: str, documents: List[Dict], filters: Dict = None,
               limit: int = 20, offset: int = 0) -> Dict:
        """Perform comprehensive search with ranking and filtering"""
        if not query.strip():
            return {"results": [], "total": 0}

        # Apply filters first
        if filters:
            filtered_docs = self.apply_filters(documents, filters)
        else:
            filtered_docs = documents

        if not filtered_docs:
            return {"results": [], "total": 0}

        # Calculate scores
        scored_results = self.calculate_tf_idf_score(query, filtered_docs)

        # Sort by score (descending)
        scored_results.sort(key=lambda x: x[1], reverse=True)

        # Apply pagination
        total_results = len(scored_results)
        start_idx = max(0, offset)
        end_idx = min(start_idx + limit, total_results)
        paginated_results = scored_results[start_idx:end_idx]

        # Format results
        results = []
        for doc, score in paginated_results:
            result = {
                "id": doc.get("id"),
                "title": doc.get("title", "Untitled"),
                "content": doc.get("content", "")[:500] + "..." if len(doc.get("content", "")) > 500 else doc.get("content", ""),
                "url": doc.get("url", ""),
                "content_type": doc.get("content_type", "webpage"),
                "indexed_at": doc.get("indexed_at"),
                "relevance_score": round(score, 3),
                "word_count": doc.get("word_count", 0)
            }
            results.append(result)

        return {
            "results": results,
            "total": total_results,
            "query": query,
            "offset": start_idx,
            "limit": len(results)
        }

# Global search engine instance
search_engine = SearchEngine()