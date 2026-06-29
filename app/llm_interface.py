import ollama

# Define standard target JSON schema structure
STUDY_SCHEMA = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["name", "summary"],
            },
        },
        "definitions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "meaning": {"type": "string"},
                },
                "required": ["term", "meaning"],
            },
        },
        "flashcards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["question", "answer"],
            },
        },
    },
    "required": ["concepts", "definitions", "flashcards"],
}


def analyze_transcript(full_text):
    """Communicates with the local Ollama service to map unstructured data to JSON."""
    prompt = f"Analyze the following transcript block and separate it into Core Concepts, Definitions, and Quiz Flashcards: {full_text}"

    # Ollama natively handles structural JSON generation locally on your CPU
    response = ollama.chat(
        model="phi3:mini",
        messages=[{"role": "user", "content": prompt}],
        format=STUDY_SCHEMA,
    )

    return response["message"]["content"]
