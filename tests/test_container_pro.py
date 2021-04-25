import os
import time
import unittest
import xmlrunner
import re
import smtplib
import imaplib
import ssl

from timeout_decorator import timeout
from pexpect import spawn as run_cli 
from pexpect.exceptions import TIMEOUT as CliTimeout
from io import StringIO
from email import message_from_bytes
from email.policy import SMTP as email_policy
from email.headerregistry import Address
from email.message import EmailMessage
from uuid import uuid1
from textwrap import dedent

class TestContainer(unittest.TestCase):
    @classmethod
    def generate_fixtures(cls):
        mid = str(uuid1())
        user, domain = cls.username.split("@")
        addr = Address("CI Bot", user, domain)
        message = EmailMessage(policy=email_policy)
        message["Subject"] = f"Test {mid}"
        message["From"] = addr
        message["To"] = addr
        
        message.set_content(dedent(f"""\
        Test ID {mid} in Text
        """))
        cls.test_message = message
        
    @classmethod
    def setUpClass(cls):
        cls.image = os.getenv("TEST_IMAGE", "localhost:5000/test/test:latest")
        cls.smtp_port = os.getenv("TEST_SMTP_PORT", "11025")
        cls.imap_port = os.getenv("TEST_IMAP_PORT", "11143")
        cls.container = run_cli(f"docker run -it --rm --name probridge_test -p '{cls.smtp_port}:1025' -p '{cls.imap_port}:1143' {cls.image} -l debug --cli", encoding='utf-8')
        cls.container.timeout = os.getenv("TEST_TIMEOUT", 30)
        cls.container.logfile_read = StringIO()
        cls.username = os.environ["TEST_USER"]
        cls.password = os.environ["TEST_USER_PW"]
        cls.generate_fixtures()

    @classmethod
    def tearDownClass(cls):
        cls.container.sendline("exit") 
        retry = 0
        while cls.container.isalive() and retry <= 5:
            time.sleep(1)
            retry += 1

        cls.container.terminate(force=True)

    def expect_prompt(self):
        self.container.expect(">>>")

    def assertIMAP(self, ret):
        status, data = ret
        self.assertEqual(status, "OK")
        return data

    def setUp(self):
        self.container.sendline(" ")
        self.expect_prompt()

    def test_01_connection(self):
        self.container.sendline("check connection")
        self.assertEqual(self.container.expect("Internet connection is available."), 0)

    def test_02_login(self):
        self.container.sendline("login")
        self.container.expect("Username: ")
        self.container.sendline(self.username)
        self.container.expect("Password: ")
        self.container.waitnoecho()
        self.container.sendline(self.password)
        self.container.expect(r"Account (.*) was added successfully\.")

    def test_03_getting_credentials(self):
        self.container.sendline("info")
        self.container.expect("IMAP Settings")
        output = self.container.logfile_read.getvalue()
        regex = r"IMAP\sSettings.*?Password:\s+([^\n^\r]+)[\r\n]"
        pw = re.search(regex, output, re.DOTALL).group(1)
        self.__class__.bridge_pw = pw

    def test_11_send_email(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP_SSL("127.0.0.1", int(self.smtp_port), timeout=10, context=context) as server:
            server.ehlo()
            server.login(self.username, self.bridge_pw)
            server.send_message(self.test_message)

    @timeout(15)
    def test_12_check_inbox(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with imaplib.IMAP4("127.0.0.1", int(self.imap_port)) as server:
            self.assertIMAP(server.starttls(context))
            self.assertIMAP(server.login(self.username, self.bridge_pw))
            self.assertIMAP(server.select(mailbox="INBOX"))
            found = False
            while not found:
                msgnums = self.assertIMAP(server.search(None, "ALL"))
                for num in msgnums[0].split():
                    data = self.assertIMAP(server.fetch(num, "(RFC822)"))[0][1]
                    msg = message_from_bytes(data, policy=email_policy)
                    if msg['Subject'] == self.test_message['Subject']:
                        recv_body = msg.get_content().replace('\r', '').replace('\n', '')
                        send_body = self.test_message.get_content().replace('\r', '').replace('\n', '')
                        self.assertEqual(recv_body, send_body)
                        found = True
                        break
                time.sleep(0.1)
            self.assertIMAP(server._simple_command('MOVE', num, 'Archive'))

    @timeout(15)
    def test_13_check_archive(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with imaplib.IMAP4("127.0.0.1", int(self.imap_port)) as server:
            self.assertIMAP(server.starttls(context))
            self.assertIMAP(server.login(self.username, self.bridge_pw))
            self.assertIMAP(server.select(mailbox="Archive"))
            found = False
            while not found:
                msgnums = self.assertIMAP(server.search(None, "ALL"))
                for num in msgnums[0].split():
                    data = self.assertIMAP(server.fetch(num, "(RFC822)"))[0][1]
                    msg = message_from_bytes(data, policy=email_policy)
                    if msg['Subject'] == self.test_message['Subject']:
                        recv_body = msg.get_content().replace('\r', '').replace('\n', '')
                        send_body = self.test_message.get_content().replace('\r', '').replace('\n', '')
                        self.assertEqual(recv_body, send_body)
                        found = True
                        break
                time.sleep(0.1)
            self.assertIMAP(server.store(num, '+FLAGS', '\\Deleted'))

    def test_21_logout(self):
        self.container.sendline("logout")
        self.container.expect(r"Are you sure you want to logout account (.*):")
        self.container.sendline("yes")
        self.expect_prompt()
        self.container.sendline("info")
        self.assertEqual(self.container.expect("Please login to"), 0)

    def test_22_removal(self):
        self.container.sendline("rm 0")
        self.container.expect(r"Are you sure you want (.*):")
        self.container.sendline("yes")
        self.container.expect(r"Do you want to remove cache for this (.*):")
        self.container.sendline("yes")
        self.expect_prompt()
        self.container.sendline("info")
        self.assertEqual(self.container.expect("No active accounts."), 0)


if __name__ == '__main__':
    output_dir = os.getenv("TEST_OUTPUT", "/tmp/build/junit-reports")
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(output=output_dir),
        failfast=False, buffer=False, catchbreak=False
    )

