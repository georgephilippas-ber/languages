from json import loads

from flask import Flask, request

from src.domain import Vocabulary
from src.openai_integration import openai_construct_exercise

flask_application_ = Flask(__name__)

demo_response_: str = """
[
  {
    "choices": [
      "untergraben",
      "jemanden ertragen",
      "die Bergung",
      "versorgen"
    ],
    "correct_choice": 2,
    "english_translation": "Despite adverse weather conditions, the operations command did everything possible to enable the recovery of the buried vehicle.",
    "question": "Die Einsatzleitung setzte trotz widriger Wetterbedingungen alles daran, _____ des verschütteten Fahrzeugs zu ermöglichen."
  },
  {
    "choices": [
      "gerissen vorgehen",
      "eine taktische Kehrtwende vollziehen",
      "sich wappnen",
      "einen Schritt voraus sein"
    ],
    "correct_choice": 2,
    "english_translation": "In order not to be caught off guard in the upcoming negotiations, the union representatives had to brace themselves and carefully coordinate their arguments.",
    "question": "Um in den anstehenden Verhandlungen nicht überrumpelt zu werden, mussten die Gewerkschaftsvertreter _____ und ihre Argumente sorgfältig aufeinander abstimmen."
  },
  {
    "choices": [
      "beharren",
      "jemanden ausfindig machen",
      "beurteilen",
      "gewaltig"
    ],
    "correct_choice": 2,
    "english_translation": "In order to be able to assess the applications fairly and transparently despite incomplete information, the committee established additional criteria.",
    "question": "Um die Bewerbungen trotz unvollständiger Angaben fair und nachvollziehbar _____ zu können, legte das Gremium zusätzliche Kriterien fest."
  },
  {
    "choices": [
      "der Neid",
      "anfällig für",
      "überlegen",
      "das Äußere / nach seinem Äußeren"
    ],
    "correct_choice": 2,
    "english_translation": "Although both models cost a similar amount, this one is clearly superior to its predecessor in terms of energy efficiency.",
    "question": "Obwohl beide Modelle ähnlich viel kosten, ist dieses seinem Vorgänger hinsichtlich der Energieeffizienz deutlich _____."
  },
  {
    "choices": [
      "die Verwirrung",
      "der Sog",
      "Wir neigen dazu",
      "jemanden ausfindig machen"
    ],
    "correct_choice": 2,
    "english_translation": "We tend to portray hasty decisions as unavoidable, although careful consideration would often bring better solutions to light.",
    "question": "_____ , vorschnelle Entscheidungen als alternativlos darzustellen, obwohl eine sorgfältige Prüfung oft bessere Lösungen zutage fördern würde."
  }
]
"""

@flask_application_.get("/api/demo")
def demo():
    return loads(demo_response_)

@flask_application_.get("/api/multiple_choice")
def multiple_choice():
    questions_: int = request.args.get("questions", default=5, type=int)
    vocabulary_: Vocabulary = request.args.get("vocabulary", default=Vocabulary.GERMAN, type=lambda value: Vocabulary[value.strip().upper()])

    return openai_construct_exercise(questions_, vocabulary_=vocabulary_)


if __name__ == "__main__":
    flask_application_.run(host="127.0.0.1", port=5_000)
