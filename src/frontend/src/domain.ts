export type single_multiple_choice_question_type = {
    question: string;
    choices: string[];
    correct_choice: number; // zero-based index into choices
    english_translation: string;
};

export enum vocabulary_enum
{
    ENGLISH = "ENGLISH",
    GERMAN = "GERMAN",
    FRENCH = "FRENCH",
}
