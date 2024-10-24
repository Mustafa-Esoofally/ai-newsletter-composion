from typing import Literal, Annotated, Sequence, TypedDict
import operator
import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from composio_langgraph import Action, ComposioToolSet

# Load environment variables
load_dotenv()

# Initialize the model
llm = ChatGroq(model="llama-3.1-70b-versatile")

# Initialize the ComposioToolSet
composio_toolset = ComposioToolSet()

# Get the tools from the ComposioToolSet
gmail_tools = composio_toolset.get_tools(
    actions=[Action.GMAIL_SEND_EMAIL, Action.GMAIL_FETCH_EMAILS],
)

tavily_tool = composio_toolset.get_tools(
    actions=[Action.TAVILY_TAVILY_SEARCH],
)

tools = [*gmail_tools, *tavily_tool]

# Define Tool Node
tool_node = ToolNode(tools)

# Define state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sender: str

def create_agent(llm, tools, system_message: str):
    """Create an agent."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_message,
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    return prompt | llm.bind_tools(tools)

def create_agent_node(agent, name):
    def agent_node(state):
        result = agent.invoke(state)
        if not isinstance(result, ToolMessage):
            result = AIMessage(**result.dict(exclude={"type", "name"}), name=name)
        return {"messages": [result], "sender": name}
    return agent_node

# Create agents
email_fetcher_agent = create_agent(
    llm,
    gmail_tools,
    system_message=f"You are an expert at retrieving and organizing email content, with a keen eye for identifying newsletters. Your goal is to Fetch recent newsletter emails from the inbox. Please look for emails with the words 'newsletter' or 'digest' only for last 7 days. Today's date is {datetime.now().strftime('%B %d, %Y')}. Don't add any other unncessary filters. Pass these emails to email_summarizer_agent."
)

email_fetcher_node = create_agent_node(email_fetcher_agent, "email_fetcher")

email_summarizer_agent = create_agent(
    llm,
    tavily_tool,
    system_message="You are an expert in analyzing and summarizing complex information, with a talent for distilling essential points from various sources. Summarize the content of the fetched newsletter emails, highlighting key information and trends. Create a concise yet comprehensive summary highlighting the key points from each newsletter. Use tavily_tool to search for relevant information and include it in the summary if not already included. This summary will be used by email_sender."
)

email_summarizer_node = create_agent_node(email_summarizer_agent, "email_summarizer")

email_sender_agent = create_agent(
    llm,
    gmail_tools,
    system_message=f"""
        "You are an expert in composing and sending emails with well-formatted, visually appealing content. You have a knack for creating engaging subject lines and structuring information for easy readability. Send the summarized newsletter content using the Gmail API to {os.getenv('TARGET_EMAIL')} with a professional and engaging format."
        "Use the following structure for the email:\n\n"
        "Subject: Your Weekly News Digest - {datetime.now().strftime('%B %d, %Y')}\n\n"
        "<h1>Weekly News Digest</h1>\n\n"
        "<p>Dear Reader,</p>\n\n"
        "<p>Here's your curated summary of this week's top news items and insights:</p>\n\n"
        "[Insert summarized content here]\n\n"
        "Each main section should be separated by a horizontal rule, like this:\n"
        "<hr>\n\n"
        "Structure the content logically, with clear sections for each summarized newsletter or topic area.\n"
        "Use appropriate HTML formatting such as <strong> for headlines, "
        "<ul> and <li> for bullet points, and <br> for line breaks to enhance readability.\n\n"
        "Include a brief introduction at the beginning to set the context and a conclusion at the end "
        "to summarize the key takeaways and trends observed across the newsletters.\n\n"
        "<footer>\n"
        "<p>For more details on these stories, click on the provided links or stay tuned to our next update. "
        "<p>Best regards,<br>Your Newsletter Summary Team</p>\n"
        "</footer>\n\n"
        "Important: Ensure all HTML tags are properly closed and nested correctly."
    """
)

email_sender_node = create_agent_node(email_sender_agent, "email_sender")

def router(state) -> Literal["call_tool", "__end__", "continue"]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "call_tool"
    if "FINAL ANSWER" in last_message.content:
        return "__end__"
    return "continue"

def main():
    # Define the Graph
    workflow = StateGraph(AgentState)

    workflow.add_node("email_fetcher", email_fetcher_node)
    workflow.add_node("email_summarizer", email_summarizer_node)
    workflow.add_node("email_sender", email_sender_node)
    workflow.add_node("call_tool", tool_node)

    workflow.add_edge(START, "email_fetcher")
    workflow.add_edge("email_sender", END)

    workflow.add_conditional_edges(
        "email_fetcher",
        router,
        {"continue": "email_summarizer", "call_tool": "call_tool"},
    )
    workflow.add_conditional_edges(
        "email_summarizer",
        router,
        {"continue": "email_sender", "call_tool": "call_tool"},
    )

    workflow.add_conditional_edges(
        "email_sender",
        router,
        {"continue": END, "call_tool": "call_tool"},
    )

    workflow.add_conditional_edges(
        "call_tool",
        lambda x: x["sender"],
        {
            "email_fetcher": "email_fetcher",
            "email_summarizer": "email_summarizer",
            "email_sender": "email_sender",
        },
    )

    app = workflow.compile()

    # Invoke the graph!
    events = app.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Please begin."
                )
            ],
        },
    )

    print(events)

if __name__ == "__main__":
    main()
