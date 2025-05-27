import logging
from typing import Dict, List, Any, Optional
from app.supabase.client import SupabaseClient

# Configure logging
logger = logging.getLogger(__name__)

class BusinessService:
    """Service for managing business entities and routing"""
    
    def __init__(self):
        self.supabase = SupabaseClient()
        logger.info("Business service initialized")
    
    async def get_all_businesses(self) -> List[Dict[str, Any]]:
        """
        Get all active businesses
        
        Returns:
            List of business objects
        """
        try:
            # Query businesses table for active businesses
            result = await self.supabase.client.table("businesses")\
                .select("*")\
                .eq("is_active", True)\
                .execute()
                
            if "error" in result:
                logger.error(f"Error fetching businesses: {result['error']}")
                return []
                
            businesses = result.data
            logger.info(f"Retrieved {len(businesses)} active businesses")
            return businesses
            
        except Exception as e:
            logger.error(f"Error getting businesses: {str(e)}")
            return []
    
    async def get_business_by_id(self, business_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a business by its ID
        
        Args:
            business_id: Business ID
            
        Returns:
            Business object or None if not found
        """
        try:
            # Query businesses table for the specific business
            result = await self.supabase.client.table("businesses")\
                .select("*")\
                .eq("id", business_id)\
                .single()\
                .execute()
                
            if "error" in result:
                logger.error(f"Error fetching business {business_id}: {result['error']}")
                return None
                
            business = result.data
            return business
            
        except Exception as e:
            logger.error(f"Error getting business by ID: {str(e)}")
            return None
    
    async def find_customer_business_association(self, phone_number: str) -> List[Dict[str, Any]]:
        """
        Find businesses associated with a customer phone number
        
        Args:
            phone_number: Customer's phone number
            
        Returns:
            List of customer-business associations
        """
        try:
            # Query customers table for matching phone number
            result = await self.supabase.client.table("customers")\
                .select("*, businesses(*)")\
                .eq("phone_number", phone_number)\
                .execute()
                
            if "error" in result:
                logger.error(f"Error finding customer associations: {result['error']}")
                return []
                
            # Format the customer-business associations
            associations = []
            for customer in result.data:
                business = customer.get("businesses")
                if business:
                    associations.append({
                        "customer_id": customer.get("id"),
                        "business_id": customer.get("business_id"),
                        "business_name": business.get("name"),
                        "customer_name": customer.get("name"),
                        "last_interaction": customer.get("last_interaction")
                    })
            
            logger.info(f"Found {len(associations)} business associations for {phone_number}")
            return associations
            
        except Exception as e:
            logger.error(f"Error finding customer business associations: {str(e)}")
            return []
    
    async def create_customer(self, 
                             business_id: str, 
                             phone_number: str, 
                             name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new customer for a business
        
        Args:
            business_id: Business ID
            phone_number: Customer's phone number
            name: Optional customer name
            
        Returns:
            Created customer object or None if failed
        """
        try:
            # Check if customer already exists for this business
            existing = await self.supabase.client.table("customers")\
                .select("*")\
                .eq("business_id", business_id)\
                .eq("phone_number", phone_number)\
                .execute()
                
            if "error" not in existing and existing.data:
                logger.info(f"Customer already exists for {business_id} with number {phone_number}")
                return existing.data[0]
            
            # Create new customer
            customer_data = {
                "business_id": business_id,
                "phone_number": phone_number,
                "name": name or "New Customer",
                "is_active": True
            }
            
            result = await self.supabase.client.table("customers").insert(customer_data).execute()
            
            if "error" in result:
                logger.error(f"Error creating customer: {result['error']}")
                return None
                
            logger.info(f"Created new customer for business {business_id}")
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            return None
    
    async def get_business_prompt(self, business_id: str) -> Optional[str]:
        """
        Get the custom AI prompt for a business
        
        Args:
            business_id: Business ID
            
        Returns:
            Custom prompt string or None if not found
        """
        try:
            # Query business_settings table for the prompt
            result = await self.supabase.client.table("business_settings")\
                .select("value")\
                .eq("business_id", business_id)\
                .eq("key", "ai_prompt")\
                .single()\
                .execute()
                
            if "error" in result:
                logger.error(f"Error fetching business prompt: {result['error']}")
                return None
                
            prompt = result.data.get("value")
            return prompt
            
        except Exception as e:
            logger.error(f"Error getting business prompt: {str(e)}")
            return None
    
    async def format_business_selection_message(self, businesses: List[Dict[str, Any]]) -> str:
        """
        Format business list for customer selection
        
        Args:
            businesses: List of business objects
            
        Returns:
            Formatted message for WhatsApp
        """
        try:
            if not businesses:
                return "Sorry, there are no businesses available at the moment."
                
            message = "*Welcome to InxSource!*\n\n"
            message += "Please select a business by replying with the number:\n\n"
            
            for i, business in enumerate(businesses, 1):
                name = business.get("name", "Unknown Business")
                description = business.get("description", "")
                
                message += f"{i}. *{name}*"
                if description:
                    message += f" - {description}"
                message += "\n"
                
            return message
            
        except Exception as e:
            logger.error(f"Error formatting business selection message: {str(e)}")
            return "Error displaying businesses. Please try again later." 