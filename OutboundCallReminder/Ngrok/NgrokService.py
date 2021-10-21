from time import sleep
from Ngrok.NgrokConnector import NgrokConnector
import os
import subprocess
import psutil
import signal
from pathlib import Path


class NgrokService:
    # The NGROK process
    __ngrokProcess = None  # Process
    # NgrokConnector connector;
    __connector = None  # NgrokConnector

    def __init__(self, ngrokPath, authToken):
        self.__connector = NgrokConnector()
        self.ensure_ngrok_not_running()
        self.create_ngrok_process(ngrokPath, authToken)

    # <summary>
    # Ensures that NGROK is not running.
    # </summary>

    def ensure_ngrok_not_running(self):
        process_name = "ngrok.exe"

        for proc in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if process_name.lower() in proc.name().lower():
                    raise(
                        "Looks like NGROK is still running. Please kill it before running the provider again.")

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    # <summary>
    # Kill ngrok.exe process
    # </summary>

    def dispose(self):
        out, err = self.__ngrokProcess.communicate()
        for line in out.splitlines():
            if 'ngrok.exe' in line:
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)

    # <summary>
    # Creates the NGROK process.
    # </summary>

    def create_ngrok_process(self, ngrokPath, authToken):
        auth_token_args = ""
        if (authToken and len(authToken)):
            auth_token_args = " --authtoken " + authToken

        executable = str(Path(ngrokPath, "ngrok.exe"))
        os.chmod(executable, 0o777)
        self.__ngrokProcess = subprocess.Popen(
            [executable, "http", "http://localhost:9007/", "-host-header", "localhost:9007"])

    # <summary>
    # Get Ngrok URL
    # </summary>

    def get_ngrok_url(self):
        try:
            totalAttempts = 4
            while(totalAttempts > 0):
                # Wait for fetching the ngrok url as ngrok process might not be started yet.
                sleep(2)
                tunnels = self.__connector.get_all_tunnels()
                if (tunnels and len(tunnels['tunnels'])):
                    # Do the parsing of the get
                    ngrok_url = tunnels['tunnels'][0]['public_url']
                    return ngrok_url

                totalAttempts = totalAttempts - 1

        except Exception as ex:
            raise Exception("Failed to retrieve ngrok url --> " + str(ex))
