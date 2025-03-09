import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pathlib import Path
import json

# Run command below to run this file and get the data
# python "/home/jovyan/OneDrive/Ambiente de Trabalho/Interviews/Cymbiotika/resume_screening/app/static/management/gather_data.py"
  
current_path = Path(__file__).resolve()
for parent in current_path.parents:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
        break

# Now you can access the API key
os.getenv("OPENAI_API_KEY")

llm = init_chat_model("gpt-4o")

SCOPES = ["https://www.googleapis.com/auth/drive"]

FOLDER_ID = "1YVPomt1xV_GBqE0IaUsydybqUX9WhaO7"

DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "files"))

save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed_resumes.json"))

# Authenticate function
def authenticate():

    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)

# Get files information
def list_files_in_folder(service, folder_id):

    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

# Download files
def download_file(service, file_id, file_name, download_path):

    request = service.files().get_media(fileId=file_id)
    file_path = os.path.join(download_path, file_name)

    with open(file_path, "wb") as file:
        file.write(request.execute())

    print(f"Downloaded: {file_name}")

# Extract information from resumes
def extract_resume_text(folder_path):
    resumes = []
    for file in os.listdir(folder_path):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(folder_path, file))
            pages = []
            for page in loader.load():
                pages.append(page.page_content)  # Get text from each page
            
            resume_text = " ".join(pages)  # Combine all pages into one text
            resumes.append({"file": file, "text": resume_text})
    return resumes

def summarize_resume(resume):
    
    prompt = f"""
        Based on the following resume, generate a structured and detailed profile suitable for matching future job descriptions. Organize the output into the following sections:

        - Information: Name, email, phone number
        - Candidate Summary: A brief professional summary highlighting key strengths, experience, and career focus.
        - Core Skills: List of technical and soft skills relevant to job applications.
        - Work Experience: Structured descriptions of previous roles, including job title, company name, dates of employment, responsibilities, key achievements, and technologies used.
        - Education: Degree(s), university name, graduation year, and relevant coursework if applicable.
        - Certifications & Training: Any relevant certifications or training programs completed.
        - Projects & Portfolio: Notable projects, personal or professional, with a brief description of objectives and outcomes.
        - Industry Keywords: A list of relevant industry terms, skills, and technologies that enhance job-matching capabilities.

        If the user doesn't have any of the sections, go to the next section.
        Don't add any other random text, just the answer to my request.

        Here is the resume:

        {resume}
    """

    return llm.invoke(prompt).content

def main():
    try:
        service = authenticate()

        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

        files = list_files_in_folder(service, FOLDER_ID)

        if not files:
            print("⚠ No files found in the folder.")
            return

        for file in files:
            download_file(service, file["id"], file["name"], DOWNLOAD_DIR)

        processed_resumes = extract_resume_text(DOWNLOAD_DIR)
        
        for file in processed_resumes:
            file["summary"] = summarize_resume(file["text"])
            print(f"Done {file['file']}")

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(processed_resumes, f, ensure_ascii=False, indent=4)
      
        print("\nAll files downloaded successfully!")

    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    main()

