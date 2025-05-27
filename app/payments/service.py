import logging
import os
from typing import Dict, Optional, List, Tuple, Any
import requests
from dotenv import load_dotenv
import json
import uuid
from datetime import datetime
from app.supabase.client import SupabaseClient

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class PaymentService:
    """Service for managing payment transactions"""
    
    def __init__(self):
        self.api_url = os.getenv("PAYMENT_API_URL")
        self.api_key = os.getenv("PAYMENT_API_KEY")
        self.api_secret = os.getenv("PAYMENT_API_SECRET")
        
        # In-memory tracking of payment sessions
        # In production, should use a database
        self.payment_sessions = {}
        
        self.supabase = SupabaseClient()
        logger.info("Payment service initialized")
    
    async def create_payment(self, data: Dict) -> Tuple[bool, Dict]:
        """
        Create a new payment request
        
        Args:
            data: Payment information including amount, customer details, etc.
            
        Returns:
            Tuple of (success, response_data)
        """
        try:
            # Validate required fields
            required_fields = ["amount", "phone_number", "description"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field for payment: {field}")
                    return False, {"error": f"Missing required field: {field}"}
            
            # Get auth token (mock implementation)
            token = await self._get_auth_token()
            if not token:
                return False, {"error": "Could not authenticate with payment gateway"}
            
            # Prepare payment data
            payment_data = {
                "description": data.get("description"),
                "customerFirstName": data.get("customer_first_name", "Customer"),
                "customerLastName": data.get("customer_last_name", ""),
                "email": data.get("email", f"{data.get('phone_number')}@example.com"),
                "phoneNumber": data.get("phone_number"),
                "amount": data.get("amount")
            }
            
            logger.info(f"Creating payment with data: {payment_data}")
            
            # For now, mock the API call
            # In production, this would be a real API call:
            # response = requests.post(
            #    f"{self.api_url}/payment", 
            #    headers={"Authorization": f"Bearer {token}"}, 
            #    json=payment_data
            # )
            
            # Mock response
            payment_id = f"mock_payment_{len(self.payment_sessions) + 1}"
            mock_response = {
                "paymentId": payment_id,
                "status": "pending",
                "amount": data.get("amount"),
                "currency": "ZMW",
                "paymentUrl": f"https://example.com/pay/{payment_id}",
                "message": "Payment request created successfully"
            }
            
            # Save payment session for later verification
            self.payment_sessions[payment_id] = {
                "status": "pending",
                "data": data,
                "expected_otp": "1234"  # In a real system, this would come from the payment provider
            }
            
            return True, mock_response
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            return False, {"error": str(e)}
    
    async def verify_payment_with_otp(self, payment_id: str, otp: str) -> Tuple[bool, Dict]:
        """
        Verify a payment using OTP
        
        Args:
            payment_id: ID of the payment to verify
            otp: One-time password received by the customer
            
        Returns:
            Tuple of (success, response_data)
        """
        try:
            # Check if payment exists in our tracking
            if payment_id not in self.payment_sessions:
                logger.error(f"Payment ID not found: {payment_id}")
                return False, {"error": "Payment not found"}
            
            session = self.payment_sessions[payment_id]
            
            # In a real implementation, this would call the payment API
            # Here, we just check against our mock OTP
            if otp == session["expected_otp"]:
                # Update payment status
                session["status"] = "completed"
                
                return True, {
                    "paymentId": payment_id,
                    "status": "completed",
                    "message": "Payment verified successfully"
                }
            else:
                return False, {
                    "paymentId": payment_id,
                    "status": "failed",
                    "message": "Invalid OTP"
                }
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return False, {"error": str(e)}
    
    async def get_payment_status(self, payment_id: str) -> Dict:
        """
        Get the current status of a payment
        
        Args:
            payment_id: ID of the payment to check
            
        Returns:
            Dictionary with payment status details
        """
        try:
            # Check if payment exists in our tracking
            if payment_id not in self.payment_sessions:
                logger.error(f"Payment ID not found: {payment_id}")
                return {"status": "unknown", "message": "Payment not found"}
            
            session = self.payment_sessions[payment_id]
            
            return {
                "paymentId": payment_id,
                "status": session["status"],
                "amount": session["data"].get("amount"),
                "currency": "ZMW"
            }
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_auth_token(self) -> Optional[str]:
        """Get authentication token from payment gateway"""
        try:
            # In a real implementation, this would call the payment API
            # Here, we return a mock token
            return "mock_auth_token_12345"
        except Exception as e:
            logger.error(f"Error getting auth token: {str(e)}")
            return None 
    
    async def get_payment_methods(self, business_id: str) -> List[Dict[str, Any]]:
        """
        Get available payment methods for a business
        
        Args:
            business_id: ID of the business
            
        Returns:
            List of payment method dictionaries
        """
        try:
            # Query payment_methods table for the business
            result = await self.supabase.client.table("payment_methods")\
                .select("*")\
                .eq("business_id", business_id)\
                .execute()
                
            if "error" in result:
                logger.error(f"Error fetching payment methods: {result['error']}")
                return []
                
            payment_methods = result.data
            logger.info(f"Retrieved {len(payment_methods)} payment methods for business {business_id}")
            return payment_methods
            
        except Exception as e:
            logger.error(f"Error getting payment methods: {str(e)}")
            return []
    
    async def create_order(self, 
                          business_id: str, 
                          customer_id: str, 
                          items: List[Dict[str, Any]], 
                          payment_method_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new order in the database
        
        Args:
            business_id: ID of the business
            customer_id: ID of the customer
            items: List of order items with product_id, quantity, and price
            payment_method_id: Optional ID of the payment method
            
        Returns:
            Created order object or None if failed
        """
        try:
            # Calculate totals
            subtotal = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
            
            # Create order record
            order_data = {
                "id": str(uuid.uuid4()),
                "business_id": business_id,
                "customer_id": customer_id,
                "order_date": datetime.now().isoformat(),
                "status": "pending",
                "subtotal": subtotal,
                "total": subtotal,  # Can add tax, shipping, etc. later
                "payment_method_id": payment_method_id,
                "payment_status": "pending"
            }
            
            # Insert order into database
            order_result = await self.supabase.client.table("orders").insert(order_data).execute()
            
            if "error" in order_result:
                logger.error(f"Error creating order: {order_result['error']}")
                return None
                
            # Insert order items
            for item in items:
                item_data = {
                    "id": str(uuid.uuid4()),
                    "order_id": order_data["id"],
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "price": item["price"],
                    "subtotal": item["price"] * item["quantity"]
                }
                
                item_result = await self.supabase.client.table("order_items").insert(item_data).execute()
                
                if "error" in item_result:
                    logger.error(f"Error adding order item: {item_result['error']}")
            
            logger.info(f"Created order {order_data['id']} for customer {customer_id} with {len(items)} items")
            return order_data
            
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return None
    
    async def update_order_status(self, 
                                 order_id: str, 
                                 status: str, 
                                 payment_status: Optional[str] = None) -> bool:
        """
        Update an order's status
        
        Args:
            order_id: ID of the order to update
            status: New order status (pending, processing, completed, cancelled)
            payment_status: Optional new payment status (pending, paid, failed)
            
        Returns:
            True if update succeeded, False otherwise
        """
        try:
            # Prepare update data
            update_data = {"status": status}
            if payment_status:
                update_data["payment_status"] = payment_status
                
            # Update order in database
            result = await self.supabase.client.table("orders")\
                .update(update_data)\
                .eq("id", order_id)\
                .execute()
                
            if "error" in result:
                logger.error(f"Error updating order status: {result['error']}")
                return False
                
            logger.info(f"Updated order {order_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating order status: {str(e)}")
            return False
    
    async def record_payment(self, 
                            order_id: str, 
                            payment_method_id: str, 
                            amount: float,
                            reference: str) -> Optional[Dict[str, Any]]:
        """
        Record a payment for an order
        
        Args:
            order_id: ID of the order
            payment_method_id: ID of the payment method used
            amount: Payment amount
            reference: Payment reference (e.g., mobile money transaction ID)
            
        Returns:
            Payment record or None if failed
        """
        try:
            # Create payment record
            payment_data = {
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "payment_method_id": payment_method_id,
                "amount": amount,
                "status": "completed",
                "reference": reference,
                "payment_date": datetime.now().isoformat()
            }
            
            # Insert payment into database
            result = await self.supabase.client.table("payments").insert(payment_data).execute()
                
            if "error" in result:
                logger.error(f"Error recording payment: {result['error']}")
                return None
                
            # Update order payment status
            await self.update_order_status(order_id, "processing", "paid")
                
            logger.info(f"Recorded payment of {amount} for order {order_id}")
            return payment_data
            
        except Exception as e:
            logger.error(f"Error recording payment: {str(e)}")
            return None
    
    async def get_payment_instructions(self, 
                                      business_id: str, 
                                      payment_method_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment instructions for a specific payment method
        
        Args:
            business_id: ID of the business
            payment_method_id: ID of the payment method
            
        Returns:
            Payment method details with instructions or None if not found
        """
        try:
            # Get payment method details
            result = await self.supabase.client.table("payment_methods")\
                .select("*")\
                .eq("id", payment_method_id)\
                .eq("business_id", business_id)\
                .single()\
                .execute()
                
            if "error" in result:
                logger.error(f"Error fetching payment method: {result['error']}")
                return None
                
            payment_method = result.data
            
            # Format instructions
            method_type = payment_method.get("type", "").lower()
            account_number = payment_method.get("account_number", "")
            account_name = payment_method.get("account_name", "")
            instructions = payment_method.get("instructions", "")
            
            formatted_instructions = {
                "title": f"{method_type.upper()} Payment Instructions",
                "account_number": account_number,
                "account_name": account_name,
                "instructions": instructions,
                "raw_data": payment_method
            }
            
            return formatted_instructions
            
        except Exception as e:
            logger.error(f"Error getting payment instructions: {str(e)}")
            return None
    
    async def format_payment_method_message(self, payment_method: Dict[str, Any]) -> str:
        """
        Format payment method details into a human-readable message
        
        Args:
            payment_method: Payment method details
            
        Returns:
            Formatted message with payment instructions
        """
        try:
            # Extract payment method details
            name = payment_method.get("name", "Unknown Method")
            method_type = payment_method.get("type", "").upper()
            account_number = payment_method.get("account_number", "N/A")
            account_name = payment_method.get("account_name", "")
            instructions = payment_method.get("instructions", "")
            
            # Build message
            message = f"*{name} ({method_type})*\n\n"
            
            if account_number:
                message += f"Account: {account_number}\n"
                
            if account_name:
                message += f"Name: {account_name}\n"
                
            if instructions:
                message += f"\n{instructions}\n"
                
            return message
            
        except Exception as e:
            logger.error(f"Error formatting payment method message: {str(e)}")
            return "Error displaying payment information" 