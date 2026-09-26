import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (
    event: React.SyntheticEvent<HTMLFormElement, SubmitEvent>
  ) => {
    event.preventDefault();

    const message = input.trim();

    if (!message || isLoading) {
      return;
    }

    setInput("");
    setIsLoading(true);

    const userMessage: Message = {
      role: "user",
      content: message,
    };

    setMessages((current) => [
      ...current,
      userMessage,
      {
        role: "assistant",
        content: "",
      },
    ]);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/chat/stream",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            conversation_id: "web-user",
            message,
          }),
        }
      );
      if (!response.ok) {
        throw new Error(
          `Request failed: ${response.status}`
        );
      }
      if (!response.body) {
        throw new Error(
          "Streaming response is unavailable."
        );
      }
      // const data = await response.json();
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(
          value,
          { stream: true }
        );

        console.log(chunk);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main>
      <h1>AI Employee Assistant</h1>

      <div>
        {messages.map((message, index) => (
          <div key={index}>
            <strong>
              {message.role === "user" ? "You" : "AI"}
            </strong>

            <p>{message.content}</p>
          </div>
        ))}
      </div>

      <form onSubmit={sendMessage}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask something..."
          disabled={isLoading}
        />

        <button disabled={isLoading}>
          {isLoading ? "Thinking..." : "Send"}
        </button>
      </form>
    </main>
  );
}

export default App;