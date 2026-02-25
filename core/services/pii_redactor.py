"""
    The core engine for PII extraction, fully implementing the IPIIRedactor interface.
    
    This service uses a Hybrid NLP approach:
    1. Regex: Fast, deterministic extraction for strict patterns (Emails, Phones).
    2. GLiNER (AI): A bidirectional encoder model for zero-shot semantic extraction (Names, Colleges, Locations).
    
    Features:
    - Offline-First: Automatically downloads the GLiNER model to an 'artifacts' folder on the first run, 
      then strictly forces offline, local-only inference for maximum speed and data privacy.
    - Fault Tolerant: Includes strict type-checking, fallback error handling, and case-insensitive deduplication.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List

from gliner import GLiNER
from core.interfaces.redaction_interface import IPIIRedactor

# 1. Set up standard Python logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class PIIRedactor(IPIIRedactor):
    def __init__(self, model_folder_name: str = "artifacts/local_gliner_model"):
        logger.info("Initializing PIIRedactor...")
        
        # __file__ is core/services/pii_redactor.py. We go up 3 levels to the root.
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[2] 
        model_path = project_root / model_folder_name
        
        # 2. Self-Healing Step: Check for the model, and download it if missing
        self._ensure_model_exists(model_path)
            
        logger.info(f"Loading GLiNER model locally from: {model_path}")
        
        try:
            # 3. Load the model strictly offline for fast inference
            self.model = GLiNER.from_pretrained(str(model_path), local_files_only=True)
            logger.info("Local model loaded successfully.")
        except Exception as e:
            logger.error(f"Critical failure loading GLiNER model: {e}")
            raise RuntimeError(f"Model initialization failed: {e}")
            
        self.labels = [
            "Person Name", 
            "University or College", 
            "Location",
            "Degree",       
            "Job Title"     
        ]
        
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b')
        self.phone_pattern = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')

    def _ensure_model_exists(self, model_path: Path):
        """Checks if the model is downloaded, and fetches it from Hugging Face if not."""
        if model_path.exists() and model_path.is_dir() and any(model_path.iterdir()):
            logger.info("Model artifacts found locally. Skipping download.")
            return

        logger.warning(f"Model artifacts not found at {model_path}. Initiating download...")
        
        # Ensure the 'artifacts' directory exists before saving
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info("Downloading GLiNER model from Hugging Face...")
            # Temporarily connect to HF to pull the model
            temp_model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
            # Save it to our local artifacts folder
            temp_model.save_pretrained(str(model_path))
            logger.info("Download complete and saved to artifacts folder.")
        except Exception as e:
            logger.error(f"Failed to download the model: {e}")
            raise RuntimeError(f"Could not provision local model: {e}")

    def extract_pii(self, text: str) -> Dict[str, List[str]]:
        # Initialize default empty state
        pii_data = {
            "Names": [], "Emails": [], "Phones": [], 
            "Colleges": [], "Locations": []
        }
        
        # Strict Input Validation
        if not text or not isinstance(text, str):
            logger.warning("extract_pii received empty or invalid non-string data.")
            return pii_data
            
        text = text.strip()
        if not text:
            return pii_data

        # Smart Deduplication Tracking (Case-Insensitive)
        seen_items = {
            "Names": set(), "Emails": set(), "Phones": set(),
            "Colleges": set(), "Locations": set()
        }
        
        def add_entity(category: str, value: str):
            clean_value = " ".join(value.split()) 
            val_lower = clean_value.lower()
            if val_lower not in seen_items[category]:
                seen_items[category].add(val_lower)
                pii_data[category].append(clean_value)

        # --- STEP 1: Regex Extraction ---
        try:
            for email in self.email_pattern.findall(text):
                add_entity("Emails", email)
            for phone in self.phone_pattern.findall(text):
                add_entity("Phones", phone)
        except Exception as e:
            logger.error(f"Regex extraction failed: {e}")

        # --- STEP 2: GLiNER Extraction ---
        try:
            entities = self.model.predict_entities(text, self.labels, threshold=0.6)
        except Exception as e:
            logger.error(f"AI Model prediction failed: {e}")
            return pii_data 

        # --- STEP 3: Deduplication & Structuring ---
        for entity in entities:
            label = entity.get("label")
            entity_text = entity.get("text", "").strip()
            
            if not entity_text:
                continue
                
            if label == "Person Name":
                if "@" not in entity_text and "." not in entity_text and len(entity_text) < 50:
                    add_entity("Names", entity_text)
                    
            elif label == "University or College":
                if entity_text.lower() not in ["college", "university"]:
                    add_entity("Colleges", entity_text)
                    
            elif label == "Location":
                if "." not in entity_text and "www" not in entity_text.lower(): 
                    add_entity("Locations", entity_text)
                
        return pii_data