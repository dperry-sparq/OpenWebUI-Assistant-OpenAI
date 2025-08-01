import openai
import os
import time
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        OPENAI_API_KEY: str = Field(default="")
        ASSISTANT_ID: str = Field(default="")
        ASSISTANT_NAME: str = Field(default="")

    def __init__(self):
        self.type = "manifold"
        self.id = "openai"
        self.name = "openai/"
        self.valves = self.Valves(
            **{
                "OPENAI_API_KEY": os.getenv("SS_OPENAI_API_KEY", "api_key"),
                "ASSISTANT_ID": os.getenv("SS_ASSISTANT_ID", "assistant_id"),
                "ASSISTANT_NAME": os.getenv("SS_ASSISTANT_NAME", "assistant_name"),
            }
        )
        if not self.valves.OPENAI_API_KEY:
            raise ValueError(
                "API Key is required. Set SS_OPENAI_API_KEY as an environment variable."
            )
        openai.api_key = self.valves.OPENAI_API_KEY

        if not self.valves.ASSISTANT_ID:
            raise ValueError(
                "Assistant ID is required. Set SS_ASSISTANT_ID as an environment variable."
            )
        self.assistant_id = self.valves.ASSISTANT_ID

        if not self.valves.ASSISTANT_NAME:
            raise ValueError(
                "Assistant Name is required. Set SS_ASSISTANT_NAME as an environment variable."
            )
        self.assistant_name = self.valves.ASSISTANT_NAME

    def pipes(self) -> List[dict]:
        return [
            {
                "id": self.assistant_id,
                "name": (
                    "Custom Assistant"
                    if self.assistant_name is None
                    else self.assistant_name
                ),
            }
        ]

    def process_messages(self, messages: List[dict]) -> List[dict]:
        """Process a list of messages and format them for OpenAI API."""
        processed_messages = []
        for message in messages:
            if isinstance(message.get("content"), list):
                processed_content = [
                    {"type": item["type"], "text": item["text"]}
                    for item in message["content"]
                    if item["type"] == "text"
                ]
                processed_messages.append(
                    {"role": message["role"], "content": processed_content}
                )
            else:
                processed_messages.append(
                    {
                        "role": message["role"],
                        "content": [
                            {"type": "text", "text": message.get("content", "")}
                        ],
                    }
                )
        return processed_messages

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        """Process the request body and interact with the assistant."""
        processed_messages = self.process_messages(body["messages"])

        # Create a conversation thread
        thread = openai.beta.threads.create()
        thread_id = thread.id

        # Add messages to the thread
        for message in processed_messages:
            openai.beta.threads.messages.create(
                thread_id=thread_id,
                role=message["role"],
                content=message["content"][0]["text"],
            )

        # Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=self.assistant_id
        )

        # Check the status of the run
        status = run.status
        while status != "completed":
            time.sleep(0.5)
            status = openai.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run.id
            ).status

        # Get the assistant's response
        response = openai.beta.threads.messages.list(thread_id=thread_id)
        assistant_reply = ""
        for message in response.data:
            if message.role == "assistant":
                assistant_reply = message.content[0].text.value
                break

        return assistant_reply

    def non_stream_response(self, body):
        try:
            return self.pipe(body)
        except Exception as e:
            print(f"Error in non_stream_response: {e}")
            return f"Error: {e}"


if __name__ == "__main__":
    pipe = Pipe()
    print(pipe.pipes())
