import axios from "axios";
import {useEffect, useState} from "react";

function App()
{
  const [response, setResponse] = useState<string>("");

  useEffect( () => {
     axios.get("http://127.0.0.1:5000/api/demo").then((response) => {
      setResponse(JSON.stringify(response.data));
    })
  }, []);
  return <>
    <div>
        {response}
    </div>
  </>;
}

export default App;
