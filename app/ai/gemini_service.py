import os
import logging
import json
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Configure logging
logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google's Gemini AI"""
    
    def __init__(self):
        # Get API key from environment variables
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            logger.warning("Gemini API key not configured")
            self.is_configured = False
        else:
            # Configure the Gemini API
            genai.configure(api_key=api_key)
            self.is_configured = True
            
            # Set default parameters
            self.model = genai.GenerativeModel(
                model_name="gemini-pro",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                },
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                }
            )
            
            logger.info("Gemini AI service initialized")
    
    async def generate_response(self, 
                              prompt: str, 
                              context: Optional[Dict[str, Any]] = None, 
                              history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate a response from Gemini AI
        
        Args:
            prompt: User message/prompt
            context: Optional context information
            history: Optional conversation history
            
        Returns:
            Generated response
        """
        if not self.is_configured:
            logger.error("Cannot generate response: Gemini AI not configured")
            return "I'm sorry, but I'm currently unavailable. Please try again later."
            
        try:
            # Format the prompt with context if provided
            formatted_prompt = self._format_prompt(prompt, context)
            
            # Create chat session with history if provided
            if history:
                chat = self.model.start_chat(history=history)
                response = chat.send_message(formatted_prompt)
            else:
                response = self.model.generate_content(formatted_prompt)
            
            # Extract the text from the response
            response_text = response.text
            
            logger.info(f"Generated AI response of {len(response_text)} characters")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "I'm sorry, but I had trouble understanding. Could you please try again?"
    
    def _format_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Format the prompt with context information
        
        Args:
            prompt: User message/prompt
            context: Optional context information
            
        Returns:
            Formatted prompt
        """
        formatted_prompt = prompt
        
        if context:
            # Add business information
            business = context.get("business")
            if business:
                business_name = business.get("name", "")
                business_description = business.get("description", "")
                
                formatted_prompt = f"""
                You are an AI sales assistant for {business_name}. 
                
                Business description: {business_description}
                
                User message: {prompt}
                """
            
            # Add custom prompt from business settings
            custom_prompt = context.get("custom_prompt")
            if custom_prompt:
                formatted_prompt = f"{custom_prompt}\n\nUser message: {prompt}"
                
            # Add product context if available
            products = context.get("products")
            if products:
                products_json = json.dumps(products, indent=2)
                formatted_prompt += f"\n\nAvailable products: {products_json}"
                
            # Add customer information if available
            customer = context.get("customer")
            if customer:
                customer_name = customer.get("name", "the customer")
                formatted_prompt += f"\n\nYou are speaking with {customer_name}."
        
        return formatted_prompt
    
    async def format_product_recommendation(self, 
                                          products: List[Dict[str, Any]], 
                                          user_query: str) -> Dict[str, Any]:
        """
        Generate AI-powered product recommendations
        
        Args:
            products: List of available products
            user_query: User's query/requirements
            
        Returns:
            Recommended products with explanation
        """
        if not self.is_configured:
            logger.error("Cannot generate recommendations: Gemini AI not configured")
            return {
                "recommendations": [],
                "explanation": "Product recommendations are unavailable at the moment."
            }
            
        try:
            # Format the products as JSON string
            products_json = json.dumps(products, indent=2)
            
            # Create recommendation prompt
            prompt = f"""
            Based on the following products and the user's query, recommend the most suitable products.
            
            Products:
            {products_json}
            
            User Query:
            {user_query}
            
            Return a JSON object with the following structure:
            {{
                "recommendations": [
                    {{
                        "product_id": "ID of the recommended product",
                        "reason": "Short explanation of why this product is recommended"
                    }}
                ],
                "explanation": "Overall explanation of the recommendations"
            }}
            
            Only include up to 3 of the most relevant products.
            """
            
            # Generate recommendation
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extract JSON from response
            try:
                # Find JSON in the response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    recommendations = json.loads(json_str)
                    
                    logger.info(f"Generated recommendations with {len(recommendations.get('recommendations', []))} products")
                    return recommendations
                else:
                    # Fallback if JSON not found
                    logger.warning("Could not extract JSON from AI response")
                    return {
                        "recommendations": [],
                        "explanation": response_text
                    }
            except json.JSONDecodeError:
                logger.error("Error parsing AI recommendation JSON")
                return {
                    "recommendations": [],
                    "explanation": response_text
                }
            
        except Exception as e:
            logger.error(f"Error generating product recommendations: {str(e)}")
            return {
                "recommendations": [],
                "explanation": "Sorry, I couldn't generate product recommendations at this time."
            } 