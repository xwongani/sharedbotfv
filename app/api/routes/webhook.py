from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any
import logging

from app.whatsapp.message_handler import WhatsAppMessageHandler

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create message handler instance
message_handler = WhatsAppMessageHandler()

@router.post("/twilio-webhook")
async def twilio_webhook(request: Request) -> Dict[str, Any]:
    """
    Handle incoming Twilio webhook requests for WhatsApp messages
    
    Args:
        request: The incoming request with Twilio payload
        
    Returns:
        Empty dict to acknowledge receipt
    """
    try:
        logger.info("Received Twilio webhook request")
        return await message_handler.process_webhook(request)
    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/twilio-callback")
async def twilio_callback(request: Request) -> Dict[str, Any]:
    """
    Handle Twilio status callback for message delivery status
    
    Args:
        request: The incoming request with callback data
        
    Returns:
        Empty dict to acknowledge receipt
    """
    try:
        form_data = await request.form()
        callback_data = dict(form_data)
        return await message_handler.handle_callback(callback_data)
    except Exception as e:
        logger.error(f"Error processing Twilio callback: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 