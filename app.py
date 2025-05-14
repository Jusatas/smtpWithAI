from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from typing import List
import os
import tempfile

import smtp_functions

app = FastAPI()

HTML_FORM = """
<!doctype html>
<title>Send Email</title>
<h1>Send Email</h1>
<form action="/send-email" method="post" enctype="multipart/form-data">
  <label>SMTP Server:<br><input name="smtp_server" value="smtp.gmail.com"></label><br><br>
  <label>Port:<br><input name="port" value="465"></label><br><br>
  <label>Your Email:<br><input name="sender_address"></label><br><br>
  <label>Your Name:<br><input name="display_name"></label><br><br>
  <label>App Password:<br><input name="password" type="password"></label><br><br>
  <label>To:<br><input name="recipient"></label><br><br>
  <label>Subject:<br><input name="subject"></label><br><br>
  <label>Message:<br><textarea name="message_body" rows="5" cols="40"></textarea></label><br><br>
  <label>Attachments:<br><input type="file" name="attachments" multiple></label><br><br>
  <button type="submit">Send</button>
</form>
"""

@app.get("/", response_class=HTMLResponse)
async def form():
    return HTML_FORM

@app.post("/send-email")
async def send_email(
    sender_address: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    recipient: str = Form(...),
    subject: str = Form(...),
    message_body: str = Form(...),
    smtp_server: str = Form("smtp.gmail.com"),
    port: int = Form(465),
    attachments: List[UploadFile] = File(None)
):
    # Save uploaded files if they were actually selected
    # FastAPI give empty objects even if no files were selected
    # So they need to be "filtered out"
    attachment_files = []
    if attachments:
        for file in attachments:
            if file.filename:  # Only handle files that have a name
                suffix = os.path.splitext(file.filename)[1]
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                content = await file.read()
                temp.write(content)
                temp.close()
                attachment_files.append(temp.name)

    try:
        reader, writer, greeting = await smtp_functions.smtp_connect(smtp_server, port)
        await smtp_functions.smtp_authenticate(reader, writer, sender_address, password)
        await smtp_functions.smtp_send_email(
            reader,
            writer,
            sender_address,
            display_name,
            recipient,
            subject,
            message_body,
            attachment_files if attachment_files else None  # Send None if empty
        )
        await smtp_functions.smtp_quit(reader, writer)

        return {"status": "success", "message": "Email sent successfully"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    finally:
        # Clean up
        for file_path in attachment_files:
            if os.path.exists(file_path):
                os.remove(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
