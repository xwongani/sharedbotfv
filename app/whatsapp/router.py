from fastapi import APIRouter, Request, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response, JSONResponse
import logging
from typing import Dict, Optional
from twilio.twiml.messaging_response import MessagingResponse

from app.twilio.service import TwilioService
from app.whatsapp.handler import WhatsAppHandler

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

# Dependency Injection
def get_twilio_service():
    return TwilioService()

def get_whatsapp_handler():
    return WhatsAppHandler()

@router.post("/webhook")
@router.post("/webhook/")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    twilio_service: TwilioService = Depends(get_twilio_service),
    whatsapp_handler: WhatsAppHandler = Depends(get_whatsapp_handler)
):
    """
    Main webhook endpoint for WhatsApp messages
    
    Processes incoming WhatsApp messages and returns TwiML responses
    """
    try:
        # Extract form data from the request
        form_data = await request.form()
        form_dict = dict(form_data)
        
        # Log the incoming message
        logger.info(f"Received webhook: {form_dict}")
        
        # Extract message data
        message_data = twilio_service.extract_whatsapp_data(form_dict)
        
        # Process the message in the background for non-blocking responses
        background_tasks.add_task(
            whatsapp_handler.process_message,
            message_data
        )
        
        # Create empty TwiML response to acknowledge receipt
        twiml_response = twilio_service.create_twiml_response("")
        
        return Response(content=twiml_response, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Return a basic error response
        resp = MessagingResponse()
        resp.message("Sorry, we encountered an error processing your message. Please try again later.")
        return Response(content=str(resp), media_type="application/xml")

@router.post("/direct-message")
@router.post("/direct-message/")
async def direct_message(
    request: Request,
    background_tasks: BackgroundTasks,
    whatsapp_handler: WhatsAppHandler = Depends(get_whatsapp_handler)
):
    """
    Endpoint for handling direct message requests
    
    This endpoint processes the message and sends responses directly,
    instead of returning TwiML
    """
    try:
        # Extract form data from the request
        form_data = await request.form()
        form_dict = dict(form_data)
        
        # Log the incoming message
        logger.info(f"Received direct message: {form_dict}")
        
        # Extract message data
        from_number = form_dict.get("From", "")
        to_number = form_dict.get("To", "")
        body = form_dict.get("Body", "")
        
        if not from_number or not body:
            logger.error("Missing required fields in direct message request")
            return JSONResponse(
                content={"error": "Missing required fields"},
                status_code=400
            )
        
        # Process the message as a direct message
        # This will send responses directly rather than returning TwiML
        background_tasks.add_task(
            whatsapp_handler.process_direct_message,
            from_number,
            to_number,
            body
        )
        
        # Return immediate acknowledgment
        return JSONResponse(
            content={"status": "processing", "message": "Message is being processed"},
            status_code=202
        )
    except Exception as e:
        logger.error(f"Error processing direct message: {str(e)}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@router.get("/status")
@router.get("/status/")
async def status(phone_number: Optional[str] = None):
    """
    Get status information about WhatsApp services
    
    Args:
        phone_number: Optional phone number to get specific user status
    """
    try:
        if phone_number:
            # Return status for specific user (would query session data)
            return {"status": "ok", "phone_number": phone_number}
        else:
            # Return general service status
            return {"status": "ok", "service": "WhatsApp Bot"}
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )