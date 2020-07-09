"""
sonos controller skill
The MIT License (MIT)

Copyright (c) 2020 Boxledev

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from mycroft.skills.core import MycroftSkill
# from mycroft.util.log import LOG
import soco
from mycroft.skills.audioservice import AudioService
from rapidfuzz import process


class SonosController(MycroftSkill):

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        super(SonosController, self).__init__(name="SonosControllerSkill")

        # Initialize working variables used within the skill.
        self.speakers = soco.discover()
        self.dictSpeakers = {}
        self.dictPlaylist = {}
        self.list_all_albums = []
        self.active_speaker = ""

        if self.speakers is not None:
            for speaker in self.speakers:
                self.dictSpeakers[str(speaker.player_name)] = speaker
            favorites = soco.music_library.MusicLibrary().get_sonos_favorites()
            self.listPlaylists = []
            for playlist in favorites:
                self.dictPlaylist[playlist.to_dict()['title']] = playlist.to_dict()['resources'][0]['uri']
                self.listPlaylists.append(playlist.to_dict()['title'])

    def initialize(self):
        self.audio_service = AudioService(self.bus)
        # padatious import intent files
        self.register_intent_file('sonos_playlist.intent', self.handle_sonos_playlist)
        self.register_intent_file('sonos_default.intent', self.handle_sonos_default)
        self.register_intent_file('sonos_search_speakers.intent', self.handle_sonos_discover_speaker)
        self.register_intent_file('sonos_show_album.intent', self.handle_sonos_show_album)
        self.register_intent_file('sonos_album.intent', self.handle_sonos_play_album)
        self.register_intent_file('sonos_commands.intent', self.handle_sonos_commands)

        # set an active speaker
        if self.settings.get('default_name') is None or self.settings.get('default_name') == "":
            self.active_speaker = str(soco.discovery.any_soco().player_name)
            #self.speak("choosing " + self.active_speaker + " as active speaker")
        else:
            self.active_speaker = process.extractOne(self.settings.get('default_name'), self.dictSpeakers.keys())[0]
            # self.speak(self.active_speaker + " was found in the settings file as default speaker")

    # search for sonos speakers and list them to the user. also get the available playlists
    def handle_sonos_discover_speaker(self):
        self.speakers = soco.discover()
        if self.speakers is not None:
            self.speak("I found the following sonos devices")
            for speaker in self.speakers:
                self.speak(speaker.player_name)
                self.dictSpeakers[str(speaker.player_name)] = speaker
            favorites = soco.music_library.MusicLibrary().get_sonos_favorites()
            self.listPlaylists = []
            for playlist in favorites:
                self.dictPlaylist[playlist.to_dict()['title']] = playlist.to_dict()['resources'][0]['uri']
                self.listPlaylists.append(playlist.to_dict()['title'])
        else:
            self.speak("I could not find any sonos devices on the local network")

    # set a chosen speaker as default/active
    def handle_sonos_default(self, message):
        if self.speakers is not None:
            self.active_speaker = message.data.get('speaker')
            self.active_speaker = process.extractOne(self.active_speaker, self.dictSpeakers.keys())[0]
            self.speak(self.active_speaker + " is now set as active")
        else:
            self.speak("I could not find any sonos devices on the local network")

    # play a chosen album
    def handle_sonos_play_album(self, message):
        if self.speakers is not None:
            spoken_album = message.data.get('album_name')
            all_albums = soco.music_library.MusicLibrary().get_music_library_information("albums", search_term='',
                                                                                         complete_result=True)
            if not self.list_all_albums:
                for album in all_albums:
                    self.list_all_albums.append(album.to_dict()['title'])
            chosen_album = process.extractOne(spoken_album, self.list_all_albums)[0]
            play_album = soco.music_library.MusicLibrary().get_tracks_for_album("", chosen_album)

            self.dictSpeakers[self.active_speaker].clear_queue()
            self.dictSpeakers[self.active_speaker].add_multiple_to_queue(play_album)
            self.dictSpeakers[self.active_speaker].play_from_queue(index=0)
            self.speak("now playing " + chosen_album + " by " +
                       self.dictSpeakers[self.active_speaker].get_current_track_info()['artist'])
        else:
            self.speak("I could not find any sonos devices on the local network")

    # play a chosen playlist (on a chosen speaker, optional)
    def handle_sonos_playlist(self, message):
        if self.speakers is not None:
            spoken_playlist = message.data.get('speak_playlist')
            spoken_speaker = message.data.get('speak_speaker')
            chosen_playlist = process.extractOne(spoken_playlist, self.dictPlaylist.keys())[0]
            if spoken_speaker is not None:
                chosen_speaker = process.extractOne(spoken_speaker, self.dictSpeakers.keys())[0]
                self.speak("now playing " + chosen_playlist + " on " + chosen_speaker)
                self.dictSpeakers[chosen_speaker].clear_queue()
                self.dictSpeakers[chosen_speaker].add_uri_to_queue(uri=self.dictPlaylist[chosen_playlist])
                self.dictSpeakers[chosen_speaker].play_from_queue(index=0)
            else:
                self.speak("now playing " + chosen_playlist + " on " + self.active_speaker)
                self.dictSpeakers[self.active_speaker].clear_queue()
                self.dictSpeakers[self.active_speaker].add_uri_to_queue(uri=self.dictPlaylist[chosen_playlist])
                self.dictSpeakers[self.active_speaker].play_from_queue(index=0)
        else:
            self.speak("I could not find any sonos devices on the local network")

    # basic commands for the active speaker
    def handle_sonos_commands(self, message):
        if self.speakers is not None:
            command = message.data.get('command')
            if command == "play":
                self.dictSpeakers[self.active_speaker].play()
            if command == "next":
                self.dictSpeakers[self.active_speaker].next()
            if command == "pause" or command == "off":
                self.dictSpeakers[self.active_speaker].pause()
            if command == "previous":
                self.dictSpeakers[self.active_speaker].previous()
            if command == "favorite" or command == "favorites":
                self.dictSpeakers[self.active_speaker].clear_queue()
                self.dictSpeakers[self.active_speaker].add_uri_to_queue(uri=self.dictPlaylist['Favorite'])
                self.dictSpeakers[self.active_speaker].play_mode = "SHUFFLE_NOREPEAT"
                self.dictSpeakers[self.active_speaker].play_from_queue(index=0)
            if command == "song" or command == "what's playing":
                self.speak(self.dictSpeakers[self.active_speaker].get_current_track_info()['title'] + " by " +
                           self.dictSpeakers[self.active_speaker].get_current_track_info()['artist'])
            if command == "louder" or command == "volume up":
                self.dictSpeakers[self.active_speaker].volume += 10
            if command == "much louder":
                self.dictSpeakers[self.active_speaker].volume += 30
            if command == 'volume down' or command == "quieter":
                self.dictSpeakers[self.active_speaker].volume -= 10
            if command == 'shuffle on':
                try:
                    self.dictSpeakers[self.active_speaker].play_mode = "SHUFFLE_NOREPEAT"
                except soco.exceptions.SoCoException:
                    pass
            if command == 'shuffle off':
                self.dictSpeakers[self.active_speaker].play_mode = "NORMAL"
        else:
            self.speak("I could not find any sonos devices on the local network")

    # show album art on screen
    def handle_sonos_show_album(self):
        album_art = self.dictSpeakers[self.active_speaker].get_current_track_info()['album_art']
        self.gui.clear()
        self.gui.show_image(album_art,
                            caption=self.dictSpeakers[self.active_speaker].get_current_track_info()['title'],
                            title=self.dictSpeakers[self.active_speaker].get_current_track_info()['artist'],
                            fill='PreserveAspectFit')


# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return SonosController()
