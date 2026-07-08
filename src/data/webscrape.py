## Web Scraping logic to get the data of the 100 most common diseases and disorders from Mayo Diseases website
## It stores all the 100 diseases by nameofdiseases.json in the disease_data folder
## It follows the order of json as
"""
{
    "Category": "",
    "Disease": "",
    "Source URL": "",
    "Overview": "",
    "Symptoms": "",
    "Causes": "",
    "Risk factors": "",
    "Complications": ""
}
"""



import json
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import os

# 1. Parsing JSON data layout
json_data = """{
  "source": "Mayo Clinic",
  "version": "1.0",
  "total_diseases": 100,
  "categories": [
    {
      "category": "Respiratory",
      "diseases": [
        "Asthma",
        "Chronic Obstructive Pulmonary Disease (COPD)",
        "Pneumonia",
        "Acute Bronchitis",
        "Chronic Bronchitis",
        "Influenza",
        "COVID-19",
        "Tuberculosis",
        "Sinusitis",
        "Allergic Rhinitis"
      ]
    },
    {
      "category": "Cardiovascular",
      "diseases": [
        "Hypertension",
        "Coronary Artery Disease",
        "Atrial Fibrillation",
        "Arrhythmia",
        "High Cholesterol",
        "Peripheral Artery Disease",
        "Deep Vein Thrombosis"
      ]
    },
    {
      "category": "Diabetes & Endocrine",
      "diseases": [
        "Type 1 Diabetes",
        "Type 2 Diabetes",
        "Prediabetes",
        "Hypothyroidism",
        "Hyperthyroidism",
        "Hashimoto's Disease",
        "Graves' Disease",
        "Polycystic Ovary Syndrome (PCOS)"
      ]
    },
    {
      "category": "Digestive System",
      "diseases": [
        "Gastroesophageal Reflux Disease (GERD)",
        "Gastritis",
        "Peptic Ulcer Disease",
        "Irritable Bowel Syndrome (IBS)",
        "Crohn's Disease",
        "Ulcerative Colitis",
        "Gallstones",
        "Appendicitis",
        "Constipation",
        "Diarrhea"
      ]
    },
    {
      "category": "Liver & Pancreas",
      "diseases": [
        "Fatty Liver Disease",
        "Hepatitis A",
        "Hepatitis B",
        "Hepatitis C",
        "Cirrhosis"
      ]
    },
    {
      "category": "Kidney & Urinary",
      "diseases": [
        "Kidney Stones",
        "Urinary Tract Infection",
        "Chronic Kidney Disease",
        "Acute Kidney Injury",
        "Benign Prostatic Hyperplasia (BPH)",
        "Urinary Incontinence"
      ]
    },
    {
      "category": "Neurology",
      "diseases": [
        "Migraine",
        "Epilepsy",
        "Parkinson's Disease",
        "Alzheimer's Disease",
        "Dementia",
        "Multiple Sclerosis",
        "Bell's Palsy",
        "Peripheral Neuropathy"
      ]
    },
    {
      "category": "Mental Health",
      "diseases": [
        "Depression",
        "Generalized Anxiety Disorder",
        "Panic Disorder",
        "Obsessive-Compulsive Disorder (OCD)",
        "Bipolar Disorder",
        "Schizophrenia",
        "Post-Traumatic Stress Disorder (PTSD)",
        "Insomnia"
      ]
    },
    {
      "category": "Bone, Joint & Muscle",
      "diseases": [
        "Osteoarthritis",
        "Rheumatoid Arthritis",
        "Osteoporosis",
        "Gout",
        "Fibromyalgia",
        "Sciatica",
        "Carpal Tunnel Syndrome",
        "Tendinitis"
      ]
    },
    {
      "category": "Skin",
      "diseases": [
        "Acne",
        "Eczema",
        "Psoriasis",
        "Rosacea",
        "Cellulitis",
        "Vitiligo",
        "Ringworm",
        "Shingles"
      ]
    },
    {
      "category": "Eye",
      "diseases": [
        "Cataract",
        "Glaucoma",
        "Conjunctivitis",
        "Dry Eye Syndrome",
        "Age-related Macular Degeneration"
      ]
    },
    {
      "category": "ENT",
      "diseases": [
        "Tonsillitis",
        "Otitis Media",
        "Hearing Loss",
        "Vertigo",
        "Tinnitus"
      ]
    },
    {
      "category": "Blood Disorders",
      "diseases": [
        "Iron Deficiency Anemia",
        "Thalassemia",
        "Hemophilia",
        "Leukemia"
      ]
    },
    {
      "category": "Infectious Diseases",
      "diseases": [
        "Dengue Fever",
        "Malaria",
        "Typhoid Fever",
        "HIV/AIDS",
        "Chickenpox"
      ]
    }
  ]
}
"""

data_blueprint = json.loads(json_data)

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
scraped_dataset = []


def get_mayo_url(disease_name):
    search_url = f"https://www.mayoclinic.org/search/search-results?q={disease_name.replace(' ', '+')}"
    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        link = soup.find("a", href=lambda h: h and "/diseases-conditions/" in h and "/symptoms-causes/" in h)
        if link:
            href = link["href"]
            return "https://www.mayoclinic.org" + href if href.startswith("/") else href
    except Exception as e:
        print(f"Search failed for {disease_name}: {e}")
    return None

def scrape_mayo_disease(url):
    sections = {"Overview": "", "Symptoms": "", "Causes": "", "Risk factors": "", "Complications": ""}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return sections
            
        soup = BeautifulSoup(res.content, "html.parser")
        
        # 1. Broadly target the main content area
        main_body = soup.find("main") or soup.find("article") or soup.find("div", {"id": "main-content"})
        
        if not main_body:
            return sections

        # 2. Grab all text elements (h2, h3, p, ul) in order to maintain flow
        # This captures everything regardless of specific class names
        elements = main_body.find_all(['h2', 'h3', 'p', 'ul'])
        
        current_section = "Overview"
        
        for el in elements:
            text = el.get_text(separator=' ', strip=True)
            
            # If we hit a header, switch the "current section"
            if el.name in ['h2', 'h3']:
                found_key = False
                for key in sections.keys():
                    if key.lower() in text.lower():
                        current_section = key
                        found_key = True
                        break
                if not found_key and el.name == 'h2':
                    current_section = "Other" # Ignore miscellaneous sections
            
            # If it's a paragraph or list, add it to the current section
            elif current_section in sections:
                sections[current_section] += " " + text

        return sections

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return sections

# 2. Extracting targets from structure
scraped_dataset = []

for cat_block in data_blueprint["categories"]:
    category_name = cat_block["category"]
    
    for disease in cat_block["diseases"]:
        print(f"Processing: {disease}")
        
        # 1. Get URL
        url = get_mayo_url(disease)
        
        # 2. Get Sections
        sections = scrape_mayo_disease(url) if url else {"Overview": "", "Symptoms": "", "Causes": "", "Risk factors": "", "Complications": ""}
        
        # 3. Create the data object
        disease_record = {
            "Category": category_name,
            "Disease": disease,
            "Source URL": url,
            **sections
        }
        
        # 4. Save to an individual file
        # Clean the disease name to be a safe filename
        filename = f"{disease.replace('/', '-').replace(' ', '_').lower()}.json"
        filepath = os.path.join("src/data/disease_data", filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(disease_record, f, indent=4, ensure_ascii=False)
            
        print(f"Saved: {filename}")
        time.sleep(5.0)