from myflaskapp.llm.llm_clients import gpt4o_client

def get_chat_prompt():
    """Return the system prompt for the chat."""
    return """
    You are an expert assistant designed to help investigators analyze and query the contents of an interview. 
    You have access to the full transcript of the interview as well as a summary of the interview. 
    Your role is to assist investigators by answering their questions based on the provided information. 
    If investigators request, you can refine the summary to highlight the most relevant and important details, 
    always referring to the most recent version of the interview's summary. Be professional, no emojis.
    """

def stream_response(messages):
    """Stream the response from the chat model."""
    response = gpt4o_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        stream=True,
    )
    for chunk in response:
        if not chunk or not hasattr(chunk, "choices") or len(chunk.choices) == 0:
            continue  # skip invalid or empty chunk

        delta = getattr(chunk.choices[0].delta, "content", "") or ""
        yield delta
