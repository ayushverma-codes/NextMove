import csv
import os

def process_skills_column(input_file, output_file):
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: The file '{input_file}' was not found.")
        return

    try:
        with open(input_file, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames

            # Check if 'Skills' column exists
            if 'Skills' not in fieldnames:
                print("Error: Column 'Skills' not found in the CSV.")
                return

            with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
                # extrasaction='ignore' would skip the error, but we want to capture the data first
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                processed_count = 0
                for row in reader:
                    # Handle overflow data (unquoted commas in the last column often cause this)
                    skills_raw = row.get('Skills', '')
                    
                    if None in row:
                        # row[None] is a list of the extra fields found
                        extra_parts = row[None]
                        # Append them back to skills, assuming the extra commas were part of the skill list
                        skills_raw += ',' + ','.join(extra_parts)
                        # Remove the None key so DictWriter doesn't crash
                        del row[None]

                    if skills_raw:
                        # 1. Split by comma
                        # 2. Strip whitespace from each skill
                        # 3. Filter out empty strings
                        skills_list = [skill.strip() for skill in skills_raw.split(',') if skill.strip()]
                        
                        # 4. Join with "|"
                        row['Skills'] = '|'.join(skills_list)
                    
                    writer.writerow(row)
                    processed_count += 1

        print(f"Successfully processed {processed_count} rows.")
        print(f"Output saved to: {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Use raw strings (r'...') to safely handle backslashes in Windows paths
    input_csv = r'D:\Projects\NextMove\workspace_folder\input\roles.csv'
    output_csv = r'D:\Projects\NextMove\workspace_folder\input\roles.csv.bak'
    
    process_skills_column(input_csv, output_csv)