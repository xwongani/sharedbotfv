import json
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request

from app.whatsapp.handler import WhatsAppHandler

# Configure logging
logger = logging.getLogger(__name__)

class WhatsAppMessageHandler:
    """Handler for processing incoming WhatsApp messages from Twilio webhook"""
    
    def __init__(self):
        self.whatsapp_handler = WhatsAppHandler()
    
    async def process_webhook(self, request: Request) -> Dict[str, Any]:
        """
        Process incoming webhook from Twilio
        
        Args:
            request: FastAPI request object
            
        Returns:
            Empty dict to acknowledge receipt
        """
        try:
            # Parse form data from Twilio
            form_data = await request.form()
            
            # Extract relevant message data
            message_data = self._extract_message_data(form_data)
            
            if not message_data:
                logger.warning("No valid message data extracted from webhook")
                return {}
                
            # Process the message in the background without blocking
            # We don't await this call so we can return quickly to Twilio
            self.whatsapp_handler.process_message(message_data)
            
            # Return empty dict to acknowledge receipt
            return {}
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing webhook")
    
    def _extract_message_data(self, form_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Extract message data from Twilio form data
        
        Args:
            form_data: Twilio webhook form data
            
        Returns:
            Dictionary with extracted message data or None if invalid
        """
        try:
            # Check if this is a WhatsApp message event
            message_sid = form_data.get("MessageSid")
            if not message_sid:
                logger.debug("Ignored webhook - not a message event")
                return None
                
            # Extract basic message data
            from_number = form_data.get("From")
            to_number = form_data.get("To")
            body = form_data.get("Body", "").strip()
            
            # Optional: Media handling
            num_media = int(form_data.get("NumMedia", "0"))
            media_urls = []
            
            for i in range(num_media):
                media_url = form_data.get(f"MediaUrl{i}")
                if media_url:
                    media_urls.append(media_url)
            
            # Build message data object
            message_data = {
                "message_sid": message_sid,
                "from_number": from_number,
                "to_number": to_number,
                "body": body,
                "media_urls": media_urls,
                "num_media": num_media,
                "raw_data": dict(form_data)
            }
            
            logger.info(f"Extracted message from {from_number} to {to_number}")
            return message_data
            
        except Exception as e:
            logger.error(f"Error extracting message data: {str(e)}")
            return None
            
    async def send_direct_message(self, to_number: str, message: str, media_url: Optional[str] = None) -> bool:
        """
        Send a direct WhatsApp message (not in response to a webhook)
        
        Args:
            to_number: Recipient phone number
            message: Message content
            media_url: Optional URL to media to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Process through WhatsApp handler
            from_number = "whatsapp:+14155238886"  # Default Twilio number, replace with actual number from config
            
            await self.whatsapp_handler.twilio_service.send_message(
                to=to_number,
                body=message,
                media_url=media_url
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending direct message: {str(e)}")
            return False
    
    async def handle_callback(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle callback events from Twilio (delivery status, etc.)
        
        Args:
            callback_data: Callback data from Twilio
            
        Returns:
            Empty dict to acknowledge receipt
        """
        try:
            # Extract message SID and status
            message_sid = callback_data.get("MessageSid")
            status = callback_data.get("MessageStatus")
            
            if message_sid and status:
                logger.info(f"Message {message_sid} status: {status}")
            
            # Return empty dict to acknowledge receipt
            return {}
            
        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}")
            raise HTTPException(status_code=500, detail="Error handling callback") 