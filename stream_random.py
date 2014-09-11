#!/usr/bin/env python2

from threading import Thread
from getpass import getpass
from time import sleep
import gmusicapi
import readline
import random
import pygst
import glib
import gst
import sys
import os

MESSAGE_TIMEOUT = 3  # seconds

class GetchUnix:
    """Implements getch for unix systems. Thanks StackOverflow."""
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class StreamPlayer:
    """Handles the control of playbin2 from the gst library."""
    def __init__(self, URI, main_player):
        self._player = gst.element_factory_make("playbin2", "player")
        self.change_song(URI)
        self.playing = False
        watcher = Thread(target=self.player_watch_thread, args=(main_player,))
        watcher.start()

    def player_watch_thread(self, main_player):  # FIXME
        self.bus = self._player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", main_player.handle_song_end)
        # glib.MainLoop().run()

    def change_song(self, URI):
        self._player.set_property('uri', URI)

    def play(self):
        self.playing = True
        self._player.set_state(gst.STATE_PLAYING)

    def pause(self):
        self.playing = False
        self._player.set_state(gst.STATE_PAUSED)

    def toggle(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        self.playing = False
        self._player.set_state(gst.STATE_NULL)


def notify(txt):
    print(txt)


def term_width():
    import os
    rows, columns = os.popen('stty size', 'r').read().split()
    return columns


def get_device_id(username, password):
    """Handles retrieving an android device ID to enable streaming."""
    if os.path.exists("./device_id"):
        with open("device_id") as id_file:
            device_id = id_file.read().strip()
        return device_id
    else:
        api = gmusicapi.Webclient()
        api.login(username, password)
        devices = api.get_registered_devices()
        for device in devices:
            if device['type'] == 'PHONE':
                return str(device['id'])[2:]


class Player:
    def __init__(self, username, password):
        self.device_id = get_device_id(username, password)
        self.username = username
        self.password = password
        self.api = gmusicapi.Mobileclient()
        self.logged_in = self.api_login()
        self.paused = False
        if self.logged_in:
            print("Logged in successfully!")
        else:
            print("Login failed.")
            quit()
        self.get_random_song()

    def beginloop(self):
        self.play_stream()
        while True:
            os.system('setterm -cursor off')
            try:
                s = unicode("\rNow playing: {s[title]} by {s[artist]}".format(
                        s=self.song))
            except UnicodeEncodeError:
                import unicodedata
                def strip_accents(s):
                    return ''.join(c for c in unicodedata.normalize('NFD', s) 
                        if unicodedata.category(c) != 'Mn')
                s = "\rNow playing: {} by {}".format(
                        strip_accents(self.song['title']),
                        strip_accents(self.song['artist']))
            s += " " * (int(term_width()) - len(s) - 1)
            sys.stdout.write(s)
            sys.stdout.flush()
            user_key = getch()
            if user_key == " ":
                self.paused = not self.paused
                self.stream_player.toggle()
                if self.paused:
                    sys.stdout.write("\rPaused:     ")
                    sys.stdout.flush()
                else:
                    sys.stdout.write("\rNow playing:")
                    sys.stdout.flush()
            elif user_key == "n":
                self.stream_player.stop()
                self.get_random_song()
                self.play_stream()
            elif user_key == "s":
                try:
                    # Screw x-compatibility.
                    os.system('setterm -cursor on')
                    search_text = raw_input("\nSearch: ")
                    os.system('setterm -cursor off')
                except (EOFError, KeyboardInterrupt):
                    continue
                matching_songs = []
                for song in self.api.get_all_songs():
                    if any([search_text.lower() in song['title'].lower(),
                           search_text.lower() in song['artist'].lower(),
                           # search_text.lower() in song['album'].lower()
                           ]):
                        matching_songs.append(song)
                        
                if not matching_songs:
                    sys.stdout.write("\rNo results found.      ")
                    sys.stdout.flush()
                    sleep(MESSAGE_TIMEOUT)
                    continue
                self.stream_player.stop()
                self.song = random.choice(matching_songs)  # FIXME
                # self.song = matching_songs[1]
                self.play_stream()
            elif user_key == "q":
                break

    def api_login(self):
        return self.api.login(self.username, self.password)

    def play_url(self, stream_url):
        self.stream_player = StreamPlayer(stream_url, self)
        self.stream_player.play()

    def get_random_song(self):
        all_songs = self.api.get_all_songs()
        self.song = random.choice(all_songs)

    def play_stream(self):
        stream_url = self.api.get_stream_url(self.song['id'], self.device_id)
        self.play_url(stream_url)

    def handle_song_end(self):
        self.get_random_song()

def disable_warnings():
    import requests.packages.urllib3 as urllib3
    urllib3.disable_warnings()


def main():
    disable_warnings()
    while True:
        username = raw_input("Username: ")
        # notify("A password is required to use Google Music.")
        password = getpass()
        try:
            player = Player("bedekelly97", "0p3n_5354m3")
            player.beginloop()
        except gmusicapi.exceptions.NotLoggedIn:
            print("Login details were incorrect or Google blocked a login " +
                  "attempt. Please check your email.")
        else:
            break
    os.system('setterm -cursor on')
    print


if __name__ == "__main__":
    # Implement 
    try:
        from msvcrt import getch
    except ImportError:
        getch = GetchUnix()
    main()