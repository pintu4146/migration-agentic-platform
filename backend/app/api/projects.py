"""
Projects API

Manages project discovery and metadata by querying Qdrant collections.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..storage.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# Dependency: Get Qdrant store
async def get_qdrant_store() -> QdrantStore:
    """Get Qdrant store instance."""
    store = QdrantStore()
    await store.initialize()
    return store


class ProjectInfo(BaseModel):
    """Project information"""
    id: str
    name: str
    collection: str
    document_count: int


class ProjectListResponse(BaseModel):
    """Response for project list"""
    projects: List[ProjectInfo]
    total: int


@router.get("/list", response_model=ProjectListResponse)
async def list_projects(
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
) -> ProjectListResponse:
    """
    List all projects by discovering Qdrant collections.
    
    Projects are identified by collections with names starting with "project_".
    
    Returns:
        List of projects with metadata
    """
    
    try:
        logger.info("Listing all projects from Qdrant collections")
        
        # Get all collections from Qdrant
        collections_response = qdrant_store.client.get_collections()
        collections = collections_response.collections
        
        projects = []
        
        for collection in collections:
            # Only include collections that are projects
            if collection.name.startswith("project_"):
                # Extract project ID from collection name
                project_id = collection.name.replace("project_", "")
                
                # Get document count using count() method to avoid Pydantic validation issues
                try:
                    # Use count() method which returns the number of points in the collection
                    count_result = qdrant_store.client.count(
                        collection_name=collection.name,
                        exact=True
                    )
                    vector_count = count_result.count if count_result else 0
                except Exception as e:
                    logger.warning(f"Could not count documents in collection {collection.name}: {e}")
                    vector_count = 0
                
                projects.append(ProjectInfo(
                    id=project_id,
                    name=project_id,  # For now, use ID as name
                    collection=collection.name,
                    document_count=vector_count
                ))
        
        # Sort by project ID
        projects.sort(key=lambda p: p.id)
        
        logger.info(f"Found {len(projects)} projects")
        
        return ProjectListResponse(
            projects=projects,
            total=len(projects)
        )
    
    except Exception as e:
        logger.error(f"Failed to list projects: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(
    project_id: str,
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
) -> ProjectInfo:
    """
    Get information about a specific project.
    
    Args:
        project_id: Project identifier
        
    Returns:
        Project information
    """
    
    try:
        collection_name = f"project_{project_id}"
        
        # Check if collection exists
        collections_response = qdrant_store.client.get_collections()
        collection_names = [c.name for c in collections_response.collections]
        
        if collection_name not in collection_names:
            raise HTTPException(
                status_code=404,
                detail=f"Project '{project_id}' not found"
            )
        
        # Get collection info
        collection_info = qdrant_store.client.get_collection(collection_name)
        vector_count = collection_info.vectors_count or 0
        
        return ProjectInfo(
            id=project_id,
            name=project_id,
            collection=collection_name,
            document_count=vector_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
) -> Dict[str, Any]:
    """
    Delete a project and its associated Qdrant collection.
    
    Args:
        project_id: Project identifier
        
    Returns:
        Deletion confirmation
    """
    
    try:
        collection_name = f"project_{project_id}"
        
        # Check if collection exists
        collections_response = qdrant_store.client.get_collections()
        collection_names = [c.name for c in collections_response.collections]
        
        if collection_name not in collection_names:
            raise HTTPException(
                status_code=404,
                detail=f"Project '{project_id}' not found"
            )
        
        # Delete collection
        qdrant_store.client.delete_collection(collection_name)
        
        logger.info(f"Deleted project: {project_id}")
        
        return {
            "success": True,
            "message": f"Project '{project_id}' deleted successfully",
            "project_id": project_id,
            "collection": collection_name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete project: {str(e)}"
        )


# Made with Bob