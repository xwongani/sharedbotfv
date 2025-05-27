from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from app.whatsapp.router import router as whatsapp_router
from app.api.router import router as api_router
from app.twilio.service import TwilioService
from app.whatsapp.handler import WhatsAppHandler
import logging
import os
from dotenv import load_dotenv
import platform
import sys

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Validate required environment variables
def validate_environment():
    required_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "GEMINI_API_KEY",
        "BASE_URL",
        "TWILIO_WHATSAPP_NUMBER",
        "SUPABASE_URL",
        "SUPABASE_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            logger.warning(f"Missing required environment variable: {var}")
    
    if missing_vars:
        logger.error(f"Application started with missing environment variables: {', '.join(missing_vars)}")
        logger.error("The application may not function correctly without these variables")
        return False
    
    return True

# Check environment variables at startup
validate_environment()

app = FastAPI(title="Inxsource WhatsApp Sales Bot",
              description="A WhatsApp chatbot for the Inxsource platform that enables sales through WhatsApp",
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(whatsapp_router)
app.include_router(api_router)

# Initialize services
twilio_service = TwilioService()
whatsapp_handler = WhatsAppHandler()

@app.get("/")
async def root():
    return {"message": "Welcome to the Inxsource WhatsApp Sales Bot API"}

@app.post("/")
async def root_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Root webhook endpoint for backward compatibility with Twilio
    """
    try:
        # Extract form data from the request
        form_data = await request.form()
        form_dict = dict(form_data)
        
        # Log the incoming message
        logger.info(f"Received webhook at root: {form_dict}")
        
        # Extract message data
        message_data = twilio_service.extract_whatsapp_data(form_dict)
        
        # Process the message in the background for non-blocking responses
        background_tasks.add_task(
            whatsapp_handler.process_message,
            message_data
        )
        
        # Create immediate acknowledgment response
        response = "We're processing your message. Please wait a moment..."
        twiml_response = twilio_service.create_twiml_response(response)
        
        return Response(content=twiml_response, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error processing webhook at root: {str(e)}")
        # Return a basic error response
        resp = twilio_service.create_twiml_response("Sorry, we encountered an error processing your message. Please try again later.")
        return Response(content=resp, media_type="application/xml")

@app.get("/health")
async def health_check():
    """Health check endpoint that can be pinged to keep the service warm"""
    # Check essential services
    env_valid = validate_environment()
    
    # Get system info
    system_info = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "hostname": platform.node()
    }
    
    # Get environment info (without sensitive values)
    env_info = {
        "BASE_URL": os.getenv("BASE_URL"),
        "env_vars_configured": env_valid
    }
    
    # Build status response
    services_status = {
        "api": "healthy",
        "system": system_info,
        "environment": env_info,
        "uptime": "active"
    }
    
    return {
        "status": "healthy", 
        "services": services_status,
        "message": "Service is running normally"
    }

@app.get("/ping")
async def ping():
    """Simple ping endpoint to keep the service warm"""
    return {"status": "ok", "message": "pong"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 