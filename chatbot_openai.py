from openai import OpenAI
from rich.console import Console
import os

console = Console()

# Create one global client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")  # or just OpenAI() if env var is set
)


class OpenAIChatbot:
    def __init__(self, name: str = "MilliBot", model: str = "gpt-4o-mini"):
        self.name = name
        self.model = model
        # store (user_message, bot_reply) pairs
        self.history: list[tuple[str, str]] = []

    def build_messages(self, user_message: str):
        """
        Turn our history into the messages list that Chat Completions needs.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are {self.name}, a friendly helpful assistant. "
                    "Be concise by default and explain things clearly."
                ),
            }
        ]

        # keep the last 10 turns of context
        for user, bot in self.history[-10:]:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": bot})

        # current user message
        messages.append({"role": "user", "content": user_message})
        return messages

    def generate_reply(self, user_message: str) -> str:
        """
        Call the OpenAI Chat Completions API and return the model's reply.
        """
        messages = self.build_messages(user_message)

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=messages,  # list of {role, content}
                temperature=0.7,
            )

            reply = completion.choices[0].message.content
            if reply is None:
                reply = "(Model returned an empty message 🤔)"

        except Exception as e:
            # if something goes wrong (bad key, network, etc.)
            reply = f"(Error talking to OpenAI API: {e})"

        return reply

    def chat_loop(self):
        console.print(
            f"[bold green]{self.name} (OpenAI) ready![/bold green] "
            "Type 'quit' or 'exit' to stop.\n"
        )

        while True:
            user_message = input("You: ").strip()
            if user_message.lower() in {"quit", "exit"}:
                console.print("[bold green]Chat ended. Goodbye![/bold green]")
                break

            reply = self.generate_reply(user_message)
            self.history.append((user_message, reply))

            console.print(f"[bold cyan]{self.name}:[/bold cyan] {reply}")


if __name__ == "__main__":
    bot = OpenAIChatbot(
        name="MilliBot",
        model="gpt-4o-mini",  # you can swap to 'gpt-4o' etc. later
    )
    bot.chat_loop()
