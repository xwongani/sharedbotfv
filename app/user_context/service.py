import logging
from typing import Dict, List, Optional, Any
import json
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# Conversation states
class ConversationState:
    GREETING = "greeting"
    BROWSING = "browsing"
    PRODUCT_DETAILS = "product_details"
    CATEGORY_BROWSING = "category_browsing"
    CART_REVIEW = "cart_review"
    CHECKOUT = "checkout"
    PAYMENT = "payment"
    ORDER_CONFIRMATION = "order_confirmation"
    SUPPORT = "support"
    BUSINESS_SELECTION = "business_selection"  # For selecting which business to interact with

class UserContextService:
    def __init__(self):
        # In-memory user session cache
        # In production, this should use Redis or similar distributed cache
        # Structure: {phone_number: {business_id: {session_data}}}
        self.user_sessions = {}
        self.conversation_history = {}
        
        # Maximum number of messages to keep in conversation history per user
        self.max_history_length = 20
        
        # Session timeout (inactive time before session is considered expired)
        self.session_timeout_minutes = 30
    
    def _get_or_create_session(self, phone_number: str, business_id: Optional[str] = None) -> Dict:
        """
        Get or create user session data
        
        Args:
            phone_number: User's phone number
            business_id: ID of the business the user is interacting with
            
        Returns:
            Session data dictionary
        """
        # Clean expired sessions occasionally
        self._clean_expired_sessions()
        
        # Create user entry if not exists
        if phone_number not in self.user_sessions:
            self.user_sessions[phone_number] = {}
            self.conversation_history[phone_number] = {}
        
        # If no specific business ID is provided and no active business
        if not business_id and not self.user_sessions[phone_number]:
            # Create a temporary session for business selection
            temp_session = {
                "state": ConversationState.BUSINESS_SELECTION,
                "last_activity": datetime.now(),
                "data": {
                    "selected_business": None,
                    "user_info": {}
                }
            }
            self.user_sessions[phone_number]["_temp"] = temp_session
            self.conversation_history[phone_number]["_temp"] = []
            return temp_session
            
        # If no specific business ID, but user has an active business
        if not business_id and self.get_active_business_id(phone_number):
            business_id = self.get_active_business_id(phone_number)
            
        # If business_id is provided, create/update that specific business session
        if business_id:
            business_id_str = str(business_id)
            
            # Create business session if not exists
            if business_id_str not in self.user_sessions[phone_number]:
                self.user_sessions[phone_number][business_id_str] = {
                    "state": ConversationState.GREETING,
                    "last_activity": datetime.now(),
                    "data": {
                        "cart": [],
                        "viewed_products": [],
                        "selected_product": None,
                        "selected_category": None,
                        "business_id": business_id,
                        "user_info": {},
                        "payment_info": {},
                        "preferences": {}
                    }
                }
                # Initialize empty conversation history for this business
                if business_id_str not in self.conversation_history[phone_number]:
                    self.conversation_history[phone_number][business_id_str] = []
            
            # Update last activity time
            self.user_sessions[phone_number][business_id_str]["last_activity"] = datetime.now()
            
            # Remove temporary session if it exists
            if "_temp" in self.user_sessions[phone_number]:
                del self.user_sessions[phone_number]["_temp"]
                if "_temp" in self.conversation_history[phone_number]:
                    del self.conversation_history[phone_number]["_temp"]
            
            return self.user_sessions[phone_number][business_id_str]
        
        # Return first business session if multiple exist
        if self.user_sessions[phone_number]:
            business_keys = [k for k in self.user_sessions[phone_number].keys() if k != "_temp"]
            if business_keys:
                business_id_str = business_keys[0]
                self.user_sessions[phone_number][business_id_str]["last_activity"] = datetime.now()
                return self.user_sessions[phone_number][business_id_str]
        
        # If we get here, create a temporary session
        temp_session = {
            "state": ConversationState.BUSINESS_SELECTION,
            "last_activity": datetime.now(),
            "data": {
                "selected_business": None,
                "user_info": {}
            }
        }
        self.user_sessions[phone_number]["_temp"] = temp_session
        self.conversation_history[phone_number]["_temp"] = []
        return temp_session
    
    def _clean_expired_sessions(self):
        """Remove expired user sessions"""
        current_time = datetime.now()
        
        for phone_number in list(self.user_sessions.keys()):
            for business_id in list(self.user_sessions[phone_number].keys()):
                session = self.user_sessions[phone_number][business_id]
                last_activity = session.get("last_activity", datetime.min)
                time_diff = current_time - last_activity
                
                if time_diff > timedelta(minutes=self.session_timeout_minutes):
                    # Remove this business session
                    self.user_sessions[phone_number].pop(business_id, None)
                    if phone_number in self.conversation_history:
                        self.conversation_history[phone_number].pop(business_id, None)
                    
                    logger.info(f"Removed expired session for {phone_number}, business {business_id}")
            
            # If no business sessions left for this user, remove the user entry
            if not self.user_sessions[phone_number]:
                self.user_sessions.pop(phone_number, None)
                self.conversation_history.pop(phone_number, None)
                logger.info(f"Removed all sessions for {phone_number}")
    
    def get_active_business_id(self, phone_number: str) -> Optional[str]:
        """
        Get the currently active business ID for a user
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Active business ID or None if no active business
        """
        if phone_number not in self.user_sessions:
            return None
            
        # Exclude temporary session
        business_keys = [k for k in self.user_sessions[phone_number].keys() if k != "_temp"]
        
        if not business_keys:
            return None
            
        # Return most recently active business
        most_recent = None
        latest_time = datetime.min
        
        for business_id in business_keys:
            session = self.user_sessions[phone_number][business_id]
            last_activity = session.get("last_activity", datetime.min)
            
            if last_activity > latest_time:
                latest_time = last_activity
                most_recent = business_id
        
        return most_recent
    
    async def set_active_business(self, phone_number: str, business_id: str) -> Dict:
        """
        Set the active business for a user
        
        Args:
            phone_number: User's phone number
            business_id: Business ID to set as active
            
        Returns:
            Updated session dictionary
        """
        session = self._get_or_create_session(phone_number, business_id)
        return session
    
    async def get_session(self, phone_number: str, business_id: Optional[str] = None) -> Dict:
        """
        Get the current session for a user
        
        Args:
            phone_number: User's phone number
            business_id: Optional business ID to get session for
            
        Returns:
            Session dictionary
        """
        return self._get_or_create_session(phone_number, business_id)
    
    async def update_session_state(self, phone_number: str, new_state: str, business_id: Optional[str] = None) -> Dict:
        """
        Update the conversation state for a user
        
        Args:
            phone_number: User's phone number
            new_state: New conversation state
            business_id: Optional business ID to update session for
            
        Returns:
            Updated session dictionary
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
        
        session = self._get_or_create_session(phone_number, business_id)
        session["state"] = new_state
        return session
    
    async def update_session_data(self, phone_number: str, data_key: str, value: Any, business_id: Optional[str] = None) -> Dict:
        """
        Update a specific data field in the session
        
        Args:
            phone_number: User's phone number
            data_key: Key to update
            value: New value
            business_id: Optional business ID to update session for
            
        Returns:
            Updated session dictionary
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
        
        session = self._get_or_create_session(phone_number, business_id)
        session["data"][data_key] = value
        return session
    
    async def get_conversation_history(self, phone_number: str, business_id: Optional[str] = None) -> List[Dict]:
        """
        Get conversation history for a user
        
        Args:
            phone_number: User's phone number
            business_id: Optional business ID to get history for
            
        Returns:
            List of conversation history entries
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
            
        # Create session to ensure the conversation history exists
        session = self._get_or_create_session(phone_number, business_id)
        
        # Get the correct business_id_str based on if we have a temporary session or business session
        business_id_str = "_temp" if business_id is None else str(business_id)
        
        if phone_number in self.conversation_history and business_id_str in self.conversation_history[phone_number]:
            return self.conversation_history[phone_number][business_id_str]
        return []
    
    async def add_message_to_history(self, phone_number: str, role: str, content: str, business_id: Optional[str] = None):
        """
        Add a message to the conversation history
        
        Args:
            phone_number: User's phone number
            role: Message role (user or assistant)
            content: Message content
            business_id: Optional business ID to add message for
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
            
        # Create session to ensure the conversation history exists
        session = self._get_or_create_session(phone_number, business_id)
        
        # Get the correct business_id_str based on if we have a temporary session or business session
        business_id_str = "_temp" if business_id is None else str(business_id)
        
        # Ensure the conversation history structure exists
        if phone_number not in self.conversation_history:
            self.conversation_history[phone_number] = {}
            
        if business_id_str not in self.conversation_history[phone_number]:
            self.conversation_history[phone_number][business_id_str] = []
            
        # Add message to history
        self.conversation_history[phone_number][business_id_str].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Limit history size
        if len(self.conversation_history[phone_number][business_id_str]) > self.max_history_length:
            self.conversation_history[phone_number][business_id_str] = self.conversation_history[phone_number][business_id_str][-self.max_history_length:]
    
    async def add_to_cart(self, phone_number: str, product: Dict, quantity: int = 1, business_id: Optional[str] = None) -> Dict:
        """
        Add a product to the user's cart
        
        Args:
            phone_number: User's phone number
            product: Product dictionary
            quantity: Quantity to add
            business_id: Optional business ID to add to cart for
            
        Returns:
            Updated cart
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
            
        if not business_id and product.get("business_id"):
            business_id = product.get("business_id")
            
        session = self._get_or_create_session(phone_number, business_id)
        
        # Get current cart
        cart = session["data"].get("cart", [])
        
        # Check if product already in cart
        product_id = product.get("id")
        existing_item = next((item for item in cart if item["product"].get("id") == product_id), None)
        
        if existing_item:
            # Update quantity
            existing_item["quantity"] += quantity
        else:
            # Add new item
            cart.append({
                "product": product,
                "quantity": quantity
            })
        
        # Update session
        session["data"]["cart"] = cart
        
        return session["data"]["cart"]
    
    async def remove_from_cart(self, phone_number: str, product_id: str, business_id: Optional[str] = None) -> Dict:
        """
        Remove a product from the user's cart
        
        Args:
            phone_number: User's phone number
            product_id: ID of product to remove
            business_id: Optional business ID to remove from cart for
            
        Returns:
            Updated cart
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
            
        session = self._get_or_create_session(phone_number, business_id)
        
        # Get current cart
        cart = session["data"].get("cart", [])
        
        # Filter out the product
        updated_cart = [item for item in cart if item["product"].get("id") != product_id]
        
        # Update session
        session["data"]["cart"] = updated_cart
        
        return session["data"]["cart"]
    
    async def clear_cart(self, phone_number: str, business_id: Optional[str] = None) -> Dict:
        """
        Clear the user's cart
        
        Args:
            phone_number: User's phone number
            business_id: Optional business ID to clear cart for
            
        Returns:
            Updated session data
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
            
        session = self._get_or_create_session(phone_number, business_id)
        session["data"]["cart"] = []
        return session["data"]
    
    async def get_cart(self, phone_number: str, business_id: Optional[str] = None) -> List[Dict]:
        """
        Get the user's current cart
        
        Args:
            phone_number: User's phone number
            business_id: Optional business ID to get cart for
            
        Returns:
            List of cart items
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
            
        session = self._get_or_create_session(phone_number, business_id)
        return session["data"].get("cart", [])
    
    async def calculate_cart_total(self, phone_number: str, business_id: Optional[str] = None) -> Dict:
        """
        Calculate the total price of items in the cart
        
        Args:
            phone_number: User's phone number
            business_id: Optional business ID to calculate total for
            
        Returns:
            Dictionary with total price and item count
        """
        cart = await self.get_cart(phone_number, business_id)
        
        total = 0
        item_count = 0
        
        for item in cart:
            quantity = item.get("quantity", 0)
            price = item.get("product", {}).get("price", 0)
            item_count += quantity
            total += price * quantity
        
        return {
            "total": total,
            "item_count": item_count,
            "currency": "ZMW"  # Assuming Zambian Kwacha as default currency
        }
    
    async def get_session_data(self, phone_number: str, business_id: Optional[str] = None) -> Dict:
        """
        Get all session data for a user
        
        Args:
            phone_number: User's phone number
            business_id: Optional business ID to get data for
            
        Returns:
            Session data dictionary
        """
        # If no business_id provided, use active business
        if not business_id:
            business_id = self.get_active_business_id(phone_number)
            
        session = self._get_or_create_session(phone_number, business_id)
        return session["data"]
        
    async def get_all_user_businesses(self, phone_number: str) -> List[str]:
        """
        Get all businesses a user has interacted with
        
        Args:
            phone_number: User's phone number
            
        Returns:
            List of business IDs
        """
        if phone_number not in self.user_sessions:
            return []
            
        # Exclude temporary session
        business_keys = [k for k in self.user_sessions[phone_number].keys() if k != "_temp"]
        
        # Return as strings (UUIDs)
        return business_keys 