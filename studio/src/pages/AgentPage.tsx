import { useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function AgentPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input) return;
    const msg: Message = { role: "user", content: input };
    setMessages((m) => [...m, msg]);
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });
      const json = await res.json();
      const reply: Message = { role: "assistant", content: json.reply };
      setMessages((m) => [...m, reply]);
    } finally {
      setLoading(false);
      setInput("");
    }
  };

  return (
    <div className="space-y-2">
      <div className="border p-2 h-64 overflow-y-auto">
        {messages.map((m, idx) => (
          <div key={idx} className={m.role === "user" ? "text-right" : "text-left"}>
            <span className="font-bold mr-2">{m.role === "user" ? "You" : "AI"}</span>
            <span>{m.content}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="border flex-1 p-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage} disabled={loading} className="bg-blue-500 text-white px-4 py-2 rounded">
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
