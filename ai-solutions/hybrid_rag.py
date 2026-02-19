#!/usr/bin/env python3
"""
Uses local Qdrant instance for vector storage
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    MultiVectorConfig,
    MultiVectorComparator,
    HnswConfigDiff,
    Filter,
    FieldCondition,
    MatchValue,
    Modifier,
    SparseVectorParams,
    SparseVector,
    Prefetch
)

from fastembed import TextEmbedding, LateInteractionTextEmbedding, SparseTextEmbedding, SparseEmbedding
from fastembed.common.types import NumpyArray
from datetime import datetime, timezone
import logging
import uuid
import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file if present
load_dotenv(find_dotenv())


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


SPARSE_VECTOR_NAME = "text"
DENSE_VECTOR_NAME = "dense"
RERANKER_VECTOR_NAME = "colbertv2.0"

# Initialize Qdrant client using config
# Fastapi service connects to Qdrant server on port 6333, not the Fastapi service port
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

# Collection name from config
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "hbrag_docs")

# Initialize embedding model based on system tier
RAG_TIER = os.getenv("RAG_TIER", "lite").lower()

# Model configurations: name -> (model_path, vector_dimensions)
MODEL_CONFIGS = {
    "lite": ("sentence-transformers/all-MiniLM-L6-v2", 384),
    "max": ("michaelfeil/embeddinggemma-300m", 768),
}
EMBED_MODEL_NAME, VECTOR_SIZE = MODEL_CONFIGS.get(RAG_TIER, MODEL_CONFIGS["lite"])


qdrant_client = AsyncQdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    https=False,  # Use HTTP, not HTTPS for local connection
)

logger.info(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")

dense_embedding_model = TextEmbedding(EMBED_MODEL_NAME,cache_dir="./embed_models")
bm25_embedding_model = SparseTextEmbedding("Qdrant/bm25",cache_dir="./embed_models")
late_embedding_model = LateInteractionTextEmbedding("colbert-ir/colbertv2.0",cache_dir="./embed_models")


def generate_vectors(text) -> tuple[NumpyArray, SparseEmbedding, NumpyArray]:
    dense_embeddings = next(dense_embedding_model.embed(text))
    bm25_embeddings = next(bm25_embedding_model.embed(text))
    late_interaction_embeddings = next(late_embedding_model.embed(text))

    return dense_embeddings, bm25_embeddings, late_interaction_embeddings


def get_collection_name(project_slug=None, source=None):
    """Get collection name based on project slug and source"""
    if project_slug:
        return f"hbrag_project_{project_slug}"
    elif source == "global_knowledgebase":
        return "hbrag_global_kb"
    return COLLECTION_NAME


async def create_collection(collection_name: str):
    dense_embeddings, _, late_embeddings = generate_vectors("Initialize to get vector sizes")
    dense_verctor_size = len(dense_embeddings.tolist())
    reranker_vector_size = len(late_embeddings[0].tolist())

    logger.info(f"Creating collection '{collection_name}' with dense vector size {dense_verctor_size} and reranker vector size {reranker_vector_size}")

    await qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config={
            DENSE_VECTOR_NAME: VectorParams(
                size=dense_verctor_size,
                distance=Distance.COSINE,
            ),
            RERANKER_VECTOR_NAME: VectorParams(
                size=reranker_vector_size,
                distance=Distance.COSINE,
                multivector_config=MultiVectorConfig(
                    comparator=MultiVectorComparator.MAX_SIM,
                ),
                hnsw_config=HnswConfigDiff(m=0),  #  Disable HNSW for reranking
            ),
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: SparseVectorParams(modifier=Modifier.IDF)
        },
    )

    # await qdrant_client.create_collection(
    #     collection_name=collection_name,
    #     vectors_config={
    #         DENSE_VECTOR_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
    #     },
    #     sparse_vectors_config={
    #         SPARSE_VECTOR_NAME: SparseVectorParams(modifier=Modifier.IDF)
    #     },
    # )


async def ensure_collection_exists(collection_name):
    """Ensure a collection exists with HYBRID vector support (dense + sparse) and correct dimensions"""
    try:
        collections = await qdrant_client.get_collections()
        collection_exists = any(
            col.name == collection_name for col in collections.collections
        )

        if collection_exists:
            # Verify the existing collection has the correct vector dimensions
            try:
                collection_info = await qdrant_client.get_collection(collection_name)

                # Check if dense vector config exists and has correct dimensions
                if DENSE_VECTOR_NAME in collection_info.config.params.vectors:
                    existing_size = collection_info.config.params.vectors[
                        DENSE_VECTOR_NAME
                    ].size

                    if existing_size != VECTOR_SIZE:
                        logger.warning(
                            f"⚠️  Collection '{collection_name}' has WRONG dimensions!"
                        )
                        logger.warning(
                            f"   Expected: {VECTOR_SIZE}, Found: {existing_size}"
                        )
                        logger.warning(
                            "   🔄 Recreating collection with correct dimensions..."
                        )

                        # Delete the old collection with wrong dimensions
                        await qdrant_client.delete_collection(collection_name)
                        logger.info(
                            "   ✅ Deleted old collection with wrong dimensions"
                        )

                        # Create new collection with correct dimensions
                        await create_collection(collection_name)
                        logger.info(
                            f"   ✅ Created new collection '{collection_name}' with {VECTOR_SIZE} dimensions"
                        )
                    else:
                        logger.info(
                            f"✅ Using existing collection '{collection_name}' (dimensions: {existing_size} ✓)"
                        )
                else:
                    logger.warning(
                        f"⚠️  Collection '{collection_name}' missing dense vector config, recreating..."
                    )
                    await qdrant_client.delete_collection(collection_name)
                    await create_collection(collection_name)
                    logger.info(
                        f"✅ Recreated collection '{collection_name}' with correct config"
                    )

            except Exception as verify_error:
                logger.error(f"Failed to verify collection dimensions: {verify_error}")
                logger.info(f"Recreating collection '{collection_name}' to be safe...")
                try:
                    await qdrant_client.delete_collection(collection_name)
                except Exception as e:
                    logger.error(
                        f"Error while deleting {collection_name}. Error: ", str(e)
                    )
                    pass
                await create_collection(collection_name)
                logger.info(f"✅ Recreated collection '{collection_name}'")
        else:
            # Collection doesn't exist, create it
            await create_collection(collection_name)
            logger.info(
                f"✅ Created new hybrid Qdrant collection '{collection_name}' ({VECTOR_SIZE} dimensions)"
            )
        return True
    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error(
            f"❌ Failed to initialize Qdrant collection '{collection_name}': {e}"
        )
        return False


async def get_collections_info():
    """Get all available collections with project information"""
    try:
        collections = await qdrant_client.get_collections()
        collections_info = []

        for col in collections.collections:
            try:
                collection_info = await qdrant_client.get_collection(col.name)
                point_count = collection_info.points_count

                # Determine if this is a project collection
                is_project_collection = col.name.startswith("hbrag_project_")
                project_slug = None
                if is_project_collection:
                    project_slug = col.name.replace("hbrag_project_", "")

                collections_info.append(
                    {
                        "name": col.name,
                        "document_count": point_count,
                        "is_project_collection": is_project_collection,
                        "project_slug": project_slug,
                    }
                )
            except Exception as e:
                logger.warning(f"Could not get info for collection {col.name}: {e}")
                collections_info.append(
                    {
                        "name": col.name,
                        "document_count": "unknown",
                        "is_project_collection": col.name.startswith(
                            "hbrag_project_"
                        ),
                        "project_slug": col.name.replace("hbrag_project_", "")
                        if col.name.startswith("hbrag_project_")
                        else None,
                    }
                )

        return collections_info

    except Exception as e:
        raise e


async def get_health():
    """Health check endpoint"""
    try:
        # Test basic connection by getting collections list
        collections = await qdrant_client.get_collections()
        collection_exists = any(
            col.name == COLLECTION_NAME for col in collections.collections
        )

        # Get information about all collections
        collections_info = []
        total_documents = 0

        for col in collections.collections:
            try:
                collection_info = await qdrant_client.get_collection(col.name)
                point_count = collection_info.points_count
                total_documents += point_count
                collections_info.append(
                    {
                        "name": col.name,
                        "document_count": point_count,
                        "is_project_collection": col.name.startswith(
                            "hbrag_project_"
                        ),
                    }
                )
            except Exception as count_error:
                logger.warning(
                    f"Could not get point count for {col.name}: {count_error}"
                )
                collections_info.append(
                    {
                        "name": col.name,
                        "document_count": "unknown",
                        "is_project_collection": col.name.startswith(
                            "hbrag_project_"
                        ),
                    }
                )

        return {
            "status": "healthy",
            "default_collection": COLLECTION_NAME,
            "collection_exists": collection_exists,
            "total_documents": total_documents,
            "collections": collections_info,
            "vector_size": VECTOR_SIZE,
            "distance_metric": "cosine",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise e


async def index_document(
    doc_id: str,
    text: str,
    source="unknown",
    avg_chunk_len=None,
    project_slug=None,
    metadata=None,
):
    """Index a document chunk"""
    try:
        new_metadata = {
            "source": source,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "text": text,  # Store original text in metadata for retrieval
        }

        # Add additional metadata if provided
        if metadata:
            new_metadata.update(metadata)

        # Add project slug to metadata
        if project_slug:
            new_metadata["project_slug"] = project_slug

        dense_vector, sparse_vector, late_interaction_vector = generate_vectors(text)

        # Create point for Qdrant
        point = PointStruct(
            id=str(uuid.uuid4()),  # Generate unique ID for Qdrant
            vector={
                DENSE_VECTOR_NAME: dense_vector,
                SPARSE_VECTOR_NAME: sparse_vector.as_object(),
                RERANKER_VECTOR_NAME: late_interaction_vector,
                # SPARSE_VECTOR_NAME: Document(
                #     text=text,
                #     model="Qdrant/bm25",
                #     options={
                #         "avg_len": len(text.split())
                #         if avg_chunk_len is None
                #         else avg_chunk_len
                #     },  # To pass BM25 parameters, here we're using default k & b for the BM25 formula
                # ),
            },
            payload={"doc_id": doc_id, **new_metadata},
        )

        # Determine collection name based on project and source
        collection_name = get_collection_name(project_slug, source)

        # Ensure collection exists
        if not await ensure_collection_exists(collection_name):
            raise Exception(f"Failed to create collection: {collection_name}")

        # Insert into Qdrant
        await qdrant_client.upsert(collection_name=collection_name, points=[point])

        logger.info(
            f"Indexed document: {doc_id} from {source} in collection: {collection_name}"
        )

        return {
            "status": "indexed",
            "id": doc_id,
            "source": source,
            "collection": collection_name,
            "project_slug": project_slug,
            "text_length": len(text),
            "vector_size": len(dense_vector),
        }

    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        raise


async def delete_document(ids=[]):
    """Delete documents by ID"""
    try:
        if not ids:
            raise ValueError("No IDs provided")

        # Search for points with matching doc_ids
        points_to_delete = []
        for doc_id in ids:
            search_results = await qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
                limit=1000,  # Get all matching points
            )

            for point in search_results[0]:
                points_to_delete.append(point.id)

        if points_to_delete:
            await qdrant_client.delete(
                collection_name=COLLECTION_NAME, points_selector=points_to_delete
            )

        return {"status": "deleted", "ids": ids, "count": len(points_to_delete)}

    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        raise Exception(f"Delete failed: {str(e)}")


async def reset_collection():
    """Reset the entire collection"""
    try:
        # Delete collection
        await qdrant_client.delete_collection(COLLECTION_NAME)

        # Recreate collection
        await create_collection(COLLECTION_NAME)

        return {"status": "reset", "message": "Collection reset successfully"}

    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        raise Exception(f"Reset failed: {str(e)}")
    

# ====================================================== Retrieval Logic ======================================================

def apply_document_type_weighting(results):
    """Boost scores based on document type"""

    DOC_TYPE_WEIGHTS = {
        ".pdf": 1.0,
        ".docx": 0.95,
        ".md": 0.6,
        ".txt": 0.7,
        ".html": 0.5,
    }

    for result in results:
        file_name = result["metadata"].get("file_name", "")
        if not file_name:
            file_name = result["metadata"].get("source", "")

        file_ext = os.path.splitext(file_name)[1].lower()

        weight = DOC_TYPE_WEIGHTS.get(file_ext, 0.8)

        result["original_score"] = result.get("original_score", result["score"])

        result["score"] = result["score"] * weight
        result["doc_type_weight"] = weight

        logger.debug(
            f"Applied weight {weight} to {file_name} (score: {result['original_score']} -> {result['score']})"
        )

    return results


async def search_collection(
    query_text: str, collection_name: str, n_results=5, metadata_filter=None
):
    if not await qdrant_client.collection_exists(collection_name):
        return []

    logger.info(f"Searching collection: {collection_name} for query: {query_text}")
    # Generate query embedding
    try:
        dense_vector, sparse_vector, late_interaction_vector = generate_vectors(query_text)
    except Exception as e:
        raise f"Failed to generate query embedding: {str(e)}"

    # Extract metadata filter if provided
    query_filter = None
    if metadata_filter:
        # Convert metadata filter to Qdrant filter
        conditions = []
        for key, value in metadata_filter.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        if conditions:
            query_filter = Filter(must=conditions)
            logger.info(f"Query with metadata filter: {metadata_filter}")

    # Use semantic search (simplified approach)
    try:
        search_results = await qdrant_client.query_points(
            collection_name=collection_name,
            prefetch=[
                Prefetch(
                    query=dense_vector,
                    using=DENSE_VECTOR_NAME,
                    limit=n_results * 2,
                ),
                Prefetch(
                    query=SparseVector(**sparse_vector.as_object()),
                    using=SPARSE_VECTOR_NAME,
                    limit=n_results * 2,
                ),
            ],
            query=late_interaction_vector,
            using=RERANKER_VECTOR_NAME,
            limit=n_results,
            query_filter=query_filter,
        )
        search_results = search_results.points

        logger.info(f"Hybrid search successful for {collection_name}")

    except Exception as hybrid_error:
        logger.warning(f"Hybrid search failed for {collection_name}: {hybrid_error}")
        logger.info(f"Falling back to semantic-only for {collection_name}")

        search_results = await qdrant_client.query_points(
            collection_name=collection_name,
            query=dense_vector,
            using=DENSE_VECTOR_NAME,
            limit=n_results,
            query_filter=query_filter,
        )
        search_results = search_results.points

        logger.info(f"Semantic search successful for {collection_name}")
    except Exception as search_error:
        logger.error(f"Search failed for {collection_name}: {search_error}")
        search_results = []

    return search_results


async def query_index(
    query_text: str, n_results=10, project_slugs=[], metadata_filter=None
):
    """Query the collection(s)"""
    try:
        # Determine which collections to search
        collections_to_search = []
        if project_slugs and any(slug.strip() for slug in project_slugs):
            # Search specific project collections
            for slug in project_slugs:
                slug = slug.strip()
                if slug:
                    collection_name = get_collection_name(slug)
                    collections_to_search.append(collection_name)
        else:
            # Search all collections
            all_collections = await qdrant_client.get_collections()
            collections_to_search = [col.name for col in all_collections.collections]

        # Search across all specified collections
        all_results = []
        for collection_name in collections_to_search:
            try:
                search_results = await search_collection(
                    query_text,
                    collection_name,
                    n_results,
                    metadata_filter,
                )

                # Add collection info to results
                for result in search_results:
                    all_results.append(
                        {
                            "content": result.payload.get("text", ""),
                            "metadata": {
                                k: v for k, v in result.payload.items() if k != "text"
                            },
                            "distance": 1.0
                            - result.score,  # Convert similarity to distance
                            "id": result.payload.get("doc_id", str(result.id)),
                            "collection": collection_name,
                            "score": result.score,
                        }
                    )

            except Exception as e:
                logger.warning(f"Failed to search collection {collection_name}: {e}")
                continue

        logger.info(f"Applying document type weighting to {len(all_results)} results")
        all_results = apply_document_type_weighting(all_results)

        all_results.sort(key=lambda x: x["score"], reverse=True)
        formatted_results = all_results[:n_results]

        logger.info("Top 3 results after weighting:")
        for i, result in enumerate(formatted_results[:3]):
            file_name = result["metadata"].get("file_name", "unknown")
            weight = result.get("doc_type_weight", "N/A")
            original_score = result.get("original_score", result["score"])
            logger.info(
                f"  {i + 1}. {file_name} - weight: {weight}, original: {original_score:.3f}, final: {result['score']:.3f}"
            )

        return {
            "query": query_text,
            "results": formatted_results,
            "count": len(formatted_results),
            "searched_collections": collections_to_search,
        }

    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise str(e)


async def query_global_index(query_text: str, n_results=10, metadata_filter=None):
    """Query specifically the global knowledge base collection (hbrag_docs)"""
    try:
        # Search specifically in the global collection
        global_collection = "hbrag_docs"

        search_results = await search_collection(
            query_text,
            global_collection,
            n_results,
            metadata_filter,
        )
        # Format results and filter out low-quality results
        formatted_results = []
        for result in search_results:
            content = result.payload.get("text", "")

            # Skip results with very low scores or empty content
            if result.score < 0.1 or not content.strip():
                continue

            # Skip results that appear to be binary/corrupted data
            if len(content) > 100 and content.count("\x00") > len(content) * 0.1:
                continue

            formatted_results.append(
                {
                    "content": content,
                    "metadata": {
                        k: v for k, v in result.payload.items() if k != "text"
                    },
                    "distance": 1.0 - result.score,  # Convert similarity to distance
                    "id": result.payload.get("doc_id", str(result.id)),
                    "collection": global_collection,
                    "score": result.score,
                }
            )
        logger.info(
            f"Applying document type weighting to {len(formatted_results)} global results"
        )
        formatted_results = apply_document_type_weighting(formatted_results)

        formatted_results.sort(key=lambda x: x["score"], reverse=True)

        # Add ranking information
        for i, result in enumerate(formatted_results):
            result["rank"] = i + 1

        logger.info("Top 3 global results after weighting:")
        for i, result in enumerate(formatted_results[:3]):
            file_name = result["metadata"].get("file_name", "unknown")
            weight = result.get("doc_type_weight", "N/A")
            original_score = result.get("original_score", result["score"])
            logger.info(
                f"  {i + 1}. {file_name} - weight: {weight}, original: {original_score:.3f}, final: {result['score']:.3f}"
            )

        return {
            "query": query_text,
            "results": formatted_results,
            "count": len(formatted_results),
            "searched_collection": global_collection,
        }

    except Exception as e:
        logger.error(f"Global query error: {str(e)}")
        raise str(e)
