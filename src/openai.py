from os import environ
from os.path import dirname, sep
from dotenv import load_dotenv


def get_openai_secret_key() -> str:
    load_dotenv(sep.join([str(dirname(__file__)), "..", ".env"]))
    return environ["OPENAI_API_KEY"]



if __name__ == "__main__":
    print(get_openai_secret_key())
