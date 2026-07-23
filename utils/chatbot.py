import os
from google import genai
from google.genai import types

SYSTEM_TEMPLATE = """You are DiaCare AI's Health Assistant, a friendly and careful diabetes-focused
health guide. You are NOT a doctor and must never claim to be one.

Here is the user's most recent prediction result, use it to personalize your answers:
- Predicted risk: {label}
- Confidence: {confidence}%
- BMI: {bmi}
- Blood Glucose Level: {glucose} mg/dL

Rules:
- Keep answers short, practical, and easy to understand.
- Base food/lifestyle suggestions on the user's risk level above.
- If asked something outside diabetes/health/nutrition, politely redirect back to health topics.
- Never diagnose. Always suggest seeing a real doctor for medical decisions.
"""


def ask_health_assistant(user_message, prediction_context):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI Assistant is not configured yet."

    client = genai.Client(api_key=api_key)

    system_prompt = SYSTEM_TEMPLATE.format(
        label=prediction_context.get("label", "Unknown"),
        confidence=prediction_context.get("confidence", "N/A"),
        bmi=prediction_context.get("bmi", "N/A"),
        glucose=prediction_context.get("glucose", "N/A"),
    )

    if not user_message.strip():
        return "Please enter a health-related question."

    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=user_message,
            config=types.GenerateContentConfig(
            system_instruction=system_prompt
        ),
    )
        return response.text.strip()
    except Exception as e:
        print("Gemini Error:", e)
        return (
        "Sorry, the AI Assistant is temporarily unavailable. "
        "Please try again later."
    ) 