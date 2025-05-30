from myflaskapp.llm.interview_summarizer import (
    parse_transcript, parse_recording, align_transcripts, 
    generate_summary, initial_greeting, 
    generate_revision, parse_additional_context
)
from myflaskapp.llm.chat import get_chat_prompt, stream_response


class Session:

    def __init__(self, name="Untitled", summary="", transcript="", messages=None):
        self.name = name
        self.summary = summary
        self.transcript = transcript
        self.messages = list(messages) if messages else []

    def summarize(self, transcript: str, recording: str, additional_context: list[str] = []):
        assert transcript.lower().endswith(
            ".docx"
        ), "Transcript file must be a .docx file."
        assert recording.lower().endswith(".mp4"), "Recording file must be a .mp4 file."
        assert isinstance(additional_context, list), "Additional context must be a list."
        if additional_context:  # Only check files if list is not empty
            for context_file in additional_context:
                assert context_file.lower().endswith('.pdf'), "Additional context files must be .pdf files."
        
        # parse transcript and recording
        print("Parsing transcript...")
        og_transcript = parse_transcript(transcript)
        print("Transcribing recording...")
        whisper_transcript = parse_recording(recording)

        # align transcripts
        print("Aligning transcripts...")
        aligned_transcript = align_transcripts(og_transcript, whisper_transcript)
        self.transcript = aligned_transcript

        self.messages.append({"role": "system", "content": get_chat_prompt()})
        self.messages.append(
            {"role": "system", "content": aligned_transcript}
        )
        
        # parse additional context
        additional_context_concat = ""
        if additional_context:
            print("Parsing additional context...")
            additional_context_concat = parse_additional_context(additional_context)
            
            # add additional context to chat
            self.messages.append(
                {"role": "system", "content": f"Additional Context: {additional_context_concat}"}
            )
        else:
            self.messages.append(
                {"role": "system", "content": f"No additional context provided."}
            )

        # generate summary
        print("Generating summary...")
        for chunk in generate_summary(aligned_transcript, additional_context_concat):
            # add summary to chat
            self.summary += chunk
            yield chunk

        self.messages.append(
            {"role": "system", "content": f"Initial Summary: {self.summary}"}
        )

        # initial message
        greeting = initial_greeting()
        self.messages.append({"role": "assistant", "content": greeting})

    def prompt_chat(self, prompt: str):
        # add user message to conversation
        self.messages.append({"role": "user", "content": prompt})
        # get response in a streaming manner
        response = ""
        for chunk in stream_response(self.messages):
            # add assistant message to conversation
            response += chunk
            yield chunk
        # add final response to conversation
        self.messages.append({"role": "assistant", "content": response})

    def revise(self, request: str):
        # initial system prompt, transcript, additional context, and summary
        system_messages = self.messages[:4]
        # most recent summary
        system_messages.append(
            {"role": "system", "content": f"Most Recent Summary: {self.summary}"}
        )
        # revision system prompt
        system_messages.append(
            {
                "role": "system",
                "content": """Your task is to revise an interview summary based on the user's request and the most recent summary. 

                You have access to:
                1. The original summary guidelines (use these as a reference for the structure and tone of the summary)
                2. The complete transcript of the interview (use this to add new content to the summary and follow the timestamps, DO NOT HALLUCINATE TIMES)
                3. The original version of the summary
                4. The most recent version of the summary
                5. The user's specific revision request

                Guidelines for revision:
                - Always begin with the title "# Interview with [interviewee's name]" as heading level 1
                - Use heading level 2 (##) for all section headers within the summary
                - CRITICAL: Preserve all timestamp citations (e.g., [00:15:30]) regardless of revision requests - these references are essential for locating information in the original interview
                - Include timestamps for all key statements, quotes, and important points
                - If adding new content from the transcript, always include the corresponding timestamp
                - Format the entire summary using proper markdown syntax
                - Maintain the professional tone and factual accuracy of the original
                - Implement the user's requested changes while ensuring the summary remains coherent and comprehensive
                - Focus on capturing the most important information from the interview
                - Organize content logically with clear section breaks
                - Make sure the summary remains an accurate reflection of the interview content

                Do not include any leading text, explanatory notes, or metadata. Provide only the revised summary starting with the title.
                """,
            }
        )

        # revision request
        system_messages.append(
            {
                "role": "user",
                "content": f"Can you make these revisions to the summary: {request}",
            }
        )
        self.summary = ""
        for chunk in generate_revision(system_messages):
            # add revision to chat
            self.summary += chunk
            yield chunk
