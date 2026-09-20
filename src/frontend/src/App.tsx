import axios from "axios";
import {useEffect, useState} from "react";
import {type SingleMultipleChoiceQuestion, Vocabulary} from "./domain.ts";


async function retrieve_exercise(questions: number, vocabulary: Vocabulary): Promise<SingleMultipleChoiceQuestion[] | undefined>
{
    try
    {
        const response_ = await axios.get<SingleMultipleChoiceQuestion[]>("http://127.0.0.1:5000/api/dummy");

        return response_.data;
    } catch (error)
    {
        console.log(error);

        return undefined;
    }
}


function App()
{
    const [response, setResponse] = useState<string>("");

    useEffect(() =>
    {
        retrieve_exercise(10, Vocabulary.ENGLISH).then((response) =>
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
