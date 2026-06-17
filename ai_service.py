"""
AI Service for Medical Waste Dashboard
Uses Groq API with Llama model for recommendations and chat
"""

from openai import OpenAI
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize the client
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

# Model to use
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Caches
recommendation_cache = {}
conversation_cache = {}  # Stores chat history per page
CACHE_DURATION = timedelta(hours=1)
MAX_CONVERSATION_TURNS = 6  # Keep last 6 messages (3 back-and-forth)

# System prompt - focused on screenshot analysis
SYSTEM_PROMPT = """You are an expert medical waste management consultant integrated into a hospital's Medical Waste Monitoring Dashboard. You can see the dashboard screenshot provided to you.

## YOUR ROLE
Analyze the dashboard screenshot to provide actionable, data-driven recommendations. You can see charts, KPIs, and all visual elements on the screen.

## WHAT YOU CAN HELP WITH
- Questions about the dashboard, charts, and data you can see
- Medical waste management and hospital sustainability
- Cost reduction strategies for waste disposal
- Emissions reduction and environmental impact
- Department waste performance analysis
- Waste forecasting and optimization strategies
- Explaining what's shown on any chart or KPI

## WHAT YOU CANNOT HELP WITH
- Topics completely unrelated to the dashboard, hospital, or waste management
- General knowledge questions, jokes, stories, or entertainment
- Personal advice unrelated to waste management

For off-topic requests, respond: "I can only assist with questions about this dashboard and medical waste management. What would you like to know about the waste data?"

## WASTE CATEGORIES
- Yellow bags: Infectious & Anatomical waste - can use autoclave (cheaper) or incineration
- Red bags: Highly Infectious waste - MUST be incinerated
- Blue bags: Chemotherapy waste - MUST be incinerated

## TREATMENT METHODS
- Incineration: Higher cost, required for Red & Blue bags
- Autoclave: Lower cost, lower emissions, allowed for Yellow bags
- Recycling: For general waste - produces negative emissions
- Landfill: For non-recyclable general waste

## GUIDELINES
1. Base ALL your analysis on what you can see in the screenshot
2. Reference specific numbers, colors, and trends visible in the charts
3. Do NOT make up data or use generic recommendations
4. Keep initial recommendations to 2-3 sentences
5. If you cannot see something clearly, say so honestly
6. NEVER mention or guess the hospital's name - refer to it only as "the hospital"
"""


def get_recommendation(kpis, context='overview', custom_prompt=None, screenshot_base64=None, period=None):
    """Generate AI recommendation based primarily on screenshot."""
    
    # Check cache
    cache_key = f"{context}_{period or 'default'}"
    if not screenshot_base64 and cache_key in recommendation_cache:
        cached = recommendation_cache[cache_key]
        if cached['expires'] and datetime.now() < cached['expires']:
            return cached['text']
    
    page_names = {
        'overview': 'Overview',
        'departments': 'Departments',
        'hazardous': 'Hazardous Waste',
        'emissions': 'Emissions',
        'costs': 'Costs',
        'trends': 'Trends & Forecasting',
        'optimization': 'Optimization'
    }
    page_name = page_names.get(context, context.title())
    
    instruction = custom_prompt or f"You are viewing the {page_name} page of the dashboard. Based on what you can see in this screenshot, provide a brief (2-3 sentences) actionable recommendation. Focus on the most important insight from the visible data."
    
    try:
        if screenshot_base64:
            # Screenshot-only mode - let the AI read the image
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_base64}",
                                "detail": "high"
                            }
                        },
                        {"type": "text", "text": instruction}
                    ]
                }
            ]
        else:
            # Fallback: minimal context, encourage general advice
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user", 
                    "content": f"The user is on the {page_name} page but no screenshot is available. Provide a general recommendation for analyzing {page_name.lower()} data in medical waste management."
                }
            ]
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.4
        )
        
        recommendation = response.choices[0].message.content.strip()
        
        # Cache result
        if not screenshot_base64:
            recommendation_cache[cache_key] = {
                'text': recommendation,
                'expires': datetime.now() + CACHE_DURATION
            }
        
        return recommendation
    
    except Exception as e:
        print(f"AI API Error: {e}")
        return "Unable to generate recommendation at this time."


def chat_with_ai(kpis, user_question, context='overview', custom_context=None, screenshot_base64=None, period=None, session_id=None):
    """Handle user's question with conversation memory."""
    
    page_names = {
        'overview': 'Overview',
        'departments': 'Departments', 
        'hazardous': 'Hazardous Waste',
        'emissions': 'Emissions',
        'costs': 'Costs',
        'trends': 'Trends & Forecasting',
        'optimization': 'Optimization'
    }
    page_name = page_names.get(context, context.title())
    
    # Get or create conversation history for this session/page
    conv_key = session_id or context
    if conv_key not in conversation_cache:
        conversation_cache[conv_key] = []
    
    conversation_history = conversation_cache[conv_key]
    
    try:
        # Build messages with history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history (without images to save tokens)
        for msg in conversation_history[-MAX_CONVERSATION_TURNS:]:
            messages.append(msg)
        
        # Add current user message
        if screenshot_base64:
            current_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_base64}",
                            "detail": "high"
                        }
                    },
                    {"type": "text", "text": f"[{page_name} page] {user_question}"}
                ]
            }
        else:
            current_message = {
                "role": "user",
                "content": f"[{page_name} page] {user_question}"
            }
        
        messages.append(current_message)
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=400,
            temperature=0.4
        )
        
        assistant_response = response.choices[0].message.content.strip()
        
        # Store in conversation history (text only to save space)
        conversation_history.append({"role": "user", "content": f"[{page_name} page] {user_question}"})
        conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # Trim history if too long
        if len(conversation_history) > MAX_CONVERSATION_TURNS * 2:
            conversation_cache[conv_key] = conversation_history[-MAX_CONVERSATION_TURNS * 2:]
        
        return assistant_response
    
    except Exception as e:
        print(f"AI Chat Error: {e}")
        return "Sorry, I couldn't process your question. Please try again."


def clear_cache(context=None):
    """Clear recommendation and conversation cache"""
    if context:
        # Clear recommendation cache
        keys_to_remove = [k for k in recommendation_cache if k.startswith(context)]
        for k in keys_to_remove:
            del recommendation_cache[k]
        # Clear conversation cache
        if context in conversation_cache:
            del conversation_cache[context]
    else:
        recommendation_cache.clear()
        conversation_cache.clear()