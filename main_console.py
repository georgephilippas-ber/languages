from src.domain import Vocabulary, CEFRLevel
from src.launcher import launch_console
from src.openai_integration import openai_construct_exercise

if __name__ == "__main__":
    print(launch_console(openai_construct_exercise(questions_number=2, vocabulary_=Vocabulary.GERMAN, cefr_level_=CEFRLevel.C1)) * 100)
