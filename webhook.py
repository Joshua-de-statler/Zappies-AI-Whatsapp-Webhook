import os
import requests
import json
import threading
from flask import Flask, request
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Setup and Configuration ---
app = Flask(__name__)

ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
CHATBOT_API_URL = os.environ.get("CHATBOT_API_URL", "http://localhost:8000/chat")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

# --- Helper Functions ---
def get_chatbot_reply(message: str, session_id: str) -> str:
    """Calls your FastAPI chatbot endpoint."""
    headers = {"Content-Type": "application/json"}
    payload = {"query": message, "conversation_id": session_id}
    
    try:
        response = requests.post(CHATBOT_API_URL, headers=headers, json=payload, timeout=10) # Added timeout
        response.raise_for_status()
        response_data = response.json()
        return response_data.get("response", "Sorry, I couldn't process that.")
    except requests.exceptions.RequestException as e:
        print(f"Error calling chatbot API: {e}")
        return "Sorry, I'm having trouble connecting to my brain right now."

def send_whatsapp_message(to_number: str, message: str):
    """Sends a message via the Meta Graph API."""
    if not all([ACCESS_TOKEN, PHONE_NUMBER_ID]):
        print("Missing environment variables for sending WhatsApp message.")
        return

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": message}}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10) # Added timeout
        if response.status_code == 200:
            print(f"Successfully sent message to {to_number}")
        else:
            print(f"Error sending message: {response.status_code} {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e}")

# NEW: Function to process messages in the background
def process_whatsapp_message(data):
    """
    This function handles the core logic in a separate thread.
    """
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" in value:
                    message_data = value["messages"][0]
                    from_number = message_data["from"]
                    
                    # NEW: Add a check to prevent the bot from replying to itself.
                    # This compares the sender's number with the bot's number ID.
                    if message_data.get('from_me'): # Another way to check if message is from the bot
                        print(f"Ignoring outgoing message to {from_number}")
                        continue
                        
                    if message_data["type"] == "text":
                        message_text = message_data["text"]["body"]
                        print(f"Processing message: '{message_text}' from {from_number}")
                        
                        # Get reply from chatbot and send it
                        chatbot_response = get_chatbot_reply(message_text, from_number)
                        send_whatsapp_message(from_number, chatbot_response)
                    else:
                        print(f"Received non-text message: {message_data['type']}")
                        send_whatsapp_message(from_number, "I can only understand text messages.")
                        
    except (IndexError, KeyError) as e:
        print(f"Error parsing message data in thread: {e}")


# --- Webhook Endpoint ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
            if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
                return "Verification token mismatch", 403
            return request.args["hub.challenge"], 200
        return "Webhook is active.", 200

    elif request.method == "POST":
        data = request.get_json()
        
        if data and data.get("object") == "whatsapp_business_account":
            # MODIFIED: Start a thread to process the message and respond immediately
            thread = threading.Thread(target=process_whatsapp_message, args=(data,))
            thread.start()
        
        # Respond to Meta immediately to prevent retries
        return "OK", 200

# --- Run the Application ---
if __name__ == "__main__":
    app.run(port=5001, debug=True)

