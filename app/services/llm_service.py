"""LLM service for handling interactions with language models."""
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.db.schemas.enums import SenderType


class LLMService:
    """Service for interacting with language models."""
    
    def __init__(self, client: OpenAI):
        """
        Initialize with an OpenAI client.
        
        Args:
            client: Configured OpenAI client
        """
        self.client = client
        self.default_model = "deepseek-chat"
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate a response from the language model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated text response
        """
        if not self.client:
            return "LLM client is not configured."
        
        # Prepare messages with system prompt if provided
        prompt_messages = []
        if system_prompt:
            prompt_messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation messages
        prompt_messages.extend(messages)
        
        try:
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=prompt_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating LLM response: {e}")
            return "Sorry, I encountered an error while generating a response."
    
    async def prepare_chat_history(
        self, messages: List[Any], system_prompt: str
    ) -> List[Dict[str, str]]:
        """
        Convert database messages to the format expected by the LLM API.
        
        Args:
            messages: List of Message objects from the database
            system_prompt: System prompt to prepend
            
        Returns:
            Formatted list of messages for the LLM API
        """
        history = [{"role": "system", "content": system_prompt}]
        
        for msg in messages:
            role = "user" if msg.sender == SenderType.USER else "assistant"
            history.append({"role": role, "content": msg.text})
            
        return history
    
    async def analyze_context(
        self, 
        messages: List[Dict[str, str]],
        query: str
    ) -> Dict[str, Any]:
        """
        Analyze conversation context based on a specific query.
        
        Args:
            messages: List of conversation messages
            query: Analysis instruction for the model
            
        Returns:
            Dictionary with analysis results
        """
        analysis_prompt = {
            "role": "system", 
            "content": f"Analyze the following conversation. {query}"
        }
        
        prompt_messages = [analysis_prompt] + messages
        
        try:
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=prompt_messages,
                temperature=0.2,  # Lower temperature for more factual responses
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response or return as string if parsing fails
            response_text = response.choices[0].message.content
            
            try:
                import json
                return json.loads(response_text)
            except:
                return {"error": "Failed to parse JSON", "raw_response": response_text}
            
        except Exception as e:
            print(f"Error analyzing context: {e}")
            return {"error": str(e)}
