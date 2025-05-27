import os
import logging
from typing import Optional, Dict, Any
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Configure logging
logger = logging.getLogger(__name__)

class TwilioService:
    """Service for interacting with Twilio API for WhatsApp messaging"""
    
    def __init__(self):
        # Get Twilio credentials from environment variables
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        
        if not self.account_sid or not self.auth_token or not self.from_number:
            logger.warning("Twilio credentials not properly configured")
            self.is_configured = False
        else:
            # Initialize Twilio client
            self.client = Client(self.account_sid, self.auth_token)
            self.is_configured = True
            logger.info("Twilio service initialized")
    
    async def send_message(self, to: str, body: str, media_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Twilio
        
        Args:
            to: Recipient phone number with WhatsApp format (whatsapp:+1234567890)
            body: Message content
            media_url: Optional URL to media to send
            
        Returns:
            Message SID and status
        """
        if not self.is_configured:
            logger.error("Cannot send message: Twilio not properly configured")
            return {"success": False, "error": "Twilio not configured"}
            
        try:
            # Format the destination number if it doesn't have the WhatsApp prefix
            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"
                
            # Prepare message parameters
            message_params = {
                "from_": self.from_number,
                "to": to,
                "body": body
            }
            
            # Add media URL if provided
            if media_url:
                message_params["media_url"] = [media_url]
                
            # Send the message
            message = self.client.messages.create(**message_params)
            
            logger.info(f"Message sent to {to}, SID: {message.sid}")
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio error sending message: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code
            }
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get the status of a previously sent message
        
        Args:
            message_sid: The SID of the message to check
            
        Returns:
            Current message status
        """
        if not self.is_configured:
            logger.error("Cannot check message: Twilio not properly configured")
            return {"success": False, "error": "Twilio not configured"}
            
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "success": True,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio error checking message status: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code
            }
        except Exception as e:
            logger.error(f"Error checking WhatsApp message status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 