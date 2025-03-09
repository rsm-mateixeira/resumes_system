from django.shortcuts import render
from django.http import JsonResponse
from langgraph.graph import StateGraph
from .functions import check_context, retrieve_request, candidates_description, find_top_5_best_fit, get_details, get_resume_by_filename, create_answer, first_router, second_router
import os
from .functions import AgentState
from dotenv import load_dotenv
import os
from django.conf import settings
from django.shortcuts import render
import json
    
load_dotenv()

graph = StateGraph(AgentState)

graph.add_node("check_context", check_context)
graph.add_node("retrieve_request", retrieve_request)
graph.add_node("candidates_description", candidates_description)
graph.add_node("get_details", get_details)
graph.add_node("find_top_5_best_fit", find_top_5_best_fit)
graph.add_node("get_resume_by_filename", get_resume_by_filename)
graph.add_node("create_answer", create_answer)


graph.set_entry_point("check_context")
graph.add_conditional_edges(
    "check_context", 
    first_router,
    {"New": "find_top_5_best_fit", "Old": "retrieve_request"}
)
graph.add_edge("find_top_5_best_fit", "candidates_description")
graph.add_conditional_edges(
    "retrieve_request", 
    second_router,
    {"get_details": "get_details", "get_resume_by_filename": "get_resume_by_filename"}
)
graph.add_edge("candidates_description", "create_answer")
graph.add_edge("get_resume_by_filename", "create_answer")
graph.add_edge("get_details", "create_answer")
graph.set_finish_point("create_answer")

workflow = graph.compile()

GLOBAL_AGENT_STATE = AgentState()

# Create your views here.
# Home Page View
def home_view(request):
    return render(request, "home.html")



def resumes_page_view(request):

    files_folder = os.path.join(settings.BASE_DIR, 'app', 'static', 'files')

    # List all files in the folder
    if os.path.exists(files_folder):
        resume_files = [
            {
                'name': file, 
                'url': f"/static/files/{file}"  # Generate static file URL
            }
            for file in os.listdir(files_folder)
            if file.endswith('.pdf') or file.endswith('.docx')
        ]
    else:
        resume_files = []

    return render(request, 'resumes_page.html', {'resumes': resume_files})



def chatbot_response(request):

    user_message = request.GET.get("message", "")

    if not user_message:
        return JsonResponse({"error": "No message provided"}, status=400)

    try:

        GLOBAL_AGENT_STATE.update_user_input(user_message)

        # Invoke workflow
        invoke_workflow = workflow.invoke(GLOBAL_AGENT_STATE)

        # Update state with new data using built-in update functions
        GLOBAL_AGENT_STATE.update_retrieved_files(invoke_workflow.get("retrieved_files", []))
        GLOBAL_AGENT_STATE.update_response(invoke_workflow.get("response", ["No response generated."]))
        GLOBAL_AGENT_STATE.update_last_action(invoke_workflow.get("last_action", None))


        return JsonResponse({
            "response": " ".join(GLOBAL_AGENT_STATE.response) if isinstance(GLOBAL_AGENT_STATE.response, list) else GLOBAL_AGENT_STATE.response,
            "retrieved_files": GLOBAL_AGENT_STATE.retrieved_files,
            "last_action": GLOBAL_AGENT_STATE.last_action
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)