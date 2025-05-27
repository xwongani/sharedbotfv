import logging
import re
from typing import Dict, List, Optional, Any

from app.twilio.service import TwilioService
from app.gemini.service import GeminiService
from app.user_context.service import UserContextService, ConversationState
from app.products.service import ProductService
from app.payments.service import PaymentService
from app.supabase.client import SupabaseClient

# Configure logging
logger = logging.getLogger(__name__)

class WhatsAppHandler:
    def __init__(self):
        self.twilio_service = TwilioService()
        self.gemini_service = GeminiService()
        self.user_context_service = UserContextService()
        self.product_service = ProductService()
        self.payment_service = PaymentService()
        self.supabase_client = SupabaseClient()
        
    async def process_message(self, message_data: Dict):
        """
        Process an incoming WhatsApp message from webhook
        
        This method is called asynchronously in the background and sends
        responses directly to the user via Twilio.
        
        Args:
            message_data: Dictionary containing extracted message data
        """
        try:
            from_number = message_data.get("from_number")
            to_number = message_data.get("to_number")
            body = message_data.get("body", "")
            
            if not from_number or not body:
                logger.error("Missing required message data")
                return
            
            # Identify the business this customer is messaging
            business_id = await self._identify_business(from_number, to_number)
            logger.info(f"[process_message] Identified business_id: {business_id} (type: {type(business_id)}) for user {from_number}")
            
            # Check what is stored in session
            active_business_id = self.user_context_service.get_active_business_id(from_number)
            logger.info(f"[process_message] Active business in session for {from_number}: {active_business_id} (type: {type(active_business_id)})")
            
            # Generate and send response
            response = await self._generate_response(from_number, body, business_id)
            
            # Send response via Twilio
            await self.twilio_service.send_message(
                to=from_number,
                body=response.get("message", "I'm sorry, I couldn't process your message."),
                media_url=response.get("media_url")
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Try to send error message
            try:
                await self.twilio_service.send_message(
                    to=message_data.get("from_number", ""),
                    body="I'm sorry, there was an error processing your message. Please try again later."
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {str(send_error)}")
    
    async def process_direct_message(self, from_number: str, to_number: str, body: str):
        """
        Process a direct message (not from webhook)
        
        Args:
            from_number: Sender phone number
            to_number: Recipient phone number
            body: Message text
        """
        try:
            if not from_number or not body:
                logger.error("Missing required message data for direct message")
                return
            
            # Identify the business this customer is messaging
            business_id = await self._identify_business(from_number, to_number)
                
            # Generate response
            response = await self._generate_response(from_number, body, business_id)
            
            # Send response via Twilio
            await self.twilio_service.send_message(
                to=from_number,
                body=response.get("message", "I'm sorry, I couldn't process your message."),
                media_url=response.get("media_url")
            )
            
        except Exception as e:
            logger.error(f"Error processing direct message: {str(e)}")
            # Try to send error message
            try:
                await self.twilio_service.send_message(
                    to=from_number,
                    body="I'm sorry, there was an error processing your message. Please try again later."
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {str(send_error)}")
    
    async def _identify_business(self, customer_phone: str, to_phone: str) -> Optional[str]:
        """
        Identify which business the customer is interacting with
        
        This attempts to identify the business through multiple methods:
        1. Check if the customer's session has an active business
        2. Check if the customer is already associated with a business
        3. Check if the phone number the customer messaged belongs to a business
        
        Returns business ID as a string for consistency.
        
        Args:
            customer_phone: Customer's phone number
            to_phone: Phone number the customer messaged
            
        Returns:
            Business ID or None
        """
        # First check if the customer already has an active business in their session
        active_business_id = self.user_context_service.get_active_business_id(customer_phone)
        logger.info(f"[_identify_business] Session active_business_id for {customer_phone}: {active_business_id} (type: {type(active_business_id)})")
        if active_business_id:
            return str(active_business_id)
        
        # Check if this customer is already associated with a business
        customer, business = await self.supabase_client.identify_customer(customer_phone)
        if customer and business:
            business_id = business.get("id")
            logger.info(f"[_identify_business] Found business by customer association: {business_id} (type: {type(business_id)})")
            if business_id:
                await self.user_context_service.set_active_business(customer_phone, str(business_id))
                return str(business_id)
        
        # Check if the phone number the customer messaged is associated with a business
        business = await self.supabase_client.get_business_by_phone(to_phone)
        logger.info(f"[_identify_business] Business found by phone {to_phone}: {business}")
        
        if business:
            # Try to get business_id from different possible fields
            business_id = business.get("id") or business.get("business_id")
            logger.info(f"[_identify_business] Extracted business_id: {business_id} (type: {type(business_id)})")
            
            if business_id:
                # Convert to string and ensure it's a valid UUID
                business_id_str = str(business_id)
                logger.info(f"[_identify_business] Setting active business to: {business_id_str}")
                
                # Set the active business in the session
                await self.user_context_service.set_active_business(customer_phone, business_id_str)
                # Update the session state to GREETING since this is a new conversation
                await self.user_context_service.update_session_state(customer_phone, ConversationState.GREETING, business_id_str)
                return business_id_str
            else:
                logger.error(f"[_identify_business] Business found but no valid ID: {business}")
        
        logger.warning(f"[_identify_business] Could not identify business for user {customer_phone}")
        return None
    
    async def _generate_response(self, from_number: str, message_text: str, business_id: Optional[str] = None) -> Dict:
        """
        Generate a response to a user message
        
        This method:
        1. Updates the user's conversation history
        2. Processes any commands or special message patterns
        3. Handles business selection if needed
        4. Generates an AI response using conversation context
        5. Updates the conversation state based on the interaction
        
        Args:
            from_number: Sender phone number
            message_text: Message text content
            business_id: Business ID the user is interacting with
            
        Returns:
            Dictionary with response message and optional media URL
        """
        try:
            # Get user session and conversation history
            session = await self.user_context_service.get_session(from_number, business_id)
            conversation_history = await self.user_context_service.get_conversation_history(from_number, business_id)
            current_state = session.get("state", ConversationState.GREETING)
            
            # Add user message to history
            await self.user_context_service.add_message_to_history(
                phone_number=from_number,
                role="user",
                content=message_text,
                business_id=business_id
            )
            
            # Handle business selection if we don't have a business_id yet
            if not business_id and current_state == ConversationState.BUSINESS_SELECTION:
                business_selection_response = await self._handle_business_selection(from_number, message_text)
                if business_selection_response:
                    return business_selection_response
            
            # Check for commands or special patterns
            command_response = await self._process_commands(from_number, message_text, current_state, business_id)
            if command_response:
                # Add bot response to history
                await self.user_context_service.add_message_to_history(
                    phone_number=from_number,
                    role="assistant",
                    content=command_response.get("message", ""),
                    business_id=business_id
                )
                return command_response
                
            # Prepare context for AI response
            context = await self._prepare_conversation_context(from_number, current_state, business_id)
            
            # Get the business-specific chatbot configuration
            if business_id:
                chatbot_config = await self.supabase_client.get_chatbot_config(business_id)
                if chatbot_config:
                    context["chatbot_config"] = chatbot_config
            
            # Generate AI response
            updated_history = await self.user_context_service.get_conversation_history(from_number, business_id)
            ai_response = await self.gemini_service.generate_response(
                user_input=message_text,
                conversation_history=updated_history,
                context=context
            )
            
            # Update conversation state based on message content
            await self._update_conversation_state(from_number, message_text, ai_response, business_id)
            
            # Add bot response to history
            await self.user_context_service.add_message_to_history(
                phone_number=from_number,
                role="assistant",
                content=ai_response,
                business_id=business_id
            )
            
            # Check if we should enhance the response with product info
            enhanced_response = await self._enhance_response_with_products(from_number, ai_response, message_text, business_id)
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {"message": "I'm sorry, I couldn't understand your message. Please try again later."}
    
    async def _handle_business_selection(self, phone_number: str, message_text: str) -> Optional[Dict]:
        """
        Handle business selection when a user needs to choose which business to interact with
        """
        try:
            # Fetch all businesses from Supabase
            businesses_result = self.supabase_client.client.table("businesses").select("*").execute()
            businesses = businesses_result.data
            if not businesses:
                return {"message": "Sorry, there are no businesses available at the moment."}

            # Store mapping of index to business ID in session for this user
            index_to_id = {str(i+1): b["id"] for i, b in enumerate(businesses)}
            await self.user_context_service.set_active_business(phone_number, None)  # Clear any previous selection
            session = self.user_context_service._get_or_create_session(phone_number, None)
            session["business_selection_map"] = index_to_id

            # If the user replies with a number, map it to the business ID
            if message_text.isdigit() and message_text in index_to_id:
                business_id = index_to_id[message_text]
                business = next((b for b in businesses if b["id"] == business_id), None)
                if business:
                    await self.user_context_service.set_active_business(phone_number, business_id)
                    return {
                        "message": f"You're now chatting with {business.get('business_name', business.get('name', 'this business'))}. How can I help you today?"
                    }

            # Try to search for business by name
            message_lower = message_text.lower()
            for business in businesses:
                if message_lower in business.get("business_name", business.get("name", "")).lower():
                    await self.user_context_service.set_active_business(phone_number, business["id"])
                    return {
                        "message": f"You're now chatting with {business.get('business_name', business.get('name', 'this business'))}. How can I help you today?"
                    }

            # If we couldn't match a business, list available businesses
            message = "I couldn't find that business. Please select one of the following businesses by sending their number:\n\n"
            for i, business in enumerate(businesses, 1):
                message += f"{i}: {business.get('business_name', business.get('name', 'Unknown'))} ({business.get('industry', '')})\n"
            return {"message": message}
        except Exception as e:
            logger.error(f"Error handling business selection: {str(e)}")
            return {"message": "Sorry, there was an error processing your business selection. Please try again later."}
    
    async def _process_commands(self, phone_number: str, message_text: str, current_state: str, business_id: Optional[str] = None) -> Optional[Dict]:
        """
        Process any commands or special message patterns
        
        Args:
            phone_number: User's phone number
            message_text: Message text content
            current_state: Current conversation state
            business_id: Business ID the user is interacting with
            
        Returns:
            Response dictionary if a command was processed, None otherwise
        """
        # Normalize message text for easier matching
        text_lower = message_text.lower().strip()
        
        # Check for business switching command
        if text_lower.startswith("switch to business") or text_lower.startswith("change business"):
            # Reset to business selection state
            await self.user_context_service.update_session_state(phone_number, ConversationState.BUSINESS_SELECTION, None)
            
            # List available businesses
            message = "Please select one of the following businesses by sending their number:\n\n"
            businesses = [
                {"id": 4, "business_name": "Borion Mobile Hub", "industry": "Phones"},
                {"id": 5, "business_name": "Kapambwe Cakes", "industry": "Cakes"},
                {"id": 6, "business_name": "WC Microfinance", "industry": "Loans"}
            ]
            
            for business in businesses:
                message += f"{business.get('id')}: {business.get('business_name')} ({business.get('industry')})\n"
            
            return {"message": message}
        
        # Get current business info if we have a business ID
        business_name = "Inxsource"
        if business_id:
            business = await self.supabase_client.get_business_by_id(business_id)
            if business:
                business_name = business.get("business_name", "Inxsource")
        
        # Check for help command
        if text_lower == "help":
            return {
                "message": f"Welcome to {business_name}! Here's what you can do:\n\n"
                "• Browse products: Say 'show products' or 'browse'\n"
                "• Search: Say 'search for [product name]'\n"
                "• Categories: Say 'show categories'\n"
                "• Cart: Say 'view cart', 'add to cart', or 'checkout'\n"
                "• Help: Say 'help' anytime\n"
                "• Start over: Say 'reset' to start a new conversation\n"
                "• Switch businesses: Say 'switch to business' to interact with a different business"
            }
        
        # Check for reset command
        if text_lower == "reset":
            await self.user_context_service.update_session_state(phone_number, ConversationState.GREETING, business_id)
            return {
                "message": f"I've reset our conversation. How can I help you with {business_name} today?"
            }
        
        # Check for product listing command
        if text_lower in ["show products", "products", "browse", "show me products"]:
            # Get products from database for this specific business
            products = await self.product_service.get_products(business_id=business_id, limit=5)
            
            if not products:
                return {"message": f"Sorry, I couldn't find any products for {business_name}."}
            
            # Update session state
            await self.user_context_service.update_session_state(phone_number, ConversationState.BROWSING, business_id)
            
            # Format products for WhatsApp
            formatted_products = await self.product_service.format_product_list_for_whatsapp(
                products, 
                title=f"{business_name} Products"
            )
            
            return formatted_products
        
        # Check for category listing command
        if text_lower in ["show categories", "categories", "what categories"]:
            # Get categories for this specific business
            products = await self.product_service.get_products(business_id=business_id, limit=100)
            categories = set()
            
            for product in products:
                category = product.get("category")
                if category:
                    categories.add(category)
            
            categories = sorted(list(categories))
            
            if not categories:
                return {"message": f"Sorry, I couldn't find any product categories for {business_name}."}
            
            # Update session state
            await self.user_context_service.update_session_state(phone_number, ConversationState.CATEGORY_BROWSING, business_id)
            
            # Format categories for response
            message = f"*{business_name} Product Categories*\n\n"
            for i, category in enumerate(categories, 1):
                message += f"{i}. {category}\n"
            
            message += "\nTo browse a category, reply with its name or number."
            
            return {"message": message}
        
        # Check for cart commands
        if text_lower in ["view cart", "show cart", "my cart", "cart"]:
            # Get cart contents for this specific business
            cart = await self.user_context_service.get_cart(phone_number, business_id)
            
            if not cart:
                return {"message": f"Your {business_name} cart is empty. Browse our products to add something!"}
            
            # Calculate cart total
            cart_total = await self.user_context_service.calculate_cart_total(phone_number, business_id)
            
            # Update session state
            await self.user_context_service.update_session_state(phone_number, ConversationState.CART_REVIEW, business_id)
            
            # Format cart for display
            message = f"*Your {business_name} Shopping Cart*\n\n"
            
            for i, item in enumerate(cart, 1):
                product = item.get("product", {})
                quantity = item.get("quantity", 0)
                price = product.get("price", 0)
                
                # Format price
                formatted_price = f"K{price}" if isinstance(price, (int, float)) else price
                
                message += f"{i}. {product.get('name', 'Unknown Product')} - {quantity} x {formatted_price}\n"
            
            message += f"\nTotal: K{cart_total.get('total', 0)} ({cart_total.get('item_count', 0)} items)"
            message += "\n\nReply with 'checkout' to proceed or 'continue shopping' to browse more products."
            
            return {"message": message}
        
        # Check for checkout command
        if text_lower in ["checkout", "pay", "buy", "purchase"]:
            # Get cart contents for this specific business
            cart = await self.user_context_service.get_cart(phone_number, business_id)
            
            if not cart:
                return {"message": f"Your {business_name} cart is empty. Browse our products to add something!"}
            
            # Update session state
            await self.user_context_service.update_session_state(phone_number, ConversationState.CHECKOUT, business_id)
            
            # Get business payment details
            payment_details = await self.supabase_client.get_payment_details(business_id)
            payment_info = ""
            if payment_details:
                provider = payment_details.get("provider", "")
                account = payment_details.get("account_number", "")
                if provider and account:
                    payment_info = f"\n\nPayment can be made via {provider} to {account}."
            
            # Prepare checkout message
            message = f"*{business_name} Checkout*\n\n"
            message += "To complete your purchase, please provide your details:\n"
            message += "1. Full name\n"
            message += "2. Delivery address\n"
            message += "3. Phone number for delivery\n"
            message += payment_info
            message += "\n\nExample: 'Name: John Doe, Address: 123 Main St, Lusaka, Phone: 0971234567'"
            
            return {"message": message}
        
        # Check for search command
        search_match = re.match(r"^(?:search|find|look for)\s+(.+)$", text_lower)
        if search_match:
            search_term = search_match.group(1).strip()
            
            # Search for products specific to this business
            products = await self.product_service.search_products(search_term)
            if business_id:
                # Filter products to only include those from this business
                products = [p for p in products if p.get("business_id") == business_id]
            
            if not products:
                return {"message": f"Sorry, I couldn't find any {business_name} products matching '{search_term}'."}
            
            # Update session state
            await self.user_context_service.update_session_state(phone_number, ConversationState.BROWSING, business_id)
            
            # Format products for WhatsApp
            formatted_products = await self.product_service.format_product_list_for_whatsapp(
                products, 
                title=f"{business_name} Products - '{search_term}'"
            )
            
            return formatted_products
            
        # No command matched
        return None
    
    async def _prepare_conversation_context(self, phone_number: str, current_state: str, business_id: Optional[str] = None) -> Dict:
        """
        Prepare context information for the AI response
        
        Args:
            phone_number: User's phone number
            current_state: Current conversation state
            business_id: Business ID the user is interacting with
            
        Returns:
            Dictionary with context information
        """
        context = {
            "current_state": current_state,
            "user_info": {}
        }
        
        # Add business information if available
        if business_id:
            business = await self.supabase_client.get_business_by_id(business_id)
            if business:
                context["business"] = business
                
                # Add payment details for this business
                payment_details = await self.supabase_client.get_payment_details(business_id)
                if payment_details:
                    context["payment_details"] = payment_details
        
        # Get user info if available
        user = await self.supabase_client.get_user_by_phone(phone_number)
        if user:
            context["user_info"] = user
        
        # Add cart info if available
        cart = await self.user_context_service.get_cart(phone_number, business_id)
        if cart:
            cart_total = await self.user_context_service.calculate_cart_total(phone_number, business_id)
            context["cart"] = {
                "items": cart,
                "total": cart_total
            }
        
        # Add session data
        session_data = await self.user_context_service.get_session_data(phone_number, business_id)
        context["session_data"] = session_data
        
        # Add relevant product info based on state
        if current_state == ConversationState.PRODUCT_DETAILS:
            selected_product_id = session_data.get("selected_product")
            if selected_product_id:
                product = await self.product_service.get_product_by_id(selected_product_id)
                if product:
                    context["current_product"] = product
        
        return context
    
    async def _update_conversation_state(self, phone_number: str, message_text: str, ai_response: str, business_id: Optional[str] = None):
        """
        Update the conversation state based on the message content and AI response
        
        Args:
            phone_number: User's phone number
            message_text: Original message text
            ai_response: Generated AI response
            business_id: Business ID the user is interacting with
        """
        session = await self.user_context_service.get_session(phone_number, business_id)
        current_state = session.get("state", ConversationState.GREETING)
        
        # Handle state transitions based on message content
        text_lower = message_text.lower().strip()
        
        # Extract intent from user message
        shopping_intent = any(word in text_lower for word in 
            ["buy", "shop", "purchase", "product", "price", "cost", "order"])
        checkout_intent = any(word in text_lower for word in 
            ["checkout", "pay", "complete", "finish", "order", "payment"])
        
        # Basic state transition logic
        if current_state == ConversationState.GREETING and shopping_intent:
            await self.user_context_service.update_session_state(phone_number, ConversationState.BROWSING, business_id)
        elif checkout_intent:
            await self.user_context_service.update_session_state(phone_number, ConversationState.CHECKOUT, business_id)
    
    async def _enhance_response_with_products(self, phone_number: str, ai_response: str, message_text: str, business_id: Optional[str] = None) -> Dict:
        """
        Enhance AI response with product information if needed
        
        Args:
            phone_number: User's phone number
            ai_response: Original AI response
            message_text: User's message
            business_id: Business ID the user is interacting with
            
        Returns:
            Enhanced response dictionary
        """
        session = await self.user_context_service.get_session(phone_number, business_id)
        current_state = session.get("state", ConversationState.GREETING)
        
        # Default response
        response = {"message": ai_response}
        
        # Check if we need to add product info based on state and message
        if current_state == ConversationState.PRODUCT_DETAILS:
            # Retrieve the selected product
            selected_product_id = session.get("data", {}).get("selected_product")
            if selected_product_id:
                product = await self.product_service.get_product_by_id(selected_product_id)
                if product and (not business_id or product.get("business_id") == business_id):
                    # Format product info for display
                    product_info = await self.product_service.format_product_for_whatsapp(product)
                    
                    # Check if we should return product info or AI response
                    product_question = any(word in message_text.lower() for word in 
                        ["price", "cost", "features", "details", "description", "specs", "information"])
                    
                    if product_question:
                        return product_info
                    
                    # Add product image to AI response if not already formatting product
                    response["media_url"] = product_info.get("media_url")
        
        return response 