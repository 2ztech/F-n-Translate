import requests
import json

if __name__ == "__main__":
    number_of_questions = 3
    question_number = 0
    
    while question_number < number_of_questions:
        question = str(input("Question: "))
        data = {
            "model": "deepseek-llm:7b",
            "messages": [{"role":"user","content":question}],
            "stream": False
        }
        url = "http://localhost:11434/api/chat"
        response = requests.post(url,json=data)
        
        response_json = json.loads(response.text)
        
        ai_reply = response_json["message"]["content"]
        print(ai_reply)
        question_number += 1