import os
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Dict, List, Optional
import logging
import json

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY not configured")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.logger = logging.getLogger(__name__)
        
        # Sales bot system prompt
        self.system_prompt = """
        You are an AI sales assistant for Inxource, an e-commerce platform. Your name is InxBot.
        Your goal is to help customers find and purchase products through WhatsApp.
        
        Follow these guidelines:
        1. Be friendly, professional, and concise in your responses.
        2. Help customers find products, answer questions about products, and guide them through the purchasing process.
        3. When a customer wants to make a purchase, collect necessary information (product, quantity, shipping details).
        4. You can display product listings and provide images when available.
        5. Stay focused on the e-commerce context and avoid non-relevant topics.
        6. If you don't know something, be honest and suggest alternatives.
        7. Respond in the same language as the customer.
        8. Keep responses short and to the point, as this is a WhatsApp conversation.
        
        Product information and order details will be provided to you as context.
        """

    async def generate_response(
        self, 
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict] = None
    ) -> str:
        logger.info(f"Gemini Service: generate_response called with user_input: {user_input}")
        try:
            # Format conversation history for the model
            formatted_history = ""
            
            # Add system prompt first - use business-specific prompt if available
            system_prompt = self.system_prompt
            logger.info(f"Gemini Service: Context received: {context}")
            
            if context and context.get("chatbot_config") and context["chatbot_config"].get("base_prompt"):
                system_prompt = context["chatbot_config"]["base_prompt"]
                logger.info(f"Gemini Service: Using chatbot_config base_prompt")
            elif context and context.get("business"):
                business = context["business"]
                business_name = business.get("business_name", "our business")
                logger.info(f"Gemini Service: Using business-specific prompt for: {business_name}")
                system_prompt = f"""
                You are an AI sales assistant for {business_name}. 
                Your goal is to help customers find and purchase products through WhatsApp.
                
                Follow these guidelines:
                1. Be friendly, professional, and concise in your responses.
                2. Help customers find products, answer questions about products, and guide them through the purchasing process.
                3. When a customer wants to make a purchase, collect necessary information (product, quantity, shipping details).
                4. You can display product listings and provide images when available.
                5. Stay focused on helping customers with {business_name} products and services.
                6. If you don't know something, be honest and suggest alternatives.
                7. Respond in the same language as the customer.
                8. Keep responses short and to the point, as this is a WhatsApp conversation.
                
                Product information and order details will be provided to you as context.
                """
            else:
                logger.info(f"Gemini Service: Using default Inxsource system prompt")
            
            formatted_history += f"System: {system_prompt}\n\n"
            
            # Add context if available
            if context:
                context_str = json.dumps(context, ensure_ascii=False, indent=2)
                formatted_history += f"Context: {context_str}\n\n"
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = "User" if msg.get('role') == 'user' else "Assistant"
                    formatted_history += f"{role}: {msg.get('content')}\n"
            
            # Combine history with current input
            prompt = f"{formatted_history}User: {user_input}\nAssistant:"
            
            # Log truncated prompt for debugging
            truncated_prompt = prompt[:500] + "..." if len(prompt) > 500 else prompt
            logger.debug(f"Sending prompt to Gemini: {truncated_prompt}")
            
            # Generate response with safety settings
            response = await self.model.generate_content_async(prompt)
            
            if not response.text:
                logger.warning("Empty response received from Gemini API")
                return "I apologize, but I'm having trouble generating a response right now. Please try again."
                
            return response.text
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            return f"I apologize, but I'm having trouble generating a response right now. Please try again later."
    
    async def generate_product_recommendation(
        self,
        user_preferences: Dict,
        available_products: List[Dict]
    ) -> List[Dict]:
        """Generate product recommendations based on user preferences"""
        try:
            # Format product data
            products_str = json.dumps(available_products[:10], ensure_ascii=False)  # Limit to avoid token limits
            preferences_str = json.dumps(user_preferences, ensure_ascii=False)
            
            prompt = f"""
            System: You are a product recommendation system. Your task is to recommend products based on user preferences.
            
            User preferences: {preferences_str}
            
            Available products: {products_str}
            
            Recommend up to 3 products that best match the user preferences. Return your response as a JSON array of product IDs in this exact format:
            [product_id1, product_id2, product_id3]
            
            Only include the JSON array in your response, nothing else.
            """
            
            response = await self.model.generate_content_async(prompt)
            
            try:
                # Parse the response as JSON
                recommended_products = json.loads(response.text.strip())
                if isinstance(recommended_products, list):
                    return recommended_products
                return []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse product recommendation response as JSON: {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error generating product recommendations: {str(e)}")
            return [] 