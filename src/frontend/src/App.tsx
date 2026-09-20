import axios from "axios";
import {useEffect, useState} from "react";
import {type single_multiple_choice_question_type, vocabulary_enum} from "./domain.ts";


async function retrieve_exercise(questions: number, vocabulary: vocabulary_enum): Promise<single_multiple_choice_question_type[] | undefined>
{
    try
    {
        const response_ = await axios.get<single_multiple_choice_question_type[]>("http://127.0.0.1:5000/api/dummy");

        return response_.data;
    } catch (error)
    {
        console.log(error);

        return undefined;
    }
}

function SingleMultipleChoiceQuestion()
{
    return <div>SingleMultipleChoiceQuestion</div>;
}

function App()
{
    const [response, setResponse] = useState<string>("");

    useEffect(() =>
    {
        retrieve_exercise(10, vocabulary_enum.ENGLISH).then((response) =>
        {
            setResponse(JSON.stringify(response));
        })
    }, []);
    return <>
        <div>
            {response}
        </div>
    </>;
}

export default App;
