from bs4 import BeautifulSoup
from threading import Thread
import subprocess
import collections
import requests
import queue
import re
import platform

class OSRSWorldPinger():
    def __init__(self):
        self.num_threads = 8
        self.ping_queue = queue.Queue()
        
        if platform.system() == "Linux":
            self.cmd_prefix = "ping {} -c 1"
            self.findstr = "time=([\d.]+) ms"
        elif platform.system() == "Windows":
            self.cmd_prefix = "ping {} -n 1"
            self.findstr = "time=([\d.]+)ms"
        else:
            sys.exit("Platform not supported")
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'}

        self.result = requests.get(url="http://oldschool.runescape.com/slu?order=WMLPA", headers=self.headers)
        self.soup = BeautifulSoup(self.result.content, "html.parser")

        self.server_list = {}

    # worker thread to ping servers with system command
    def thread_pinger(self, i, q):
        while True:
            world = q.get()
            address = "oldschool{}.runescape.com".format(world)
            
            command = self.cmd_prefix.format(address)
            output = subprocess.check_output(command, shell=True).decode('utf-8')
            matches = re.findall(self.findstr, output)
            # print(' '.join(self.server_list))
            self.server_list[world]['ping'] = int(matches[0])

            q.task_done()

    # initiates server list with info pulled from osrs world selection website.
    def init_server_list(self):
        table = self.soup.findAll("tr", "server-list__row")

        for row in table:
            data = row.find_all("td", class_="server-list__row-cell")

            w = data[0].text.split()[-1]
            if not data[1].text:
                p = "FULL"
            else:
                p = data[1].text.split()[0]

            c, t, a = data[2].text, data[3].text, data[4].text
            self.server_list[w] = {"players": p, "country": c, "type": t, "activity": a, "ping": 0}

    # displays the top five servers with the lowest latencies.
    def get_best_servers(self):
        print("=======================================================================================")

        print("[Top Five Worlds] \n")
        print(
            "{:<7} {:<20} {:<15} {:15} {:<10} {}".format("World", "Country", "Players", "Type", "Ping(ms)", "Activity"))
        print("---------------------------------------------------------------------------------------")

        # sort server_list in ascending order by ping value
        d = collections.OrderedDict(sorted(self.server_list.items(), key=lambda t: t[1]['ping']))

        count = 0
        for key, value in d.items():
            if count < 5:
                self.display(key, value)
                count += 1

    # prints out the server info in formatted string.
    def display(self, key, value):
        print("{:<7} {:<20} {:<15} {:<15} {:<10} {}".format(str(int(key) + 300), value["country"], value["players"],
                                                            value["type"], value["ping"], value["activity"]))


def main():
    wp = OSRSWorldPinger()
    wp.init_server_list()

    print("// OSRS World Pinger - https://github.com/isaychris")
    print("// Tip: Press [enter] to ping ALL worlds \n")

    x = input("Ping World[?]: ")

    print("")
    print("{:<7} {:<20} {:<15} {:15} {:<10} {}".format("World", "Country", "Players", "Type", "Ping(ms) ", "Activity"))
    print("---------------------------------------------------------------------------------------")

    # if user input is empty, ping all worlds
    if x == "":
        for key in sorted(wp.server_list.keys()):
            wp.ping_queue.put(key)

        # start the thread pool
        for i in range(wp.num_threads):
            worker = Thread(target=wp.thread_pinger, args=(i, wp.ping_queue))
            worker.setDaemon(True)
            worker.start()

        # wait until worker threads are done to exit
        wp.ping_queue.join()

        # display info for all servers
        for key, value in wp.server_list.items():
            wp.display(key, value)

        wp.get_best_servers()

    # else, user input must be a number, so ping only one world.
    else:
        if x.isdigit() and str(int(x) - 300) in wp.server_list:
            wp.ping_queue.put(str(int(x) - 300))

            # start the thread pool
            for i in range(wp.num_threads):
                worker = Thread(target=wp.thread_pinger, args=(i, wp.ping_queue))
                worker.setDaemon(True)
                worker.start()

            # wait until worker threads are done to exit
            wp.ping_queue.join()

            # display info for only one server
            wp.display(str(int(x) - 300), wp.server_list[str(int(x) - 300)])

        else:
            print("Unable to retrieve info for world [{}] ...".format(x))

    print("")
    input("Press [enter] to quit the program ...")


if __name__ == "__main__":
    main()
