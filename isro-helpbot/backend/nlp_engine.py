"""
NLP Engine for ISRO HelpBot

Provides:
- Query processing
- Context management (session context load/save)
- Response generation (extractive summarization + sources)
- Learning system hooks (apply simple relevance boosts from feedback)

This module intentionally keeps models lightweight (no external LLMs) so it
works offline for the hackathon. It uses the existing search engine and the
MongoDB database when available.
"""
from typing import Optional, Dict, Any, List, Tuple
import re
import math
from datetime import datetime
import uuid

from search_utils import search_engine

"""
Use a lightweight regex-based sentence tokenizer to avoid NLTK punkt dependency
which may not be available in the runtime environment.
"""
def sent_tokenize(text: str):
    if not text:
        return []
    # Split on sentence boundaries while keeping abbreviations simple
    return re.split(r'(?<=[.!?])\s+', text)

def simple_preprocess(text: str) -> List[str]:
    text = (text or '').lower()
    text = re.sub(r'[^\n\w\s]', ' ', text)
    tokens = [t for t in text.split() if len(t) > 2]
    return tokens

async def load_session_context(db, session_id: str) -> Dict:
    """Load session context from DB if available."""
    if db is None:
        return {}
    try:
        sess = await db.sessions.find_one({"session_id": session_id})
        if sess:
            return sess.get('context', {}) or {}
    except Exception:
        pass
    return {}

async def save_session_context(db, session_id: str, context: Dict) -> None:
    if db is None:
        return
    try:
        await db.sessions.update_one({"session_id": session_id}, {"$set": {"context": context, "last_active": datetime.now()}})
    except Exception:
        pass

async def apply_learning_boosts(db, scores: List[Tuple[Dict, float]]) -> List[Tuple[Dict, float]]:
    """Apply simple boosts based on feedback stored in the DB.

    We look for a collection `relevance_adjustments` with docs:
      { "content_id": <id>, "boost": <float> }

    and add the boost to the score. This is intentionally simple.
    """
    if db is None:
        return scores
    try:
        adjustments = await db.relevance_adjustments.find({}).to_list(length=None)
        boost_map = {a['content_id']: float(a.get('boost', 0.0)) for a in adjustments}
        new_scores = []
        for doc, score in scores:
            b = boost_map.get(doc.get('id'))
            if b:
                score = score + b
            new_scores.append((doc, score))
        return new_scores
    except Exception:
        return scores

