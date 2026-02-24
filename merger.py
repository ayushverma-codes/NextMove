import os

def merge_files(file_paths, output_filename="merged_code.txt"):
    """
    Reads multiple files and writes their content into a single output file.
    
    Args:
        file_paths (list): A list of strings representing file paths.
        output_filename (str): The name of the resulting text file.
    """
    
    # Counter to track successful merges
    success_count = 0
    
    print(f"--- Starting Merge Process ---")
    print(f"Output file will be: {output_filename}\n")

    try:
        with open(output_filename, 'w', encoding='utf-8') as outfile:
            for path in file_paths:
                # Clean up path string (remove quotes if user pasted them with extra spaces)
                path = path.strip().strip('"').strip("'")
                
                try:
                    # Try to open the source file
                    with open(path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        
                        # Write the formatted header
                        outfile.write(f"// {path}\n")
                        
                        # Write the content
                        outfile.write(content)
                        
                        # Add a few newlines for separation between files
                        outfile.write("\n\n")
                        
                        print(f"[SUCCESS] Added: {path}")
                        success_count += 1
                        
                except FileNotFoundError:
                    print(f"[ERROR] File not found: {path}")
                    # Optionally write an error note to the output file
                    outfile.write(f"// {path}\n")
                    outfile.write(f"# ERROR: File not found at this address.\n\n")
                except Exception as e:
                    print(f"[ERROR] Could not read {path}: {e}")

        print(f"\n--- Process Complete ---")
        print(f"Successfully merged {success_count} out of {len(file_paths)} files.")
        
    except IOError as e:
        print(f"Critical Error: Could not create output file. {e}")

if __name__ == "__main__":
    # ==========================================
    # ENTER YOUR FILE ADDRESSES HERE
    # ==========================================
    # You can use absolute paths (C:/Users/...) or relative paths (script.py)
    
    files_to_merge = [
        r"D:\Projects\NextMove\app.py",
        r"D:\Projects\NextMove\chatbot_app.py",
        r"D:\Projects\NextMove\pipelines\run_pipeline.py",
        r"D:\Projects\NextMove\pipelines\query_analyzer_test_pipeline.py", 
        r"D:\Projects\NextMove\pipelines\query_decomposer_test_pipeline.py",
        r"D:\Projects\NextMove\entities\config.py",
        r"D:\Projects\NextMove\constants\__init__.py",
        r"D:\Projects\NextMove\components\LLM\llm_loader.py",
        r"D:\Projects\NextMove\components\history_manager\history_handler.py",
        r"D:\Projects\NextMove\components\connectors\mysql_connector.py",
        r"D:\Projects\NextMove\components\analyzer_and_decomposer\query_analyzer.py",
        r"D:\Projects\NextMove\components\analyzer_and_decomposer\query_decomposer.py",
        r"D:\Projects\NextMove\scripts\build_knowledge_base.py",
        r"D:\Projects\NextMove\components\synthesizer\integration.py",

    ]

    # call the function
    merge_files(files_to_merge, r"D:\Projects\NextMove\workspace_folder\artifacts\codebase.txt")