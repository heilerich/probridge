import os
import time
import unittest
import xmlrunner
import re
import smtplib
import ssl

from pexpect import spawn as run_cli 
from pexpect.exceptions import TIMEOUT as CliTimeout
from io import StringIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from uuid import uuid1

class TestContainer(unittest.TestCase):
    @classmethod
    def generate_fixtures(cls):
        mid = str(uuid1())
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Test {mid}"
        message["From"] = cls.username
        message["To"] = cls.username
        
        text = f"""
        Test ID {mid} in Text
        """
        html = f"""
        <html><body>
            <p>ID <b>{mid}</b> in HTML<br \></p>
        </body></html>
        """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)

        cls.test_message = message
        
    @classmethod
    def setUpClass(cls):
        cls.image = os.getenv("TEST_IMAGE", "localhost:5000/test/test:latest")
        cls.smtp_port = os.getenv("TEST_SMTP_PORT", "11025")
        cls.imap_port = os.getenv("TEST_IMAP_PORT", "11143")
        cls.container = run_cli(f"docker run -it --rm --name probridge_test -p '{cls.smtp_port}:1025' -p '{cls.imap_port}:1143' {cls.image} -l panic --cli", encoding='utf-8')
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
        regex = r"IMAP\sSettings.*?Password:\s+([^\n]+)\n"
        pw = re.search(regex, output, re.DOTALL).group(0)
        self.__class__.bridge_pw = pw

    def test_04_send_email(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        print(f"127.0.0.1:{int(self.smtp_port)}")

        with smtplib.SMTP("127.0.0.1", int(self.smtp_port), timeout=10) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(self.username, self.bridge_pw)
            server.sendmail(self.username, self.username, self.test_message.as_string())

    def test_05_logout(self):
        self.container.sendline("logout")
        self.container.expect(r"Are you sure you want to logout account (.*):")
        self.container.sendline("yes")
        self.expect_prompt()
        self.container.sendline("info")
        self.assertEqual(self.container.expect("Please login to"), 0)

    def test_06_removal(self):
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

