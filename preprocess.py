import pandas as pd
import numpy as np
import os
import gc # Garbage collector to free up memory

# --- CONFIGURATION ---
INPUT_FILE = r"D:\Projects\NextMove\workspace_folder\dataset\LinkedIn_Job_Postings.csv"
OUTPUT_FILE = r"D:\Projects\NextMove\workspace_folder\dataset\jobs_cleaned_sample.csv"
TARGET_SAMPLE_SIZE = 100000 
CHUNK_SIZE = 25000 

def clean_chunk(df):
    """
    Cleans a specific chunk of data.
    """
    # 1. Drop completely empty rows
    df = df.dropna(how='all')

    # 2. IMMEDIATE FILTER: Drop rows where Critical Columns are NaN (null)
    # This handles the \N values converted to NaN by read_csv
    cols_to_check = ['company_name', 'title']
    df = df.dropna(subset=cols_to_check)

    # 3. Handle Date Columns
    date_cols = ['original_listed_time', 'expiry', 'closed_time', 'listed_time']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit='ms', errors='coerce')
            df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S').replace({np.nan: None})

    # 4. Clean Text Columns
    text_cols = ['description', 'title', 'skills_desc', 'company_name']
    
    for col in text_cols:
        if col in df.columns:
            # Fill N/A with empty string, force to string
            df[col] = df[col].fillna("").astype(str)
            # Remove newlines, tabs, and carriage returns
            df[col] = df[col].str.replace(r'[\n\r\t]+', ' ', regex=True)
            # Remove backslashes and double quotes
            df[col] = df[col].str.replace('\\', '', regex=False)
            df[col] = df[col].str.replace('"', "'", regex=False)
            # Trim extra whitespace
            df[col] = df[col].str.strip()

    # 5. SECONDARY FILTER: Drop rows that became empty strings after cleaning
    # (e.g. a row that was just "   " spaces would become "" and needs to be dropped)
    for col in cols_to_check:
        df = df[df[col] != ""]
        df = df[df[col] != "nan"] # specialized check for string "nan" artifacts

    return df

def process_dataset():
    print(f"Processing file: {INPUT_FILE}")
    
    sampled_chunks = []
    total_rows_seen = 0
    
    # Read CSV in chunks
    try:
        chunk_iterator = pd.read_csv(
            INPUT_FILE, 
            chunksize=CHUNK_SIZE, 
            encoding='utf-8', 
            na_values=['\\N', ''], # Treat \N and empty fields as NaN
            low_memory=False,
            on_bad_lines='skip' 
        )
    except FileNotFoundError:
        print(f"Error: File not found at {INPUT_FILE}")
        return

    for i, chunk in enumerate(chunk_iterator):
        # Clean the chunk
        clean_df = clean_chunk(chunk)
        
        # Keep valid rows
        sampled_chunks.append(clean_df)
        
        total_rows_seen += len(chunk)
        print(f"Processed chunk {i+1} (Total rows seen: {total_rows_seen})")
        
        # Free memory
        del chunk
        gc.collect()

    if not sampled_chunks:
        print("No data processed.")
        return

    print("Combining all chunks...")
    full_sample_df = pd.concat(sampled_chunks, ignore_index=True)
    
    print(f"Total valid rows collected: {len(full_sample_df)}")
    
    # Final Sampling
    if len(full_sample_df) > TARGET_SAMPLE_SIZE:
        print(f"Downsampling from {len(full_sample_df)} to {TARGET_SAMPLE_SIZE}...")
        final_df = full_sample_df.sample(n=TARGET_SAMPLE_SIZE, random_state=42)
    else:
        print(f"Keeping all {len(full_sample_df)} rows.")
        final_df = full_sample_df

    print(f"Writing {len(final_df)} rows to {OUTPUT_FILE}...")
    
    final_df.to_csv(
        OUTPUT_FILE, 
        index=False, 
        encoding='utf-8', 
        quoting=1, 
        quotechar='"'
    )
    
    print("Done! File ready for SQL import.")

if __name__ == "__main__":
    process_dataset()