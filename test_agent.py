import anthropic
import os
from dotenv import load_dotenv

# Load your API key from .env file
load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')

# Create the client
client = anthropic.Anthropic(api_key=api_key)

# Send a simple message to Claude
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Say hello and tell me you're ready to build an SEO agent!"}
    ]
)

# Print the response
print(message.content[0].text)