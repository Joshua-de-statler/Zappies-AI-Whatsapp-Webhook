# WhatsApp Chatbot Webhook Setup Guide

Follow these steps to connect your chatbot to WhatsApp.

## Step 1: Install Dependencies

Open your terminal in the project directory and run:
```bash
pip install -r requirements.txt
```

## Step 2: Update Your `.env` File

Copy your credentials from the Meta for Developers dashboard into the `.env` file you created.
- `WHATSAPP_TOKEN`: The temporary or permanent access token.
- `PHONE_NUMBER_ID`: Found directly below the access token field.
- `VERIFY_TOKEN`: Make up a secure string. You will use this in the dashboard.

## Step 3: Run Your Services

You need to run three separate processes in three different terminal windows.

**Terminal 1: Start your Chatbot API**
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

**Terminal 2: Start the Webhook Server**
```bash
python webhook.py
```
This server will now be running locally on port 5001.

**Terminal 3: Expose Your Webhook with ngrok**

[Download ngrok](https://ngrok.com/download) if you haven't already.
```bash
# This command exposes your local port 5001 to the internet.
ngrok http 5001
```
ngrok will provide a public HTTPS URL (e.g., `https://random-string.ngrok-free.app`). **Copy this URL.**

## Step 4: Configure the Webhook in Meta for Developers

1.  Go to your app's dashboard on [Meta for Developers](https://developers.facebook.com/).
2.  Navigate to **WhatsApp -> API Setup**.
3.  Under "Step 2: Configure webhook", click **Edit**.
4.  **Callback URL:** Paste the `https` URL from ngrok and add `/webhook` to the end.
    -   Example: `https://random-string.ngrok-free.app/webhook`
5.  **Verify token:** Enter the exact same string you used for `VERIFY_TOKEN` in your `.env` file.
6.  Click **Verify and save**. You should see a success message.
7.  Next to the webhook section, click **Manage** and subscribe to the `messages` event.

## Step 5: Test It!

Use the "API Setup" page to send a test message to your configured phone number, or simply message the number from WhatsApp. Check the terminal running `webhook.py` to see the incoming message being processed.