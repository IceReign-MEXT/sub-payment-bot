# Sub-Payment-Bot

A simple Telegram bot designed to handle cryptocurrency payment verification for subscription services. This bot is intended for use within a self-hosted environment, such as Termux or a cloud server.

## Features

*   Telegram Command Handling (`/start`, `/getaddress`, `/checkpayment`)
*   Solana Payment Monitoring (requires RPC URL)
*   Environment variable configuration using `.env`

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/IceReign-MEXT/sub-payment-bot.git
    cd sub-payment-bot
    ```

2.  **Install system dependencies (Termux/Linux):**
    ```bash
    # Termux example:
    pkg install build-essential clang python openssl libxml2 libxslt libffi rust
    ```

3.  **Create and activate a Python Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

4.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure environment variables:**
    Copy the `env.example` file to a new file named `.env` and fill in your details:

    ```bash
    cp env.example .env
    # Use nano or another editor to fill in the BOT_TOKEN, ADMIN_ID, etc.
    nano .env
    ```

6.  **Run the bot:**
    ```bash
    python main.py
    ```

## License

[Specify your license here if applicable]

