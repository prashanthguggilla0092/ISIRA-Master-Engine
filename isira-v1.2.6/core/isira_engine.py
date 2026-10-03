# PROJECT: ISIRA Supreme Engine v1.3.0 (Powered by Gemini 2.5 Flash)
# COMPONENT: Auto-Coder & File Architect
# ARCHITECT: Guggilla Prashanth
# LOCATION: Nirmal, Telangana

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
from core.security_vault import ISIRASecurity

class ISIRACore:
    def __init__(self):
        # Initializing the Supreme Security Vault
        self.vault = ISIRASecurity()
        self.api_key = self.vault.get_secret("Digital-Daari-Key")
        
        # Powering up Gemini 2.5 Flash
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash') # Currently calling flash engine

    def fetch_project_context(self, p_name: str):
        """Ultra-Stable Fetch from Google Sheets"""
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name("service-account-key.json", scope)
            client = gspread.authorize(creds)
            
            spreadsheet = client.open("Digital-daari-leads")
            sheet = spreadsheet.get_worksheet(0)
            all_values = sheet.get_all_values()
            
            headers = [h.strip() for h in all_values[0]]
            search_term = p_name.strip().upper()
            
            for row in all_values[1:]:
                row_data = [str(cell).strip() for cell in row]
                if any(search_term in str(cell).upper() for cell in row_data):
                    return dict(zip(headers, row_data))
            return None
        except Exception as e:
            print(f"DEBUG: Sheet Error -> {e}")
            return None

    def execute_auto_coder(self, project_data):
        """ISIRA generates full functional code files using 2.5 Flash"""
        print(f"\n[SUPREME BUILD] Architect {project_data['Business Name']} in Progress...")
        
        # The ultimate prompt for Gemini 2.5 Flash
        prompt = f"""
        System Role: You are ISIRA, the Supreme AI Lead Developer built by Guggilla Prashanth.
        User Context: {project_data}
        
        Task: Write the full source code for this project.
        Requirements:
        1. Include main.py (Flask/Streamlit based on needs).
        2. Include config.py for Vault security.
        3. Include requirements.txt for deployment.
        
        Strict Rule: Every file MUST start with the header:
        # PROJECT: {project_data['Business Name']}
        # ARCHITECT: Guggilla Prashanth
        # STATUS: READY FOR DEPLOYMENT
        
        Generate only pure Python code blocks.
        """
        
        response = self.model.generate_content(prompt)
        
        print("\n" + "="*60)
        print("ISIRA v1.3.0 OUTPUT (Gemini 2.5 Flash Generation)")
        print("="*60)
        print(response.text)
        print("="*60)
        print("\n[READY] Boss, your code is generated. Just copy, save and deploy!")

if __name__ == "__main__":
    print("\n--- ISIRA v1.3.0: SUPREME AUTO-CODER (Architect: Guggilla Prashanth) ---")
    engine = ISIRACore()
    target = input("Target Project Name: ")
    context = engine.fetch_project_context(target)
    
    if context:
        engine.execute_auto_coder(context)
    else:
        print("Error: Could not find project details in Sheet.")