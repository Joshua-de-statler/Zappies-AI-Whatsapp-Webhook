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
API_SECRET_KEY = os.environ.get("API_SECRET_KEY") # <-- Read the new secret key

# --- Helper Functions ---
def get_chatbot_reply(message: str, session_id: str) -> str:
    """Calls your FastAPI chatbot endpoint."""
    if not API_SECRET_KEY:
        print("Error: API_SECRET_KEY is not set in the environment.")
        return "Error: The chatbot is not configured correctly (missing API key)."

    # Add the secret key to the headers
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_SECRET_KEY
    }
    payload = {"query": message, "conversation_id": session_id}
    
    try:
        response = requests.post(CHATBOT_API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status() # This will raise an error for 4xx or 5xx status codes
        response_data = response.json()
        return response_data.get("response", "Sorry, I couldn't process that.")
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 401:
            print("Error: 401 Unauthorized. The API_SECRET_KEY is incorrect.")
            return "Sorry, I'm having trouble authenticating with my brain right now."
        else:
            print(f"HTTP error occurred: {http_err}")
            return "Sorry, a server error occurred."
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
        response = requests.post(url, headers=headers, json=data, timeout=120)
        if response.status_code == 200:
            print(f"Successfully sent message to {to_number}")
        else:
            print(f"Error sending message: {response.status_code} {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e}")

# (The rest of the webhook.py file remains unchanged)
def process_whatsapp_message(data):
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" in value:
                    message_data = value["messages"][0]
                    from_number = message_data["from"]
                    
                    if message_data.get('from_me'):
                        print(f"Ignoring outgoing message to {from_number}")
                        continue
                        
                    if message_data["type"] == "text":
                        message_text = message_data["text"]["body"]
                        print(f"Processing message: '{message_text}' from {from_number}")
                        
                        chatbot_response = get_chatbot_reply(message_text, from_number)
                        send_whatsapp_message(from_number, chatbot_response)
                    else:
                        print(f"Received non-text message: {message_data['type']}")
                        send_whatsapp_message(from_number, "I can only understand text messages.")
                        
    except (IndexError, KeyError) as e:
        print(f"Error parsing message data in thread: {e}")


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
            thread = threading.Thread(target=process_whatsapp_message, args=(data,))
            thread.start()
        
        return "OK", 200

if __name__ == "__main__":
    app.run(port=5001, debug=True)