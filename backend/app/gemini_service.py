import os
import vertexai
from vertexai.generative_models import GenerativeModel, Content, Part
from .system_prompt import ISIRA_SYSTEM_PROMPT

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "prashanth-genai-practice-2026")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
)

model = GenerativeModel("gemini-2.5-flash", system_instruction=ISIRA_SYSTEM_PROMPT)


def generate_response(message: str, history: list[dict] | None = None) -> str:
    contents = []

    if history:
        for item in history:
            role = item.get("role", "user")
            content = item.get("content", "")

            if content:
                contents.append(
                    Content(
                        role="user" if role == "user" else "model",
                        parts=[Part.from_text(content)],
                    )
                )

    contents.append(
        Content(
            role="user",
            parts=[Part.from_text(message)],
        )
    )

    response = model.generate_content(
        contents,
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.7,
        },
    )

    return response.text
