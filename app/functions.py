import os
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import GoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.docstore.document import Document
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field
from typing import Optional, List, Tuple
from pathlib import Path
import json

current_path = Path(__file__).resolve()
for parent in current_path.parents:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
        break

file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "data", "processed_resumes.json"))

with open(file_path, "r", encoding="utf-8") as f:
    processed_resumes = json.load(f)

llm = GoogleGenerativeAI(model="models/gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))

embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

docs = [Document(page_content=res["summary"], metadata={"source": res["file"]}) for res in processed_resumes]

vector_store = InMemoryVectorStore.from_documents(docs, embeddings)

chat_memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

class AgentState(BaseModel):
    user_input: Optional[str] = Field(default=None, description="User's latest input message")
    response: Optional[List[str]] = Field(default=None, description="Generated response to the user")
    related: Optional[str] = Field(default=None, description="Indicates relation status of the current conversation")
    retrieved_files: Optional[List[Tuple[str, str]]] = Field(default=None, description="List of retrieved files (source, page_content)")
    last_action: Optional[str] = Field(default=None, description="Last operation performed")

    def update_user_input(self, input_text: str):
        """Updates the user input."""
        self.user_input = input_text

    def update_response(self, response_text: str):
        """Ensures the response is stored as a list."""
        if isinstance(response_text, list):
            self.response = response_text  # If already a list, keep it as is
        else:
            self.response = [response_text]  # Convert string to a list

    def update_retrieved_files(self, files: List[Tuple[str, str]]):
        """Updates the list of retrieved files."""
        self.retrieved_files = files

    def store_relation(self, relation_status: str):
        """Stores relation status for conversation tracking."""
        self.related = relation_status

    def update_last_action(self, action: str):
        """Updates the last performed action."""
        self.last_action = action



def check_context(state: AgentState) -> AgentState:

    memory = chat_memory.load_memory_variables({}).get("chat_history", [])
    
    prompt = f"""
        Based on the message and the memory, is this request related to the one before or are we talking about a new position?
        If the user is talking about a new position return "New", otherwise "Old".

        User: {state.user_input}

        Memory: {memory}

        Return ONLY New or Old.
    """

    related = llm.invoke(prompt).strip()

    state.store_relation(related)

    return state

def first_router(state: AgentState):
    
    return state.related



def find_top_5_best_fit(state) -> AgentState:

    # Clear old retrieved files
    state.update_retrieved_files([])
    
    prompt = f"""
        Structure the job description in a way that can be used to best match resumes descriptions which have the format below.

        - Information: Name, email, phone number
        - Candidate Summary: A brief professional summary highlighting key strengths, experience, and career focus.
        - Core Skills: List of technical and soft skills relevant to job applications.
        - Work Experience: Structured descriptions of previous roles, including job title, company name, dates of employment.
        - Education: Degree(s), university name, graduation year.
        - Certifications & Training: Any relevant certifications or training programs completed.
        - Industry Keywords: A list of relevant industry terms, skills, and technologies that enhance job-matching capabilities.

        Don't add any other random text, just the answer to my request.

        Description: {state.user_input}
    """

    text_to_match = llm.invoke(prompt).strip()

    results = vector_store.similarity_search(text_to_match, k=5)

    document_info = [(doc.metadata["source"], doc.page_content) for doc in results]

    state.update_retrieved_files(document_info)

    state.update_last_action("find_top_5_best_fit")

    return state



def retrieve_request(state: AgentState) -> AgentState:
    prompt = f"""
        Based on the request of the user, route my next step:

        - If the user is giving a job description, return "candidates_description".
        - If the user is asking for you to be more detailed, return "get_details"
        - If he is asking specifically to answer with the resume files, return "get_resume_by_filename"

        User Text: {state.user_input}

        Return ONLY get_resume_by_filename, get_details or candidates_description.
    """

    route = llm.invoke(prompt).strip()

    state.update_last_action(route)

    return state



def get_details(state: AgentState) -> AgentState:

    candidates_info = []

    prompt = f"""
        Understand from the user request, which candidates the user wants more information.
        If the user specifies that wants from the first 3 for example, return 1,2,3.
        If the user specify names, return the number they are in the order of the information candidates I will provide.

        User Text: 
        {state.user_input}

        Information candidates: 
        {state.response}

        Return ONLY the numbers, with comma as separator.
    """

    numbers = llm.invoke(prompt).strip()

    numbers = numbers.replace(" ", "").split(",")

    for number in numbers:
        candidates_info.append(state.retrieved_files[int(number) - 1][1])

    state.update_response(candidates_info)
    state.update_last_action("get_details")
    
    return state



def candidates_description(state: AgentState) -> AgentState:

    page_contents = [content for _, content in state.retrieved_files]

    state.update_last_action("candidates_description")
    state.update_response(page_contents) 

    return state



def get_resume_by_filename(state: AgentState) -> AgentState:

    filename = [file for file, _ in state.retrieved_files]

    state.update_last_action("get_resume_by_filename")
    state.update_response(filename)

    return state


def create_answer(state: AgentState):

    files = []

    if state.last_action == "candidates_description":
        
        prompt = f"""
            Based on the results of the retrieve, write a text with the structure below for each candidate retrieved.
            Return ONLY what I asked if a good format, no other random text.

            Candidates: {state.response}

            Follow the format bellow:

            Here are the best matches based on your description:
            
            Name candidate | phone number | email
            - Create a short and concise text why is a good fit.
            ...
        """

        result = llm.invoke(prompt).strip()

    elif state.last_action == "get_details":

        prompt = f"""
            Create a detailed and structured description of the candidates.
            Try to summarize a bit the text but keep some detail.
            Return ONLY what I asked if a good format, no other random text.

            Candidates: {state.response}

            Follow the format bellow:

            Here is some more information:

            Name candidate
            - Work Experience: Paragraph about work experience
            - Education: Paragraph about educationCan
            - Skills: Paragraph about skills
            - Additional Information: Another short paragraph with some information you think is relevant
            ...
        """

        result = llm.invoke(prompt).strip()

    else:
        files = state.response

        resume_folder = "/static/files/"

        result = "Here are the files:\n" + "\n".join(
            [f"- <a href='{resume_folder}{file}' style='color: white; text-decoration: underline;' download>{file}</a>" for file in files]
        )

    state.update_last_action("create_answer")

    chat_memory.save_context({"question": state.user_input}, {"answer": result})

    return {'user_input': state.user_input, 'response': result, 'related': state.related, 'retrieved_files': state.retrieved_files, 'last_action': state.last_action}



def second_router(state: AgentState):

    return state.last_action