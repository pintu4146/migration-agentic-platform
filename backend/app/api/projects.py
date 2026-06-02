"""
Projects API

Manages project discovery and metadata by querying Qdrant collections.
"""

import logging
import re
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..storage.qdrant_store import QdrantStore
from ..models.schemas import ProjectCreateRequest, ProjectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# Dependency: Get Qdrant store
async def get_qdrant_store() -> QdrantStore:
    """Get Qdrant store instance."""
    store = QdrantStore()
    await store.initialize()
    return store


def sanitize_project_name(name: str) -> str:
    """
    Sanitize project name to create valid project ID.
    
    Args:
        name: Raw project name
        
    Returns:
        Sanitized project ID (lowercase, alphanumeric + hyphens)
    """
    # Convert to lowercase
    project_id = name.lower()
    # Replace spaces and special chars with hyphens
    project_id = re.sub(r'[^a-z0-9-_]', '-', project_id)
    # Remove duplicate hyphens
    project_id = re.sub(r'-+', '-', project_id)
    # Remove leading/trailing hyphens
    project_id = project_id.strip('-')
    return project_id


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


@router.post("/create", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
) -> ProjectResponse:
    """
    Create a new project with Qdrant collection.
    
    Args:
        request: Project creation request with name and optional description
        
    Returns:
        Created project information
    """
    
    try:
        # Validate and sanitize project name
        if not request.name or len(request.name.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Project name must be at least 3 characters long"
            )
        
        # Sanitize project name to create project ID
        project_id = sanitize_project_name(request.name)
        
        if not project_id:
            raise HTTPException(
                status_code=400,
                detail="Project name contains only invalid characters"
            )
        
        collection_name = f"project_{project_id}"
        
        logger.info(f"Creating project: {project_id} (collection: {collection_name})")
        
        # Check if collection already exists
        collections_response = qdrant_store.client.get_collections()
        existing_collections = [c.name for c in collections_response.collections]
        
        if collection_name in existing_collections:
            raise HTTPException(
                status_code=409,
                detail=f"Project '{project_id}' already exists"
            )
        
        # Create Qdrant collection for the project
        await qdrant_store.create_collection(
            collection_name=collection_name,
            vector_size=768,  # Default for sentence transformers
        )
        
        logger.info(f"Successfully created project: {project_id}")
        
        return ProjectResponse(
            project_id=project_id,
            name=request.name,
            description=request.description,
            phase="init",
            state_version=0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}"
        )


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