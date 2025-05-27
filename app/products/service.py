import logging
from typing import Dict, List, Any, Optional
from app.supabase.client import SupabaseClient

# Configure logging
logger = logging.getLogger(__name__)

class ProductService:
    """Service for managing product catalog information for businesses"""
    
    def __init__(self):
        self.supabase = SupabaseClient()
        logger.info("Product service initialized")
    
    async def get_business_products(self, business_id: str) -> List[Dict[str, Any]]:
        """
        Get all products for a specific business
        
        Args:
            business_id: The ID of the business to fetch products for
            
        Returns:
            List of product objects
        """
        try:
            # Query products table filtered by business_id
            result = await self.supabase.client.table("products").select("*").eq("business_id", business_id).execute()
            
            if "error" in result:
                logger.error(f"Error fetching products: {result['error']}")
                return []
                
            products = result.data
            logger.info(f"Retrieved {len(products)} products for business {business_id}")
            return products
            
        except Exception as e:
            logger.error(f"Error getting business products: {str(e)}")
            return []
    
    async def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific product
        
        Args:
            product_id: The ID of the product to fetch
            
        Returns:
            Product details or None if not found
        """
        try:
            # Query products table for the specific product
            result = await self.supabase.client.table("products").select("*").eq("id", product_id).single().execute()
            
            if "error" in result:
                logger.error(f"Error fetching product details: {result['error']}")
                return None
                
            product = result.data
            return product
            
        except Exception as e:
            logger.error(f"Error getting product details: {str(e)}")
            return None
    
    async def get_product_by_name(self, business_id: str, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Search for a product by name within a business
        
        Args:
            business_id: The ID of the business to search in
            product_name: The name of the product to find (case-insensitive partial match)
            
        Returns:
            Product details or None if not found
        """
        try:
            # Query products table for products matching the name pattern
            result = await self.supabase.client.table("products").select("*")\
                .eq("business_id", business_id)\
                .ilike("name", f"%{product_name}%")\
                .execute()
            
            if "error" in result or not result.data:
                logger.error(f"No product found matching '{product_name}' for business {business_id}")
                return None
                
            # Return the first matching product
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error finding product by name: {str(e)}")
            return None
    
    async def get_business_categories(self, business_id: str) -> List[str]:
        """
        Get all unique product categories for a business
        
        Args:
            business_id: The ID of the business
            
        Returns:
            List of unique category names
        """
        try:
            # Query products table for distinct categories
            result = await self.supabase.client.table("products")\
                .select("category")\
                .eq("business_id", business_id)\
                .execute()
            
            if "error" in result:
                logger.error(f"Error fetching categories: {result['error']}")
                return []
                
            # Extract unique categories
            categories = set()
            for product in result.data:
                if product.get("category"):
                    categories.add(product["category"])
                    
            return list(categories)
            
        except Exception as e:
            logger.error(f"Error getting business categories: {str(e)}")
            return []
    
    async def get_products_by_category(self, business_id: str, category: str) -> List[Dict[str, Any]]:
        """
        Get all products in a specific category for a business
        
        Args:
            business_id: The ID of the business
            category: The category name to filter by
            
        Returns:
            List of product objects in the category
        """
        try:
            # Query products table filtered by business_id and category
            result = await self.supabase.client.table("products")\
                .select("*")\
                .eq("business_id", business_id)\
                .eq("category", category)\
                .execute()
            
            if "error" in result:
                logger.error(f"Error fetching products by category: {result['error']}")
                return []
                
            products = result.data
            logger.info(f"Retrieved {len(products)} products in category '{category}' for business {business_id}")
            return products
            
        except Exception as e:
            logger.error(f"Error getting products by category: {str(e)}")
            return []
    
    async def format_product_message(self, product: Dict[str, Any]) -> str:
        """
        Format a product object into a human-readable message
        
        Args:
            product: Product object with details
            
        Returns:
            Formatted product message
        """
        try:
            # Basic product information
            name = product.get("name", "Unknown Product")
            price = product.get("price", 0)
            description = product.get("description", "No description available")
            sku = product.get("sku", "N/A")
            
            # Format price with currency symbol
            formatted_price = f"K{price:.2f}" if price else "Price not available"
            
            # Construct message
            message = f"*{name}*\n"
            message += f"Price: {formatted_price}\n"
            message += f"SKU: {sku}\n"
            message += f"Description: {description}\n"
            
            # Add stock information if available
            if "stock_quantity" in product:
                stock = product["stock_quantity"]
                stock_status = "In Stock" if stock > 0 else "Out of Stock"
                message += f"Stock: {stock_status}"
                
            return message
            
        except Exception as e:
            logger.error(f"Error formatting product message: {str(e)}")
            return "Error displaying product information"

    async def get_products(self, limit: int = 10, offset: int = 0, category: Optional[str] = None) -> List[Dict]:
        """
        Get products from the database
        
        Args:
            limit: Maximum number of products to return
            offset: Number of products to skip (for pagination)
            category: Optional category to filter by
            
        Returns:
            List of product dictionaries
        """
        try:
            products = await self.supabase.get_products(limit=limit, offset=offset, category=category)
            return products
        except Exception as e:
            logger.error(f"Error getting products: {str(e)}")
            return []
    
    async def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """
        Get a specific product by its ID
        
        Args:
            product_id: The ID of the product to retrieve
            
        Returns:
            Product dictionary or None if not found
        """
        try:
            product = await self.supabase.get_product_by_id(product_id)
            return product
        except Exception as e:
            logger.error(f"Error getting product by ID: {str(e)}")
            return None
    
    async def format_product_for_whatsapp(self, product: Dict) -> Dict:
        """
        Format a product for display in WhatsApp
        
        Args:
            product: The product dictionary
            
        Returns:
            Dictionary with formatted message and media URLs
        """
        try:
            # Extract product information
            name = product.get("name", "Unknown Product")
            price = product.get("price", 0)
            description = product.get("description", "No description available")
            stock = product.get("stock", 0)
            image_urls = product.get("image_urls", [])
            
            # Format price
            formatted_price = f"K{price}" if isinstance(price, (int, float)) else price
            
            # Build the message
            message = f"*{name}*\n"
            message += f"Price: {formatted_price}\n"
            message += f"In Stock: {'Yes' if stock > 0 else 'No'}\n\n"
            
            # Truncate description if too long for WhatsApp
            max_desc_length = 500
            if len(description) > max_desc_length:
                description = description[:max_desc_length] + "..."
                
            message += description
            
            return {
                "message": message,
                "media_url": image_urls[0] if image_urls else None
            }
        except Exception as e:
            logger.error(f"Error formatting product for WhatsApp: {str(e)}")
            return {
                "message": "Sorry, there was an error displaying this product.",
                "media_url": None
            }
    
    async def format_product_list_for_whatsapp(self, products: List[Dict], title: str = "Products") -> Dict:
        """
        Format a list of products for display in WhatsApp
        
        Args:
            products: List of product dictionaries
            title: Title for the product list
            
        Returns:
            Dictionary with formatted message and featured image URL
        """
        try:
            if not products:
                return {
                    "message": "No products found.",
                    "media_url": None
                }
            
            # Build the message
            message = f"*{title}*\n\n"
            
            # Featured image (first product's first image)
            featured_image = None
            if products and "image_urls" in products[0] and products[0]["image_urls"]:
                featured_image = products[0]["image_urls"][0]
            
            # List products
            for i, product in enumerate(products, 1):
                name = product.get("name", "Unknown Product")
                price = product.get("price", 0)
                
                # Format price
                formatted_price = f"K{price}" if isinstance(price, (int, float)) else price
                
                message += f"{i}. *{name}* - {formatted_price}\n"
            
            message += "\nTo view details about a product, reply with the number or the name of the product."
            
            return {
                "message": message,
                "media_url": featured_image
            }
        except Exception as e:
            logger.error(f"Error formatting product list for WhatsApp: {str(e)}")
            return {
                "message": "Sorry, there was an error displaying the product list.",
                "media_url": None
            }
    
    async def get_categories(self) -> List[str]:
        """
        Get all available product categories
        
        Returns:
            List of category names
        """
        try:
            # This would normally query a categories table, but for now we'll get unique categories from products
            products = await self.supabase.get_products(limit=100)
            categories = set()
            
            for product in products:
                category = product.get("category")
                if category:
                    categories.add(category)
            
            return sorted(list(categories))
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []
    
    async def search_products(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for products by name or description
        
        Args:
            query: Search query
            limit: Maximum number of products to return
            
        Returns:
            List of matching product dictionaries
        """
        try:
            # In a real implementation, this would use Supabase's full-text search
            # For now, we'll get all products and filter them manually
            all_products = await self.supabase.get_products(limit=100)
            query = query.lower()
            
            matching_products = []
            for product in all_products:
                name = product.get("name", "").lower()
                description = product.get("description", "").lower()
                
                if query in name or query in description:
                    matching_products.append(product)
                    
                if len(matching_products) >= limit:
                    break
            
            return matching_products
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            return [] 