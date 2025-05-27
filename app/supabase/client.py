import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class SupabaseClient:
    """Singleton class to manage Supabase connections"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the Supabase client connection"""
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            
            if not url or not key:
                logger.error("Supabase URL or key is missing. Check your environment variables.")
                self.client = None
                return
            
            # Remove /rest/v1 if it exists and ensure proper URL format
            url = url.replace('/rest/v1', '')
            url = url.rstrip('/')
            
            logger.info(f"Initializing Supabase client with URL: {url}")
            self.client = create_client(url, key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            self.client = None

    async def get_business_by_id(self, business_id):
        """Get business information by ID"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            result = self.client.table("businesses").select("*").eq("id", business_id).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error fetching business by ID: {str(e)}")
            return None

    async def get_business_by_phone(self, phone_number):
        """Get business information by business WhatsApp phone number"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            # Normalize phone number to ensure consistent searching
            normalized_phone = phone_number.replace("whatsapp:", "")
            
            # First, check businesses table for the phone number
            result = self.client.table("businesses").select("*").eq("phone", normalized_phone).execute()
            logger.debug(f"Supabase businesses query result: {result}")
            if "data" in result and result["data"]:
                return result["data"][0]
            
            # If not found, check mobile_money_details where businesses might have registered their phone
            result = self.client.table("mobile_money_details").select("*, businesses(*)").eq("account_number", normalized_phone).execute()
            if "data" in result and result["data"]:
                # Return the associated business data
                return result["data"][0]["businesses"]
                
            return None
        except Exception as e:
            logger.error(f"Error fetching business by phone: {str(e)}")
            return None

    async def get_chatbot_config(self, business_id):
        """Get the chatbot configuration for a specific business"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            result = self.client.table("chatbot_configurations").select("*").eq("business_id", business_id).order("version", desc=True).limit(1).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error fetching chatbot configuration: {str(e)}")
            return None
    
    async def get_products(self, business_id=None, limit=100, offset=0, category=None):
        """Get products from the database with optional filtering by business and category"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return []
                
            query = self.client.table("products").select("*")
            
            # Filter by business if provided
            if business_id:
                query = query.eq("business_id", business_id)
                
            # Filter by category if provided
            if category:
                query = query.eq("category", category)
                
            result = query.range(offset, offset + limit - 1).execute()
            
            if "data" in result:
                return result["data"]
            return []
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []
    
    async def get_product_by_id(self, product_id):
        """Get a specific product by ID"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            result = self.client.table("products").select("*").eq("id", product_id).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error fetching product by ID: {str(e)}")
            return None
    
    async def identify_customer(self, phone_number):
        """Identify a customer by phone number and return customer and business info"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None, None
                
            # Normalize phone number
            normalized_phone = phone_number.replace("whatsapp:", "")
            
            # Search for customer by phone
            result = self.client.table("customers").select("*, businesses(*)").eq("phone", normalized_phone).execute()
            
            if "data" in result and result["data"]:
                customer = result["data"][0]
                business = customer["businesses"] if "businesses" in customer else None
                return customer, business
                
            return None, None
        except Exception as e:
            logger.error(f"Error identifying customer: {str(e)}")
            return None, None
    
    async def create_order(self, order_data):
        """Create a new order in the database"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            result = self.client.table("orders").insert(order_data).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return None
    
    async def create_order_item(self, order_item_data):
        """Create a new order item in the database"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            result = self.client.table("order_items").insert(order_item_data).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error creating order item: {str(e)}")
            return None
    
    async def update_order(self, order_id, update_data):
        """Update an existing order"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return False
                
            result = self.client.table("orders").update(update_data).eq("id", order_id).execute()
            
            if "data" in result:
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating order: {str(e)}")
            return False
    
    async def get_user_by_phone(self, phone_number):
        """Get user information by phone number"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            # Normalize phone number to ensure consistent searching
            normalized_phone = phone_number.replace("whatsapp:", "")
            
            # First check customers table
            result = self.client.table("customers").select("*").eq("phone", normalized_phone).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
                
            # If not found in customers, check users table
            result = self.client.table("users").select("*").eq("phone", normalized_phone).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
                
            return None
        except Exception as e:
            logger.error(f"Error fetching user by phone: {str(e)}")
            return None
            
    async def create_customer(self, customer_data):
        """Create a new customer in the database"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            result = self.client.table("customers").insert(customer_data).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            return None
            
    async def record_sale(self, sale_data):
        """Record a new sale in the database"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            result = self.client.table("sales").insert(sale_data).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error recording sale: {str(e)}")
            return None
            
    async def get_payment_details(self, business_id, payment_method="mobile_money"):
        """Get payment details for a business"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
                
            if payment_method == "mobile_money":
                result = self.client.table("mobile_money_details").select("*").eq("business_id", business_id).execute()
            else:  # bank account
                result = self.client.table("bank_account_details").select("*").eq("business_id", business_id).execute()
            
            if "data" in result and result["data"]:
                return result["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error getting payment details: {str(e)}")
            return None 