from src.domain import Vocabulary
from src.launcher import launch_console
from src.openai_integration import openai_construct_exercise

if __name__ == "__main__":
    print(launch_console(openai_construct_exercise(questions_number=10, vocabulary_=Vocabulary.GERMAN)) * 100)
