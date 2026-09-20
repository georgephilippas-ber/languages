from src.launcher import launch_console
from src.openai_integration import openai_construct_exercise

if __name__ == "__main__":
    print(launch_console(openai_construct_exercise(questions_number=3)) * 100)
    print("Hello World!")
