import os
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import logging
from typing import Dict, List, Optional, Union

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            logger.error("Twilio credentials not configured")
            raise ValueError("Twilio credentials not configured")
            
        self.client = Client(account_sid, auth_token)
        self.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
        
        if not self.whatsapp_number:
            logger.error("TWILIO_WHATSAPP_NUMBER not configured")
            raise ValueError("TWILIO_WHATSAPP_NUMBER not configured")
    
    async def send_message(
        self, 
        to: str, 
        body: str, 
        media_url: Optional[Union[str, List[str]]] = None
    ) -> Dict:
        """
        Send a WhatsApp message via Twilio
        
        Args:
            to: Destination phone number (with or without whatsapp: prefix)
            body: Message text content
            media_url: Optional URL(s) to media to include with the message
            
        Returns:
            Dict containing message SID and status
        """
        try:
            # Ensure the 'to' number has the whatsapp: prefix
            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"
                
            # Create message parameters
            message_params = {
                "from_": self.whatsapp_number,
                "body": body,
                "to": to
            }
            
            # Add media if provided
            if media_url:
                message_params["media_url"] = media_url
                
            # Send the message
            message = self.client.messages.create(**message_params)
            
            logger.info(f"Message sent to {to}, SID: {message.sid}")
            
            return {
                "sid": message.sid,
                "status": message.status
            }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }
    
    def create_twiml_response(self, message: str, media_url: Optional[Union[str, List[str]]] = None) -> str:
        """
        Create a TwiML response for webhook replies
        
        Args:
            message: Text message to include in the response
            media_url: Optional URL(s) to media to include with the message
            
        Returns:
            String containing the TwiML XML response
        """
        try:
            resp = MessagingResponse()
            msg = resp.message(body=message)
            
            # Add media if provided
            if media_url:
                if isinstance(media_url, list):
                    for url in media_url:
                        msg.media(url)
                else:
                    msg.media(media_url)
            
            return str(resp)
            
        except Exception as e:
            logger.error(f"Error creating TwiML response: {str(e)}")
            # Fall back to a simple response if there's an error
            resp = MessagingResponse()
            resp.message("I apologize, but I'm having trouble generating a response right now.")
            return str(resp)
    
    def extract_whatsapp_data(self, form_data: Dict) -> Dict:
        """
        Extract relevant data from Twilio webhook request
        
        Args:
            form_data: The form data from the webhook request
            
        Returns:
            Dict containing extracted WhatsApp message data
        """
        try:
            # Get key message data
            message_sid = form_data.get('MessageSid', '')
            from_number = form_data.get('From', '')
            to_number = form_data.get('To', '')
            body = form_data.get('Body', '')
            
            # Handle media if present
            num_media = int(form_data.get('NumMedia', '0'))
            media_urls = []
            
            if num_media > 0:
                for i in range(num_media):
                    media_url = form_data.get(f'MediaUrl{i}')
                    if media_url:
                        media_urls.append(media_url)
            
            # Handle location if present
            latitude = form_data.get('Latitude')
            longitude = form_data.get('Longitude')
            location = None
            
            if latitude and longitude:
                location = {
                    'latitude': latitude,
                    'longitude': longitude
                }
            
            # Put it all together
            return {
                'message_sid': message_sid,
                'from_number': from_number,
                'to_number': to_number,
                'body': body,
                'media_urls': media_urls if media_urls else None,
                'location': location,
                'num_media': num_media,
                'timestamp': form_data.get('MessageTimestamp')
            }
            
        except Exception as e:
            logger.error(f"Error extracting WhatsApp data: {str(e)}")
            # Return minimal data to prevent failures
            return {
                'from_number': form_data.get('From', ''),
                'body': form_data.get('Body', ''),
                'error': str(e)
            } 