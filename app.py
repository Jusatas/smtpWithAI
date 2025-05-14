from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from fastapi import Response
from typing import List
import os
import tempfile

import smtp_functions
from ai_utils import generate_email_body

app = FastAPI()

HTML_FORM = """
<!doctype html>
<title>Send Email</title>
<h1>Send Email</h1>
<form action="/send-email" method="post" enctype="multipart/form-data">
  <!-- SMTP settings + credentials -->
  SMTP Server: <input name="smtp_server" value="smtp.gmail.com"><br>
  Port:        <input name="port" value="465"><br><br>

  Your Email:  <input name="sender_address"><br>
  Your Name:   <input name="display_name"><br>
  App Password:<input name="password" type="password"><br><br>

  To:      <input name="recipient"><br>
  Subject: <input name="subject"><br><br>

  <!-- AI checkbox -->
  <label>
    <input type="checkbox" id="use_ai" name="use_ai" onclick="toggleFields(this)">
    Let AI write my mail
  </label><br><br>

  <!-- OpenAI key, hidden by default -->
  <div id="ai_key_div" style="display:none;">
    OpenAI API Key:<br>
    <input id="ai_key" name="openai_api_key" type="password"><br><br>
  </div>

  <!-- Message body -->
  Message:<br>
  <textarea id="body" name="message_body" rows="5" cols="40"></textarea><br><br>

  <!-- Attachments -->
  Attachments: <input type="file" name="attachments" multiple><br><br>

  <button type="submit">Send</button>
</form>

<script>
function toggleFields(cb) {
  // Show/hide the API key field
  document.getElementById("ai_key_div").style.display = cb.checked ? "block" : "none";
  // Disable/enable the message textarea
  document.getElementById("body").disabled = cb.checked;
}
</script>
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
    message_body: str = Form(""),
    smtp_server: str = Form("smtp.gmail.com"),
    port: int = Form(465),
    use_ai: bool = Form(False),
    openai_api_key: str = Form(""), 
    attachments: List[UploadFile] = File(None)
):
    
    if use_ai:
        if not openai_api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key is required when using AI.")
        # Generate the body based on headers
        message_body = await generate_email_body(
            sender=f"{display_name}",
            recipient=recipient,
            subject=subject,
            api_key=openai_api_key
        )

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

        return Response(status_code=204)
    
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
