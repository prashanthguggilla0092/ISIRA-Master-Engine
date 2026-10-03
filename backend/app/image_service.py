from vertexai.generative_models import Content, Part

from .gemini_service import model


def analyze_image(
    image_bytes: bytes,
    mime_type: str,
    prompt: str = "Analyze this image and describe the important details clearly.",
    history: list[dict] | None = None,
    project_context: str = "",
) -> str:
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

    image_part = Part.from_data(
        data=image_bytes,
        mime_type=mime_type,
    )

    full_prompt = prompt

    if project_context:
        full_prompt = (
            f"Project Context:\n{project_context}\n\n"
            f"User Request:\n{prompt}"
        )

    contents.append(
        Content(
            role="user",
            parts=[image_part, Part.from_text(full_prompt)],
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
