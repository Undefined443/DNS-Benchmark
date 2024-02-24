#!/Users/xiao/Workspace/Lab/DNS-Benchmark/.venv/bin/python

import threading
import subprocess
import yaml
import re
import time
from sys import stderr

CONFIG_FILE = "config.yaml"


class DnsQueryThread(threading.Thread):
    OK = 0
    ERROR = 1

    def __init__(self, _domain, _nameserver):
        threading.Thread.__init__(self)

        self.nameserver = _nameserver
        self.domain = _domain
        self.command = None

        self.header = {
            "status": None,
            "answer": None,
        }
        self.answer = None
        self.code = None
        self.query_result = None
        self.query_time = None
        self.execution_time = None

    def run(self):
        start_time = time.time()  # 线程开始时的时间戳
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

        self.command = [
            "kdig",
            f"@{self.nameserver}",
            self.domain,
            "+retry=0",
            "+timeout=5",
        ]

        if option:
            self.command.append(option)

        try:
            self.query_result = subprocess.check_output(
                self.command, stderr=subprocess.STDOUT
            ).decode()
        except subprocess.CalledProcessError as e:
            self.query_result = e.output.decode()

        try:
            search = re.search(
                r";; ->>HEADER<<- opcode: QUERY; status: (.*); id: \d+\n;; Flags: .*; QUERY: 1; ANSWER: (\d+); AUTHORITY: \d+; ADDITIONAL: \d+",
                self.query_result,
            )
            self.header["status"] = search.group(1)
            self.header["answer"] = search.group(2)
        except AttributeError:
            if ";; WARNING: response timeout for " in self.query_result:
                self.header["status"] = "RESPONSE_TIMEOUT"
            elif ";; WARNING: connection timeout for " in self.query_result:
                self.header["status"] = "CONNECTION_TIMEOUT"
            elif ";; ERROR: failed to query server " in self.query_result:
                self.header["status"] = "FAILED_TO_QUERY_SERVER"
            else:
                self.header["status"] = "UNKNOWN_ERROR"
                print(self.query_result, file=stderr)

        if self.header["status"] == "NOERROR":
            self.code = DnsQueryThread.OK

            self.query_time = float(
                re.search(
                    r";; Received \d+ B\n;; Time .* CST\n;; From .* in (\d+(\.\d)?) ms",
                    self.query_result,
                ).group(1)
            )
            try:
                search = re.search(
                    r";; ANSWER SECTION:\n(.*IN\s+CNAME.*\n)*(.*IN\s+A\s+\d+\.\d+\.\d+\.\d+)*",
                    self.query_result,
                ).group(2)
                self.answer = re.search(
                    r".*IN\s+A\s+(\d+\.\d+\.\d+\.\d+)", search
                ).group(1)
            except Exception:
                # stderr
                print("line 104: answer section failed", file=stderr)
        else:
            self.code = DnsQueryThread.ERROR
        end_time = time.time()  # 线程结束时的时间戳
        self.execution_time = end_time - start_time
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
    nameservers = config["nameservers"]
    domains = config["domains"]

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
                query_time = query_thread.header["status"]
            elif query_thread.answer == "0.0.0.0" or query_thread.answer == "127.0.0.1":
                query_time = "POISONED"
            else:
                query_time = query_thread.query_time

            query_times[domain][nameserver] = query_time

    # Print query times
    c1 = 60  # column width 1
    c2 = 22  # column width 2
    separator_length = c1 + c2
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
            print(f"{nameserver:{c1}s}{query_time:>{c2}}")

    print(separator_line)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)
