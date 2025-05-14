import os
import socket
import ssl
import base64
import zipfile
import asyncio
import aiofiles 

async def send_command(writer, command, reader, decode=True):
    writer.write(command.encode())
    await writer.drain()
    response = await reader.read(1024)
    if decode:
        return response.decode()
    return response

async def smtp_connect(smtp_server, port):
    context = ssl.create_default_context() # secure sockets layer protocol default settings
    reader, writer = await asyncio.open_connection(
        smtp_server, port, ssl=context
    )
    greeting = await reader.read(1024)
    
    return reader, writer, greeting.decode()

async def smtp_authenticate(reader, writer, sender_address, password):

    response = await send_command(writer, "EHLO localhost\r\n", reader)
    print("Google replied to the EHLO command:\n", response)

    # response is bytes but we decoded,so it is a string containing the SMTP status
    # and a message saying what they want now
    response = await send_command(writer, "AUTH LOGIN\r\n", reader)

    # response is a string without whitespace (whitespace causes b64 encoding errors)
    response = response.strip()
    response_parts = response.split() # response is status code and message
    response = response_parts[1] # dont care about the status code

    # response is the decoded base64 information but in bytes
    response = base64.b64decode(response)

    response = response.decode() # response is finally a readable string
    print("Google replied to the AUTH LOGIN:\n", response)


    # Send sender_address
    encoded_sender_address = base64.b64encode(sender_address.encode())
    response = await send_command(writer, encoded_sender_address.decode() + "\r\n", reader)
    response = response.strip().split()[1]
    response = base64.b64decode(response).decode()
    print("Server replied to my sender_address\n", response)



    # Send password
    encoded_password = base64.b64encode(password.encode())
    response = await send_command(writer, encoded_password.decode() + "\r\n", reader)
    print("Password authentication response:\n", response)
    return response

async def smtp_send_email(
    reader,
    writer,
    sender_address,
    display_name,
    recipient,
    subject,
    message_body,
    attachment_files=None
):
    # Create ZIP if attachments are provided
    zip_filename = None
    if attachment_files:
        zip_filename = await create_zip_file(attachment_files)

    email_content = await create_email(
        sender_address,
        display_name,
        recipient,
        subject,
        message_body,
        zip_filename
    )
    # setup the mail
    response = await send_command(writer, f"MAIL FROM:<{sender_address}>\r\n", reader)
    print("MAIL FROM response:\n", response)
    
    response = await send_command(writer, f"RCPT TO:<{recipient}>\r\n", reader)
    print("RCPT TO response:\n", response)
    
    response = await send_command(writer, "DATA\r\n", reader)
    print("DATA response:\n", response)

    # Send the message 
    email_content += ".\r\n"  # protocol terminator
    response = await send_command(writer, email_content, reader)
    print("Message data response:\n", response)

    await send_command(writer, "QUIT\r\n", reader)
    writer.close()
    await writer.wait_closed()

    if zip_filename:
        os.remove(zip_filename)

async def create_zip_file(attachment_files):
    zip_filename = "attachments.zip"

    try:
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file_path in attachment_files:
                filename = os.path.basename(file_path)
                zipf.write(file_path, filename)
    except Exception as e:
        print(f"Problem creating zip {filename}: {e}")
        return None
    
    return zip_filename

async def create_email(sender_address, display_name, recipient,
                subject, message_body, zip_filename = None):

    boundary = "any boundary"
    if zip_filename:
        try:
            async with aiofiles.open(zip_filename, 'rb') as file:
                file_bytes = await file.read()
                fileb64 = base64.b64encode(file_bytes).decode()

                email = (
                    f"From: \"{display_name}\" <{sender_address}>\r\n"
                    f"To: {recipient}\r\n"
                    f"Subject: {subject}\r\n"
                    f"MIME-Version: 1.0\r\n"
                    f"Content-Type: multipart/mixed; boundary=\"{boundary}\"\r\n"
                    "\r\n"
                    f"--{boundary}\r\n"
                    f"Content-Type: text/plain; charset=\"utf-8\"\r\n"
                    "\r\n"
                    f"{message_body}\r\n"
                    "\r\n"
                    f"--{boundary}\r\n"
                    f"Content-Type: application/zip\r\n"
                    f"Content-Disposition: attachment; filename=\"{zip_filename}\"\r\n"
                    f"Content-Transfer-Encoding: base64\r\n"
                    "\r\n"
                    f"{fileb64}\r\n"
                    "\r\n"
                    f"--{boundary}--\r\n"
                )
        except Exception as e:
            print (f"Error: cannot open file {zip_filename} : {e}")
            return None

    else: # No zip
        email = (
            f"From: \"{display_name}\" <{sender_address}>\r\n"
            f"To: {recipient}\r\n"
            f"Subject: {subject}\r\n"
            f"MIME-Version: 1.0\r\n"
            f"Content-Type: text/plain; charset=\"utf-8\"\r\n"
            "\r\n"
            f"{message_body}\r\n"
        )

    return email
