from flask import Flask, request
from flask_cors import CORS

from src.domain import Vocabulary
from src.openai_integration import openai_construct_exercise

flask_application_ = Flask(__name__)
CORS(flask_application_, origins=["http://localhost:5173"])


@flask_application_.get("/api/multiple_choice")
def multiple_choice():
    questions_: int = request.args.get("questions", default=5, type=int)
    vocabulary_: Vocabulary = request.args.get("vocabulary", default=Vocabulary.GERMAN,
                                               type=lambda value: Vocabulary[value.strip().upper()])

    return openai_construct_exercise(questions_, vocabulary_=vocabulary_)


if __name__ == "__main__":
    flask_application_.run(host="127.0.0.1", port=5_000, debug=True)
