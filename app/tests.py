from django.test import TestCase
import json
import re

# For this text, I asked ChatGPT to generate a job description based on the "Resume-Samples-1-36-2.pdf ", and now 
# I am checking if it matches

# Run the code below in cmd
# python manage.py test

class ResumeRetrievalTest(TestCase):

    def setUp(self):
        """Initialize test data before each test runs."""
        self.job_description = """
        Entry-Level Accountant (Tax & Audit Focus) Location: Roseland, NJ | Job Type: Full-Time 
        Job Summary: We are seeking a detail-oriented and motivated Entry-Level Accountant to join our team. 
        The ideal candidate has a strong foundation in accounting principles, a passion for corporate tax and auditing, 
        and excellent analytical skills. This role offers hands-on experience in tax preparation, financial auditing, 
        and bookkeeping tasks for diverse clients.
        
        Responsibilities: Assist with corporate tax audits and financial statement reviews. 
        Identify and resolve accounting discrepancies, ensuring compliance with regulations. 
        Support bookkeeping tasks, including payroll and accounts payable. 
        Prepare and file tax returns for businesses and individuals. 
        Maintain organized financial records and assist in process improvements. 
        Collaborate with senior accountants on tax credit recoveries and audit projects.
        
        Qualifications: 
        Education: Master’s in Accounting (CPA exam eligible) or Bachelor's in Finance. 
        Experience: Internship or assistant accountant role in a public accounting firm. 
        Skills: Strong analytical, problem-solving, and financial software proficiency. 
        Preferred: Membership in Beta Alpha Psi, familiarity with tax software, and audit experience.
        """

    def extract_filenames(self, response_text):
        """Extracts filenames from the HTML response text."""
        return re.findall(r"/static/files/([\w\-\.]+)", response_text)

    def test_resume_file_retrieval(self):
        """Test retrieving resume files and checking the first file name."""
        
        response = self.client.get("/chat/", {"message": self.job_description})
        self.assertEqual(response.status_code, 200)  
        
        resume_response = self.client.get("/chat/", {"message": "Give me the resumes"})
        self.assertEqual(resume_response.status_code, 200)

        response_data = json.loads(resume_response.content)

        retrieved_files = self.extract_filenames(response_data["response"])

        print(retrieved_files)
        
        first_filename = retrieved_files[0]

        self.assertEqual(first_filename, "Resume-Samples-1-36-2.pdf", "First retrieved file does not match expected.")