def extractive_answer(query: str, documents: List[Tuple[Dict, float]], max_sentences: int = 2) -> str:
    """Build a short extractive answer from top documents.

    Score sentences by token overlap with the query and with the document's
    title. Return top `max_sentences` joined.
    """
    if not documents:
        return "I couldn't find relevant information in the indexed content. Could you rephrase or ask about a different topic?"

    query_tokens = set(simple_preprocess(query))
    candidate_sentences = []  # (score, sentence, source_url)

    def is_menu_like(s: str) -> bool:
        """Heuristics to detect menu/navigation/boilerplate lines."""
        if not s or len(s.strip()) < 10:
            return True
        low = s.lower()
        # common boilerplate phrases
        menu_tokens = ['skip to main', 'signup', 'sign up', 'login', 'logout', 'secondary menu',
                       'served by', 'copyright', 'privacy policy', 'terms & conditions', 'hyperlink policy',
                       'contact us', 'feedback', 'due to preventive maintenance', 'sitemap', 'help', 'catalog']
        if any(mt in low for mt in menu_tokens):
            return True
        # If the line contains many short tokens (likely menu items), mark as menu
        toks = [t for t in re.findall(r"\b\w+\b", s)]
        if not toks:
            return True
        short_frac = sum(1 for t in toks if len(t) <= 3) / len(toks)
        if short_frac > 0.6 and len(toks) >= 3:
            return True
        # Lines that are mostly uppercase tokens (menu bars)
        up_frac = sum(1 for t in toks if t.isupper()) / len(toks)
        if up_frac > 0.5 and len(toks) >= 3:
            return True
        # Lines that are lists separated by '|' or ' - ' are likely menus
        if '|' in s or ' - ' in s or ' / ' in s:
            # but allow if long and contains verbs
            if len(s) < 60:
                return True
        return False

    for doc, score in documents[:5]:
        content = doc.get('content', '')
        title = doc.get('title', '')
        url = doc.get('url', '')
        sentences = sent_tokenize(content)
        for s in sentences:
            # skip boilerplate/menu-like sentences early
            if is_menu_like(s):
                continue

            s_tokens = set(simple_preprocess(s))
            overlap = len(query_tokens.intersection(s_tokens))
            # small heuristic: title overlap counts more
            title_overlap = len(set(simple_preprocess(title)).intersection(s_tokens))
            s_score = overlap * 2 + title_overlap * 3 + (1 if len(s) < 400 else 0)
            if s_score > 0:
                candidate_sentences.append((s_score + score, s.strip(), url))

    # Fallback: if no sentence had overlap, try to find a sensible paragraph in top docs
    if not candidate_sentences:
        # examine top documents for a non-boilerplate paragraph containing query tokens
        for doc, _ in documents[:3]:
            content = doc.get('content', '') or ''
            # split into paragraphs and pick the first non-menu-like paragraph
            paras = [p.strip() for p in re.split(r'\n{1,}', content) if p.strip()]
            for p in paras:
                if is_menu_like(p):
                    continue
                if any(t in simple_preprocess(p) for t in query_tokens) and len(p) > 40:
                    return f"I found information that might help (source: {doc.get('url')}):\n\n{p[:800]}..."

        # as a last resort, return a polite fallback instead of raw menu/content
        return "I found relevant pages but couldn't extract a concise answer from them. Could you please rephrase the question or ask about a specific data product or feature?"

    # select top sentences
    candidate_sentences.sort(key=lambda x: x[0], reverse=True)
    selected = candidate_sentences[:max_sentences]
    pieces = []
    for sc, sent, url in selected:
        pieces.append(f"{sent} (source: {url})")

    return '\n\n'.join(pieces)

async def get_ai_response(question: str, session_id: str, db, content_database: Dict[str, Any]) -> str:
    """Main entry point for generating AI responses.

    Steps:
      - Load session context
      - Do lightweight intent/rule handling
      - Run search over indexed content
      - Apply learning boosts
      - Build extractive answer and update session context
    """
    q = (question or '').strip()
    q_lower = q.lower()

    # Quick rule-based intents (greetings etc.)
    if any(g in q_lower for g in ['hello', 'hi', 'hey', 'how are you', 'how do you do']):
        return "Hello! I'm MOSDAC's assistant. Ask me about our satellite data, products, or how to download datasets. How can I help today?"

    # Load context
    context = await load_session_context(db, session_id)

    # Query processing: normalize and optionally expand using context
    processed_query = q
    last_topic = context.get('last_topic')
    if last_topic and len(processed_query.split()) < 4:
        # short follow-up queries might be about last topic, expand
        processed_query = f"{last_topic} {processed_query}"

    # Gather documents to search (database + in-memory)
    docs = []
    if db is not None:
        try:
            db_content = await db.content.find({}).to_list(length=None)
            docs.extend(db_content)
        except Exception:
            pass
    # add memory content
    try:
        docs.extend(list(content_database.values()))
    except Exception:
        pass

    # Use the search engine to score docs
    scored = search_engine.calculate_tf_idf_score(processed_query, docs)

    # Apply learning boosts from DB
    scored = await apply_learning_boosts(db, scored)

    # Sort and take top results
    scored.sort(key=lambda x: x[1], reverse=True)

    # Build answer
    answer = extractive_answer(processed_query, scored, max_sentences=2)

    # Update context: record last topic as first few words of query
    try:
        topic = ' '.join(simple_preprocess(q)[:6])
        if topic:
            context['last_topic'] = topic
            context.setdefault('query_count', 0)
            context['query_count'] += 1
            await save_session_context(db, session_id, context)
    except Exception:
        pass

    return answer
