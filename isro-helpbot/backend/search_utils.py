"""
Advanced search utilities for MOSDAC content search
"""

import re
import math
from typing import List, Dict, Tuple, Set
from collections import Counter, defaultdict
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
    except Exception:
        print("Warning: Could not download NLTK punkt tokenizer")

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        nltk.download('stopwords', quiet=True)
    except Exception:
        print("Warning: Could not download NLTK stopwords")

class SearchEngine:
    def __init__(self):
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        # Add domain-specific stop words
        self.stop_words.update(['mosdac', 'satellite', 'data', 'service', 'services', 'isro'])

    def preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for search indexing"""
        try:
            # Convert to lowercase
            text = text.lower()

            # Remove special characters and extra whitespace
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            # Tokenize
            tokens = nltk.word_tokenize(text)

            # Remove stop words and stem
            processed_tokens = []
            for token in tokens:
                if token not in self.stop_words and len(token) > 2:
                    stemmed = self.stemmer.stem(token)
                    processed_tokens.append(stemmed)

            return processed_tokens
        except Exception as e:
            print(f"NLTK preprocessing failed: {e}, falling back to simple processing")
            # Fallback: simple split and filter
            text = text.lower()
            text = re.sub(r'[^\w\s]', ' ', text)
            tokens = text.split()
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
            # Create TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                preprocessor=self.preprocess_text,
                tokenizer=lambda x: x,  # Already preprocessed
                token_pattern=None,  # Disable default tokenization
                max_features=1000
            )

            # Fit and transform documents
            tfidf_matrix = vectorizer.fit_transform(doc_texts)

            # Transform query
            query_processed = self.preprocess_text(query)
            query_vector = vectorizer.transform([query_processed])

            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, tfidf_matrix)[0]

            # Combine with metadata
            results = []
            for i, similarity in enumerate(similarities):
                results.append((doc_metadata[i], float(similarity)))

            return results

        except Exception as e:
            print(f"TF-IDF calculation failed: {e}")
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