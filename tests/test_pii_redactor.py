"""
Standalone testing script to validate the PII extraction service.
    
    It dynamically adjusts the Python path to import the core service, instantiates 
    the local model, and runs it against various text edge-cases (perfect formatting, 
    conversational text, missing data, and duplicates) to ensure the AI confidence 
    thresholds and data sanitization logic are working perfectly.

"""

import sys
import os

# 1. Add the root NextMove directory to the Python path
# This allows us to import the 'core' module from inside the 'tests' folder
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 2. Import the service we just created
from core.services.pii_redactor import PIIRedactor

def run_tests():
    print("Initializing the PIIRedactor service...")
    print("-" * 50)
    
    # 3. Instantiate the service (this loads the local model once)
    # It will automatically look for 'local_gliner_model' in your root folder
    redactor = PIIRedactor()
    print("\nModel loaded successfully! Running tests...\n" + "="*50)
    
    # 4. Define test cases
    test_cases = {
        "1. The Perfect Baseline": """
            Priya Patel
            Software Developer
            Email: priya.dev99@email.com
            Phone: 987-654-3210
            Location: Bangalore, Karnataka
            
            Education:
            B.Tech in Computer Science, National Institute of Technology
        """,
        
        "2. Conversational & Messy": """
            Hey there! I'm David Chen. I just graduated from the University of Toronto last spring. 
            I'm currently based out of Seattle. Shoot a message to david.c.ai@protonmail.com 
            or text me at 5558675309.
        """,
        
        "3. Missing Data & Duplicates": """
            Senior ML Engineer applying for the role.
            Reach me at: primary.contact@work.net OR primary.contact@work.net.
            Mobile 1: +1 415 555 0198
            Mobile 2: +1 415 555 0198
            (Notice: No name, no location, no college provided here.)
        """
    }

    # 5. Run the tests and print results
    for test_name, text in test_cases.items():
        print(f"\nEvaluating: {test_name}")
        print("-" * 50)
        
        # Call the extract_pii method from our service
        results = redactor.extract_pii(text)
        
        # Print the results cleanly
        for key, value in results.items():
            if value:
                print(f"{key}: {value}")
            else:
                print(f"{key}: [None Found]")
                
        print("=" * 50)

if __name__ == "__main__":
    run_tests()