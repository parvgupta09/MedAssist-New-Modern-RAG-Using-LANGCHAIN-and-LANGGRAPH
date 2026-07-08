# This file is the master toggle switch that controls which LLMs (local vs. cloud) and API keys the whole project uses bases on development or production mode.
# It is used by the main.py file to determine which LLMs to use for the different levels of reasoning (light, moderate, heavy) and which API keys to use for the cloud LLMs.

import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# App Environment Toggling
# If we set APP_ENV to "production" it will use all the production LLMs rather than using the local Ollama LLMs.
APP_ENV = os.getenv("APP_ENV","production")

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def get_light_llm():
    """Returns the Light LLM used for Guardrails and Routing."""
    
    if APP_ENV == "development":
        return ChatOllama(model="qwen2.5:14b", temperature=0.2)
    # return ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key=GOOGLE_API_KEY, temperature=0)
    return ChatGroq(model="llama-3.3-70b-versatile", groq_api_key = GROQ_API_KEY, temperature=0)

def get_moderate_llm():
    """Returns the Moderate LLM used for intake, explanations and summarizations."""

    if APP_ENV == "development":
        return ChatOllama(model="qwen2.5:14b", temperature=0.2)
    # return ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key=GOOGLE_API_KEY, temperature=0.2)
    return ChatGroq(model="llama-3.3-70b-versatile", groq_api_key = GROQ_API_KEY, temperature=0)

def get_heavy_llm():
    """Returns the Heavy LLM used for deep differential diagnosis reasoning."""

    if APP_ENV == "development":
        return ChatOllama(model="qwen2.5:14b", temperature=0)
    return ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", google_api_key=GOOGLE_API_KEY, temperature=0)
    # return ChatGroq(model="llama-3.3-70b-versatile", groq_api_key = GROQ_API_KEY, temperature=0)