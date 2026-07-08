# This script merges the whole diseases data into one json file to be ready for the vector database ingestion.


import json
import os

def merge_json_files(folder_path, output_filename):
    merged_data = []
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    merged_data.append(data)
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
    
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully merged {len(merged_data)} files into {output_filename}")

merge_json_files("src/data/disease_data", "src/data/merged_medical_data.json")