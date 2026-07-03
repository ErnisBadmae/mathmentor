import os
import sys
from openai import OpenAI

# Настройки из вашего .env
client = OpenAI(
    base_url="http://192.168.0.18:8000/v1",
    api_key="token-abc123"
)
MODEL_NAME = "Qwen3.6-35B-A3B-Q5-256K"

SYSTEM_PROMPT = (
    "Ты — Локальный Исполнитель кода (Executor). Твоя задача — строго выполнять "
    "инструкции из технического плана. Пиши чистый, готовый к продакшену код. "
    "Минимум разговоров, только код и краткие пояснения, где его разместить."
)

def ask_qwen(prompt):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1 # Низкая температура для точной генерации кода
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка подключения к llama.cpp: {e}"

if __name__ == "__main__":
    # Если передали аргумент командной строки (например, python qwen.py "сделай то")
    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
        print(ask_qwen(user_prompt))
    else:
        # Интерактивный режим чата в терминале
        print("🤖 Локальный исполнитель Qwen готов. Введите задачу (или 'exit' для выхода):")
        while True:
            try:
                user_input = input("\nqwen_cli > ")
                if user_input.lower() in ['exit', 'quit']:
                    break
                if not user_input.strip():
                    continue
                
                print("\nThinking...")
                result = ask_qwen(user_input)
                print(f"\n{result}")
            except KeyboardInterrupt:
                break