# AI Newsletter Assistant

This project creates an AI-powered newsletter assistant that automatically fetches, summarizes, and sends email digests using Composio and Groq.

## Features

- Automatically fetches newsletter emails from your inbox
- Summarizes newsletter content
- Enriches summaries with contextual information using Tavily
- Sends well-formatted digest emails

## Prerequisites

Before running this project, you'll need:

1. A Groq API key from [console.groq.com/keys](https://console.groq.com/keys)
2. A Tavily API key from [app.tavily.com](https://app.tavily.com/)
3. Composio integrations set up for Gmail and Tavily

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the setup script to add all required integrations:
   ```bash
   python setup.py
   ```
4. Copy `.env.example` to `.env` and fill in your API keys and target email

## Usage

Run the script:
