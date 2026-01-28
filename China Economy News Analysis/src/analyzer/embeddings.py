"""Topic vector embedding generation for news articles.

Uses sentence-transformers for generating embeddings from article text.
Falls back to TF-IDF based vectors if sentence-transformers is not available.
"""

import json
import logging
from typing import Optional
import hashlib

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.database.models import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Embedding dimension for fallback TF-IDF approach
TFIDF_DIMENSION = 384

# Global model cache
_embedding_model = None
_use_sentence_transformers = None


def _check_sentence_transformers() -> bool:
    """Check if sentence-transformers is available."""
    global _use_sentence_transformers
    if _use_sentence_transformers is not None:
        return _use_sentence_transformers

    try:
        from sentence_transformers import SentenceTransformer
        _use_sentence_transformers = True
        logger.info("sentence-transformers is available")
    except ImportError:
        _use_sentence_transformers = False
        logger.warning("sentence-transformers not installed, using TF-IDF fallback")

    return _use_sentence_transformers


def _get_embedding_model():
    """Get or create the embedding model."""
    global _embedding_model

    if _embedding_model is not None:
        return _embedding_model

    if _check_sentence_transformers():
        from sentence_transformers import SentenceTransformer
        # Use a multilingual model that works well with Chinese
        _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("Loaded sentence-transformers model")
    else:
        _embedding_model = None

    return _embedding_model


def generate_tfidf_vector(text: str, dimension: int = TFIDF_DIMENSION) -> list:
    """Generate a simple hash-based pseudo-vector for text.

    This is a fallback when sentence-transformers is not available.
    Uses character n-grams and hashing to create a fixed-dimension vector.
    """
    if not text:
        return [0.0] * dimension

    # Normalize text
    text = text.lower().strip()

    # Generate character n-grams (2-4 grams)
    ngrams = []
    for n in range(2, 5):
        for i in range(len(text) - n + 1):
            ngrams.append(text[i:i+n])

    # Create vector using hashing
    vector = [0.0] * dimension

    for ngram in ngrams:
        # Hash the ngram to get bucket index
        h = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
        idx = h % dimension
        # Use another hash for sign
        sign = 1 if (h // dimension) % 2 == 0 else -1
        vector[idx] += sign

    # Normalize vector
    norm = sum(v * v for v in vector) ** 0.5
    if norm > 0:
        vector = [v / norm for v in vector]

    return vector


def generate_embedding(text: str, max_length: int = 512) -> list:
    """Generate embedding vector for text.

    Uses sentence-transformers if available, otherwise falls back to TF-IDF.

    Args:
        text: Input text (Chinese article content)
        max_length: Maximum text length to process

    Returns:
        List of floats representing the embedding vector
    """
    if not text:
        return []

    # Truncate text if needed
    text = text[:max_length * 2]  # Rough character limit for Chinese

    model = _get_embedding_model()

    if model is not None:
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating sentence embedding: {e}")
            return generate_tfidf_vector(text)
    else:
        return generate_tfidf_vector(text)


def generate_topic_vector(news_id: int) -> Optional[list]:
    """Generate and store topic vector for a news article.

    Args:
        news_id: ID of the news article

    Returns:
        Generated embedding vector or None if failed
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT original_title, original_content, summary
            FROM news
            WHERE id = ?
        """, (news_id,))

        row = cursor.fetchone()
        if not row:
            logger.warning(f"News {news_id} not found")
            return None

        # Combine title and content for embedding
        title = row["original_title"] or ""
        content = row["original_content"] or ""
        summary = row["summary"] or ""

        # Use summary + title if available, otherwise use content
        if summary:
            text = f"{title} {summary}"
        else:
            text = f"{title} {content[:1000]}"

        embedding = generate_embedding(text)

        if embedding:
            # Store in database
            cursor.execute("""
                UPDATE news
                SET topic_vector = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(embedding), news_id))
            conn.commit()
            logger.debug(f"Generated topic vector for news {news_id} (dim={len(embedding)})")

        return embedding

    except Exception as e:
        logger.error(f"Error generating topic vector for news {news_id}: {e}")
        return None

    finally:
        conn.close()


def backfill_topic_vectors(limit: int = 100) -> dict:
    """Generate topic vectors for news items that don't have them.

    Args:
        limit: Maximum number of items to process

    Returns:
        Summary dict with counts
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id FROM news
            WHERE topic_vector IS NULL
                AND analyzed_at IS NOT NULL
            ORDER BY importance_score DESC
            LIMIT ?
        """, (limit,))

        news_ids = [row["id"] for row in cursor.fetchall()]
        conn.close()

        success_count = 0
        error_count = 0

        for news_id in news_ids:
            result = generate_topic_vector(news_id)
            if result:
                success_count += 1
            else:
                error_count += 1

        logger.info(f"Backfilled topic vectors: {success_count} success, {error_count} errors")
        return {
            "processed": len(news_ids),
            "success": success_count,
            "errors": error_count,
        }

    except Exception as e:
        logger.error(f"Error in backfill: {e}")
        return {"processed": 0, "success": 0, "errors": 0}


def main():
    """Run backfill from command line."""
    result = backfill_topic_vectors(limit=50)
    print(f"Backfill complete: {result}")


if __name__ == "__main__":
    main()
