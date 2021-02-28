import os
import time
import unittest
import xmlrunner
from pexpect import spawn as run_cli 
from pexpect.exceptions import TIMEOUT as CliTimeout

class TestContainer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = os.getenv("TEST_IMAGE", "localhost:5000/test/test:latest")
        cls.container = run_cli(f"docker run -it --rm --name probridge_test -p '1025:1025' -p '1143:1143' {cls.image} -l panic --cli")
        cls.container.timeout = os.getenv("TEST_TIMEOUT", 30)

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

    def test_connection(self):
        self.container.sendline("check connection")
        self.assertEqual(self.container.expect("Internet connection is available."), 0)

    def test_login(self):
        username = os.environ["TEST_USER"]
        password = os.environ["TEST_USER_PW"]

        self.container.sendline("login")
        self.container.expect("Username: ")
        self.container.sendline(username)
        self.container.expect("Password: ")
        self.container.waitnoecho()
        self.container.sendline(password)
        self.container.expect(r"Account (.*) was added successfully\.")

    def test_logout(self):
        self.container.sendline("logout")
        self.container.expect(r"Are you sure you want to logout account (.*):")
        self.container.sendline("yes")
        self.expect_prompt()
        self.container.sendline("info")
        self.assertEqual(self.container.expect("Please login to"), 0)

    def test_removal(self):
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

