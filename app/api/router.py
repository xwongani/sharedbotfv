from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import logging

from app.products.service import ProductService
from app.user_context.service import UserContextService
from app.supabase.client import SupabaseClient

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["API"])

# Dependency Injection
def get_product_service():
    return ProductService()

def get_user_context_service():
    return UserContextService()

def get_supabase_client():
    return SupabaseClient()

@router.get("/products")
async def get_products(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    product_service: ProductService = Depends(get_product_service)
):
    """
    Get a list of products with optional filtering by category
    
    Args:
        limit: Maximum number of products to return (1-100)
        offset: Number of products to skip (for pagination)
        category: Optional category to filter by
    """
    try:
        products = await product_service.get_products(limit=limit, offset=offset, category=category)
        return {"products": products, "count": len(products)}
    except Exception as e:
        logger.error(f"Error getting products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve products")

@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    product_service: ProductService = Depends(get_product_service)
):
    """
    Get a specific product by ID
    
    Args:
        product_id: The ID of the product to retrieve
    """
    try:
        product = await product_service.get_product_by_id(product_id)
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve product")

@router.get("/categories")
async def get_categories(
    product_service: ProductService = Depends(get_product_service)
):
    """Get all available product categories"""
    try:
        categories = await product_service.get_categories()
        return {"categories": categories}
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")

@router.get("/search")
async def search_products(
    query: str,
    limit: int = Query(10, ge=1, le=100),
    product_service: ProductService = Depends(get_product_service)
):
    """
    Search for products by name or description
    
    Args:
        query: Search term
        limit: Maximum number of products to return (1-100)
    """
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
            
        products = await product_service.search_products(query, limit=limit)
        return {"products": products, "count": len(products), "query": query}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search products")

@router.get("/users/{phone_number}")
async def get_user(
    phone_number: str,
    supabase_client: SupabaseClient = Depends(get_supabase_client)
):
    """
    Get user information by phone number
    
    Args:
        phone_number: User's phone number (with or without whatsapp: prefix)
    """
    try:
        # Normalize phone number
        normalized_phone = phone_number.replace("whatsapp:", "")
        
        user = await supabase_client.get_user_by_phone(normalized_phone)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user")

@router.get("/sessions/{phone_number}")
async def get_user_session(
    phone_number: str,
    user_context_service: UserContextService = Depends(get_user_context_service)
):
    """
    Get the current session information for a user
    
    Args:
        phone_number: User's phone number (with or without whatsapp: prefix)
    """
    try:
        # Normalize phone number
        normalized_phone = phone_number.replace("whatsapp:", "")
        
        session = await user_context_service.get_session(normalized_phone)
        return session
    except Exception as e:
        logger.error(f"Error getting user session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user session")

@router.get("/sessions/{phone_number}/history")
async def get_conversation_history(
    phone_number: str,
    limit: int = Query(20, ge=1, le=100),
    user_context_service: UserContextService = Depends(get_user_context_service)
):
    """
    Get conversation history for a user
    
    Args:
        phone_number: User's phone number (with or without whatsapp: prefix)
        limit: Maximum number of messages to return (1-100)
    """
    try:
        # Normalize phone number
        normalized_phone = phone_number.replace("whatsapp:", "")
        
        history = await user_context_service.get_conversation_history(normalized_phone)
        
        # Limit the number of messages returned
        limited_history = history[-limit:] if history else []
        
        return {"history": limited_history, "count": len(limited_history)}
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation history") 