import axios from "axios";

export type SingleMultipleChoiceQuestion = {
    question: string;
    choices: string[];
    correct_choice: number; // zero-based index into choices
    english_translation: string;
};

export enum Vocabulary
{
    ENGLISH = "ENGLISH",
    GERMAN = "GERMAN",
    FRENCH = "FRENCH",
}
