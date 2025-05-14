from fastapi import FastAPI, Form, Request, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import os
import tempfile
import asyncio

# Import our async SMTP functions
import async_smtp_functions

app = FastAPI(title="SMTP Email Client")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_email_form(request: Request):
    return templates.TemplateResponse("email_form.html", {"request": request})

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
    # Save uploaded files temporarily
    attachment_files = []
    if attachments and attachments[0].filename:
        for attachment in attachments:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(attachment.filename)[1]) as temp_file:
                content = await attachment.read()
                temp_file.write(content)
                attachment_files.append(temp_file.name)

    try:
        # Connect to SMTP server
        reader, writer, greeting = await async_smtp_functions.smtp_connect(smtp_server, port)
        print(f"Connected to server: {greeting}")
        
        # Authenticate
        auth_response = await async_smtp_functions.smtp_authenticate(reader, writer, sender_address, password)
        
        # Send email
        send_response = await async_smtp_functions.smtp_send_email(
            reader,
            writer,
            sender_address,
            display_name,
            recipient,
            subject,
            message_body,
            attachment_files
        )
        
        # Close connection gracefully
        await async_smtp_functions.smtp_quit(reader, writer)
        
        # Clean up temporary files
        for file_path in attachment_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                
        return {"status": "success", "message": "Email sent successfully"}
    
    except (ConnectionRefusedError, asyncio.TimeoutError) as e:
        return {"status": "error", "message": f"Connection error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}
    finally:
        # Make sure to clean up temporary files in case of errors
        for file_path in attachment_files:
            if os.path.exists(file_path):
                os.remove(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)