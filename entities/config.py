import os
from dotenv import load_dotenv

# Use absolute path to .env file
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=dotenv_path)

# ---------------------------
# Database 1 Credentials (Linkedin_source)
# ---------------------------
LINKEDIN_DB_HOST = os.getenv("LINKEDIN_DB_HOST")
LINKEDIN_DB_USER = os.getenv("LINKEDIN_DB_USER")
LINKEDIN_DB_PASSWORD = os.getenv("LINKEDIN_DB_PASSWORD")
LINKEDIN_DB_NAME = os.getenv("LINKEDIN_DB_NAME")


# ---------------------------
# Database 2 Credentials (Naukri_source)
# ---------------------------
NAUKRI_DB_HOST = os.getenv("NAUKRI_DB_HOST")
NAUKRI_DB_USER = os.getenv("NAUKRI_DB_USER")
NAUKRI_DB_PASSWORD = os.getenv("NAUKRI_DB_PASSWORD")
NAUKRI_DB_NAME = os.getenv("NAUKRI_DB_NAME")


# ---------------------------
# Global Schema: UnifiedJobPosting
# ---------------------------
GLOBAL_SCHEMA = {
    "job_id": "TEXT",
    "title": "TEXT",
    "company_name": "TEXT",
    "description": "TEXT",
    "skills": "TEXT",
    "experience_required": "TEXT",
    "qualifications": "TEXT",
    "location": "TEXT",
    "country": "TEXT",
    "work_type": "TEXT",
    "salary_range": "TEXT",
    "currency": "TEXT",
    "job_posting_date": "DATETIME",
    "role_category": "TEXT"
}

# ---------------------------
# GAV Mappings (Global-As-View)
# Map each global attribute to source-specific columns
# ---------------------------
GAV_MAPPINGS = {
    "Linkedin_source": {
        "job_id": "job_id",
        "title": "title",
        "company_name": "company_name",
        "description": "description",
        "skills": "skills_desc",
        "experience_required": "formatted_experience_level",
        "qualifications": None,  # Not available in source 1
        "location": "location",
        "country": None,  # Not available in source 1
        "work_type": "formatted_work_type",
        "salary_range": "normalized_salary",
        "currency": "currency",
        "job_posting_date": "listed_time",
        "role_category": None
    },
    "Naukri_source": {
        "job_id": "Job Id",
        "title": "Job Title",
        "company_name": "Company",
        "description": "Job Description",
        "skills": "skills",
        "experience_required": "Experience",
        "qualifications": "Qualifications",
        "location": "location",
        "country": "Country",
        "work_type": "Work Type",
        "salary_range": "Salary Range",
        "currency": None,
        "job_posting_date": "Job Posting Date",
        "role_category": "Role"
    }
}

# ---------------------------
# Map source to actual DB table name
# ---------------------------
SOURCE_TO_TABLE = {
    "Linkedin_source": "jobs",               
    "Naukri_source": "job_listings"        
}

# ---------------------------
# Map source to actual DB platform
# ---------------------------
SOURCE_TO_DB_Type = {
    "GLOBAL_SCHEMA": "MySQL", 
    "Linkedin_source": "MySQL",               
    "Naukri_source": "MySQL"     
}