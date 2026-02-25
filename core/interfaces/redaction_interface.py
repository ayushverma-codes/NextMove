"""
    Defines the strict contract (Interface) for any PII extraction service in the application.
    By using an Abstract Base Class (ABC), we ensure that the web layer (FastAPI/Django) 
    never has to know *how* the AI works, only that it can call 'extract_pii()' and get 
    a guaranteed dictionary format back. This makes swapping AI models in the future effortless.
"""

from abc import ABC, abstractmethod
from typing import Dict, List

class IPIIRedactor(ABC):
    """
    Abstract Base Class for PII extraction and redaction services.
    Any class implementing this interface must provide the extract_pii method.
    """
    
    @abstractmethod
    def extract_pii(self, text: str) -> Dict[str, List[str]]:
        """
        Takes raw text and returns a dictionary of extracted PII entities.
        
        Expected return format:
        {
            "Names": [],
            "Emails": [],
            "Phones": [],
            "Colleges": [],
            "Locations": []
        }
        """
        pass