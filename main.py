from flask import Flask, request

from src.domain import Vocabulary
from src.launcher import launch_console
from src.openai_integration import openai_construct_exercise

flask_application_ = Flask(__name__)


@flask_application_.get("/api/hello")
def hello():
    count = request.args.get("count", default=1, type=int)

    return {"message": f"Hello from Flask! {count}"}


if __name__ == "__main__":
    print(launch_console(openai_construct_exercise(10, vocabulary_=Vocabulary.FRENCH)))

    flask_application_.run(host="127.0.0.1", port=5000)
