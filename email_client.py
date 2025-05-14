import os
import socket
import ssl
import base64
import zipfile

def send_command(ssl_sock, command, decode=True):
    ssl_sock.sendall(command.encode())
    response = ssl_sock.recv(1024)
    if decode:
        return response.decode()
    return response

def smtp_connect(smtp_server, port):
    context = ssl.create_default_context() # secure sockets layer protocol default settings
    sock = socket.create_connection((smtp_server, port))
    ssl_sock = context.wrap_socket(sock, server_hostname=smtp_server)
    return ssl_sock

def smtp_authenticate(ssl_sock, sender_address, password):

    response = send_command(ssl_sock, "EHLO localhost\r\n")
    print("Google replied to the EHLO command:\n", response)

    # response is bytes but we decoded,so it is a string containing the SMTP status
    # and a message saying what they want now
    response = send_command(ssl_sock, "AUTH LOGIN\r\n")

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
    response = send_command(ssl_sock, encoded_sender_address.decode() + "\r\n").strip().split()[1]
    response = base64.b64decode(response).decode()
    print("Google replied to my sender_address\n", response)


    # Send password
    encoded_password = base64.b64encode(password.encode())
    response = send_command(ssl_sock, encoded_password.decode() + "\r\n")
    print("Password authentication response:\n", response)

def smtp_send_email(ssl_sock, sender_address, recipient, message):
    # setup the mail
    response = send_command(ssl_sock, f"MAIL FROM:<{sender_address}>\r\n")
    print("MAIL FROM response:\n", response)

    response = send_command(ssl_sock, f"RCPT TO:<{recipient}>\r\n")
    print("RCPT TO response:\n", response)

    response = send_command(ssl_sock, "DATA\r\n")
    print("DATA response:\n", response)

    # send the message 
    response = send_command(ssl_sock, message, decode=True)
    print("Message data response:\n", response)

def create_zip_file(attachment_files):
    zip_filename = "attachments.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file_path in attachment_files:
            filename = os.path.basename(file_path)
            zipf.write(file_path, filename)
    return zip_filename

def create_email(sender_address, display_name, recipient,
                subject, message_body, zip_filename = None):

    boundary = "any boundary"
    if zip_filename:
        try:
            with open(zip_filename, 'rb') as file:
                file_bytes = file.read()
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
                    ".\r\n"
                )
        except Exception as e:
            print (f"Error: cannot open file {zip_filename} : {e}")
            return None

    else: # No zip
        email = (
        # headers
        f"From: \"{sender_address}\"\r\n"
        f"To: {recipient}\r\n"
        f"Subject: {subject}\r\n"
        "\r\n" # header-body separator
        f"{message_body}\r\n"
        ".\r\n" # end symbol
        ) 
    email += f"--{boundary}--\r\n.\r\n"

    return email
  
        
def smtp_send_email_with_attachments(ssl_sock, sender_address, display_name, recipient, subject, message_body, attachment_files):
    zip_filename = create_zip_file(attachment_files)
    email_content = create_email(sender_address, display_name, recipient, subject, message_body, zip_filename)
    smtp_send_email(ssl_sock, sender_address, recipient, email_content)
    os.remove(zip_filename)

def main():
    # smtp_server = "smtp.gmail.com"
    # port = 465  # SSL port for Gmail SMTP
    # sender_address = ""
    # password = ""
    # recipient = ""
    # subject = ""
    # sender = ""
    # message = "this is my default msg\r\nhere I write something"

    # ready_email = (
    #         # headers
    #         f"From: \"{sender}\"\r\n"
    #         f"To: {recipient}\r\n"W
    #         f"Subject: {subject}\r\n"
    #         "\r\n" # header-body separator
    #         f"{message}\r\n"
    #         ".\r\n") # end symbol

    # with smtp_connect(smtp_server, port) as ssl_sock:
    #     banner = ssl_sock.recv(1024).decode()
    #     print("Server banner:\n", banner)

    #     smtp_authenticate(ssl_sock, sender_address, password)

    #     smtp_send_email(ssl_sock, sender_address, recipient, ready_email)

    #     response = send_command(ssl_sock, "QUIT\r\n")
    #     print("QUIT response:\n", response)
    zip_filename = create_zip_file(attachment_files)
    email = create_email(1, 1, 1, 1, 1)
    print(f"this is the email {email}")

main()