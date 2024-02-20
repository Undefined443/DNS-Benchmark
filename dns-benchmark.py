#!/Users/xiao/Workspace/Lab/DNS-Benchmark/.venv/bin/python

import threading
import subprocess
import yaml
import re

CONFIG_FILE = "config.yaml"


class DnsQueryThread(threading.Thread):
    OK = 0
    ERROR = 1

    def __init__(self, _domain, _nameserver):
        threading.Thread.__init__(self)
        self.code = None
        self.status = None
        self.query_result = None
        self.nameserver = _nameserver
        self.domain = _domain
        self.query_time = None
        self.command = None

    def run(self):
        option = ""
        if self.nameserver.startswith("https://"):
            self.nameserver = self.nameserver[len("https://") :]
            option = "+https"
        elif self.nameserver.startswith("tls://"):
            self.nameserver = self.nameserver[len("tls://") :]
            option = "+tls"
        elif self.nameserver.startswith("quic://"):
            self.nameserver = self.nameserver[len("quic://") :]
            option = "+quic"

        # Remove path
        self.nameserver = self.nameserver.split("/")[0]

        self.command = ["kdig", f"@{self.nameserver}", self.domain, "+retry=0"]

        if option:
            self.command.append(option)

        try:
            self.query_result = subprocess.check_output(
                self.command, stderr=subprocess.STDOUT
            ).decode()
        except subprocess.CalledProcessError as e:
            self.query_result = e.output.decode()

        try:
            self.status = re.search(
                r";; ->>HEADER<<- opcode: .*; status: (.*); id: \d+", self.query_result
            ).group(1)
        except AttributeError:
            if ";; WARNING: response timeout for " in self.query_result:
                self.status = "RESPONSE_TIMEOUT"
            elif ";; WARNING: connection timeout for " in self.query_result:
                self.status = "CONNECTION_TIMEOUT"
            else:
                self.status = "UNKNOWN_ERROR"

        if not self.status == "NOERROR":
            self.code = DnsQueryThread.ERROR
            return
        self.query_time = re.search(
            r";; Received \d+ B\n;; Time .* CST\n;; From .* in (\d+(\.\d)?) ms",
            self.query_result,
        ).group(1)
        self.code = DnsQueryThread.OK
        return


def safe_float_conversion(value):  # , default=float("inf")
    try:
        return float(value)
    except ValueError:
        return float("inf")


def main():
    # Read the configuration from the YAML file
    with open(CONFIG_FILE, "r") as file:
        try:
            config = yaml.safe_load(file)
        except yaml.parser.ParserError as e:
            print(f"Error parsing the configuration file: \n{e}")
            exit(1)
    nameservers = config["nameserver"]
    domains = config["domain"]

    # Perform DNS queries
    query_threads = {}
    for domain in domains:
        query_threads[domain] = {}

        for nameserver in nameservers:
            query_thread = DnsQueryThread(domain, nameserver)
            query_thread.start()
            query_threads[domain][nameserver] = query_thread

    query_times = {}
    for domain in domains:
        query_times[domain] = {}
        for nameserver in nameservers:
            query_thread = query_threads[domain][nameserver]
            query_thread.join()

            if query_thread.code is DnsQueryThread.ERROR:
                query_time = query_thread.status
            else:
                query_time = query_thread.query_time

            query_times[domain][nameserver] = query_time

    # Print query times
    separator_length = 80
    separator_line = "-" * separator_length
    # Sort query times
    for domain in domains:
        sorted_query_times = dict(
            sorted(
                query_times[domain].items(),
                key=lambda item: safe_float_conversion(item[1]),
            )
        )
        print(separator_line)
        # 居中显示 >> Benchmark for {domain} <<
        print(f"{'>> Benchmark for ' + domain + ' <<':^{separator_length}s}")
        for nameserver, query_time in sorted_query_times.items():
            print(f"{nameserver:60s} {query_time:>4}")

    print(separator_line)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)
