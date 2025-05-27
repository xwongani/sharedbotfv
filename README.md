# Inxsource WhatsApp Bot

A multi-tenant WhatsApp chatbot that enables small and medium businesses (SMEs) to sell products through WhatsApp using AI-powered conversations.

## Overview

This system enables multiple businesses to share the same WhatsApp bot infrastructure while maintaining separate conversations with their customers. The bot intelligently routes messages to the correct business context and provides a personalized sales experience for each business.

### Key Features

- Multi-tenant architecture supporting multiple businesses
- AI-powered conversational sales using Google's Gemini AI
- Business-specific product catalog management
- Integrated payment processing capabilities
- Contextual conversation tracking per business-customer relationship

## Technology Stack

- **FastAPI**: Backend web framework
- **Twilio**: WhatsApp messaging API
- **Google Gemini**: AI conversational intelligence
- **Supabase**: Database and authentication
- **Python 3.10+**: Programming language

## Project Structure

```
inxsource-whatsapp-bot/
├── app/
│   ├── ai/
│   │   └── gemini_service.py
│   ├── api/
│   │   └── routes/
│   │       └── webhook.py
│   ├── business/
│   │   └── service.py
│   ├── payments/
│   │   └── service.py
│   ├── products/
│   │   └── service.py
│   ├── supabase/
│   │   └── client.py
│   ├── user_context/
│   │   └── service.py
│   ├── whatsapp/
│   │   ├── handler.py
│   │   ├── message_handler.py
│   │   └── twilio_service.py
│   └── main.py
├── tests/
│   └── ...
├── .env.example
├── README.md
└── requirements.txt
```

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- A Twilio account with WhatsApp Business API access
- A Google Cloud account with Gemini API access
- A Supabase project

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-org/inxsource-whatsapp-bot.git
   cd inxsource-whatsapp-bot
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```

5. Update the `.env` file with your credentials:
   ```
   # Twilio Configuration
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_FROM_NUMBER=whatsapp:+14155238886  # Replace with your Twilio WhatsApp number
   
   # Supabase Configuration
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   
   # Gemini AI Configuration
   GEMINI_API_KEY=your_gemini_api_key
   ```

### Running the Application

1. Start the FastAPI server:
   ```
   uvicorn app.main:app --reload
   ```

2. The API will be available at `http://localhost:8000`

3. Configure Twilio to send webhook requests to your API endpoint:
   - For local development, use a service like ngrok to expose your local server
   - Set the Twilio WhatsApp webhook URL to `https://your-domain.com/api/twilio-webhook`

## Database Schema

The application uses the following main tables in Supabase:

- `businesses`: Business profiles (name, description, contact info)
- `customers`: Customer profiles linked to businesses
- `products`: Product catalogs for each business
- `orders`: Customer orders
- `order_items`: Line items in orders
- `payments`: Payment records
- `payment_methods`: Business payment method configurations
- `business_settings`: Custom settings for each business (including AI prompts)

## License

[MIT License](LICENSE)

## Contributors

- [Your Name](https://github.com/yourusername) 