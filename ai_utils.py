import asyncio
from openai import OpenAI

async def generate_email_body (
        sender: str,
        recipient: str,
        subject: str,
        api_key: str
):
    prompt = (
        f"Write a polite email adressed to {recipient} from {sender}."
        f"The email should be about {subject}. Make it sound important."
        f"remind the user why it is important. Talk like {subject} is"
        f"already in process and make up something that {recipient} has"
        f"already done."
    )
    return await asyncio.to_thread(openai_call, prompt, api_key)

def openai_call(prompt, api_key):
    client = OpenAI(api_key=api_key)

    ai_answer = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": (
                 "You are an expert on all topics."
                 "Write only the email's body—do NOT include any headers or the subject line."
                 )},
            {"role": "user",    "content": prompt},
        ],
        max_tokens=300,
        temperature=0.8
    )
    return ai_answer.choices[0].message.content