"""
Collection of methods to control a Chromecast via Python.

Functionality is currently limited to starting and quiting applications.

Interaction with running applications is not supported.

So what can it do? It can open YouTube movies and playlists.
"""
import xml.etree.ElementTree as ET
from collections import namedtuple
import json

import requests


APP_ID_HOME = "00000000-0000-0000-0000-000000000000"
APP_ID_YOUTUBE = "YouTube"
APP_ID_NETFLIX = "Netflix"
APP_ID_TICTACTOE = "TicTacToe"
APP_ID_GOOGLE_MUSIC = "GoogleMusic"
APP_ID_PLAY_MOVIES = "PlayMovies"
APP_ID_HULU_PLUS = "Hulu_Plus"
APP_ID_HBO = "HBO_App"
APP_ID_PANDORA = "Pandora_App"
APP_ID_REDBULLTV = "edaded98-5119-4c8a-afc1-de722da03562"
APP_ID_VIKI = "1812335e-441c-4e1e-a61a-312ca1ead90e"
APP_ID_PLEX_QA = "06ee44ee-e7e3-4249-83b6-f5d0b6f07f34"
APP_ID_PLEX = "06ee44ee-e7e3-4249-83b6-f5d0b6f07f34_1"
APP_ID_VEVO = "2be788b9-b7e0-4743-9069-ea876d97ac20"
APP_ID_AVIA = "aa35235e-a960-4402-a87e-807ae8b2ac79"
APP_ID_REVISION3 = "Revision3_App"
APP_ID_SONGZA = "Songza_App"
APP_ID_REALPLAYER_CLOUD = "a7f3283b-8034-4506-83e8-4e79ab1ad794_2"
APP_ID_BEYONDPOD = "18a8aeaa-8e3d-4c24-b05d-da68394a3476_1"
APP_ID_WASHINGTON_POST = "Post_TV_App"


FRIENDLY_NAMES = {
    "00000000-0000-0000-0000-000000000000": "Idle Screen",
    "GoogleMusic": "Google Music",
    "PlayMovies": "Play Movies",
    "Hulu_Plus": "Hulu Plus",
    "HBO_App": "HBO",
    "Pandora_App": "Pandora",
    "edaded98-5119-4c8a-afc1-de722da03562": "RedBull.tv",
    "1812335e-441c-4e1e-a61a-312ca1ead90e": "Viki",
    "06ee44ee-e7e3-4249-83b6-f5d0b6f07f34": "Plex QA",
    "06ee44ee-e7e3-4249-83b6-f5d0b6f07f34_1": "Plex",
    "2be788b9-b7e0-4743-9069-ea876d97ac20": "Vevo",
    "aa35235e-a960-4402-a87e-807ae8b2ac79": "Avia",
    "Revision3_App": "Revision3",
    "Songza_App": "Songza",
    "a7f3283b-8034-4506-83e8-4e79ab1ad794_2": "RealPlayer Cloud",
    "18a8aeaa-8e3d-4c24-b05d-da68394a3476_1": "Beyondpod",
    "Post_TV_App": "Washington Post"
}


def get_possible_app_ids():
    """ Returns all possible app ids. """

    try:
        data = json.loads(CC_SESSION.get(
            "https://clients3.google.com/cast/chromecast/device/config"
            ).text[4:])

        return [app['app_name'] for app in data['applications']]

    except ValueError:
        # If json fails to parse
        return []


def get_friendly_name(app_id):
    """ Return a friendly name if we have one, else the app id. """
    if app_id in FRIENDLY_NAMES:
        return FRIENDLY_NAMES[app_id]

    elif app_id.endswith("_App"):
        return app_id[:-4]

    else:
        return app_id


def start_app(host, app_id, data=None):
    """ Starts an application.

        If your TV is not on will turn it on unless app_id == APP_ID_HOME. """

    if data is None:
        data = {"": ""}

    CC_SESSION.post(_craft_url(host, app_id), data=data)


def quit_app(host, app_id=None):
    """ Quits specified application if it is running.
        If no app_id specified will quit current running app. """

    if not app_id:
        app_id = get_app_status(host).name

    if app_id:
        CC_SESSION.delete(_craft_url(host, app_id))


def play_youtube_video(host, video_id):
    """ Starts the YouTube app if it is not running and plays
        specified video. """

    start_app(host, APP_ID_YOUTUBE, {"v": video_id})


def play_youtube_playlist(host, playlist_id):
    """ Starts the YouTube app if it is not running and plays
        specified playlist. """

    start_app(host, APP_ID_YOUTUBE,
              {"listType": "playlist", "list": playlist_id})


def get_device_status(host):
    """ Returns the device status as a named tuple. """

    try:
        status_el = ET.fromstring(CC_SESSION.get(
            FORMAT_BASE_URL.format(host) + "/ssdp/device-desc.xml").text)

        device_info_el = status_el.find(XML_NS_UPNP_DEVICE + "device")
        api_version_el = status_el.find(XML_NS_UPNP_DEVICE + "specVersion")

        friendly_name = _read_xml_element(device_info_el, XML_NS_UPNP_DEVICE,
                                          "friendlyName", "Unknown Chromecast")
        model_name = _read_xml_element(device_info_el, XML_NS_UPNP_DEVICE,
                                       "modelName", "Unknown model name")
        manufacturer = _read_xml_element(device_info_el, XML_NS_UPNP_DEVICE,
                                         "manufacturer",
                                         "Unknown manufacturer")

        api_version = (int(_read_xml_element(api_version_el,
                                             XML_NS_UPNP_DEVICE, "major", -1)),
                       int(_read_xml_element(api_version_el,
                                             XML_NS_UPNP_DEVICE, "minor", -1)))

        return DeviceStatus(friendly_name, model_name, manufacturer,
                            api_version)

    except (requests.exceptions.RequestException, ET.ParseError):
        return None


def get_app_status(host, app_id=None):
    """ Returns the status of the specified app
        or else the current running app. """
    # /apps/ will redirect to the active app
    url = (FORMAT_APP_PATH.format(host, app_id) if app_id
           else FORMAT_BASE_URL.format(host) + "/apps/")

    try:
        status_el = ET.fromstring(CC_SESSION.get(url).text)
        options = status_el.find(XML_NS_DIAL + "options").attrib

        name = _read_xml_element(status_el, XML_NS_DIAL,
                                 "name", "Unknown application")
        state = _read_xml_element(status_el, XML_NS_DIAL,
                                  "state", "unknown")

        return AppStatus(name, state, options)

    except (requests.exceptions.RequestException, ET.ParseError):
        return None


class PyChromecast(object):
    """ Class to connect to a ChromeCast. """

    def __init__(self, host, app_id=None):
        self._app_id = None
        self.app = None

        self.host = host

        self.device = get_device_status(host)

        self.app_id = app_id

    @property
    def app_id(self):
        """ Returns the selected app_id.

        Does not guerentee that it is also active.
        Use .start_app() for that.
        """
        return self._app_id

    @app_id.setter
    def app_id(self, value):
        """ Sets app_id and fetches the app status. """
        self._app_id = value

        self.refresh_app_status()

        # There is always an app active on the Chromecast.
        # So if app_id was none then get_app_status retrieved the status
        # from the current active app, let's update self._app_id
        if not value:
            self._app_id = self.app.name

    def refresh_app_status(self):
        """ Queries the Chromecast for the status of this app. """
        self.app = get_app_status(self.host, self._app_id)

    def start_app(self, data=None):
        """ Starts the app of selected app_id. """

        # data parameter has to contain atleast 1 key
        # or else some apps won't show
        start_app(self.host, self.app_id, data)
        self.refresh_app_status()

    def quit_app(self):
        """ Tells the Chromecast to quit selected app_id. """
        quit_app(self.host, self.app_id)

    def __str__(self):
        return "PyChromecast({}, {}, {}, {}, api={}.{})".format(
            self.host, self.device.friendly_name, self.device.model_name,
            self.device.manufacturer, self.device.api_version[0],
            self.device.api_version[1])


XML_NS_UPNP_DEVICE = "{urn:schemas-upnp-org:device-1-0}"
XML_NS_DIAL = "{urn:dial-multiscreen-org:schemas:dial}"

FORMAT_BASE_URL = "http://{}:8008"
FORMAT_APP_PATH = FORMAT_BASE_URL + "/apps/{}"

CC_SESSION = requests.Session()
CC_SESSION.headers['content-type'] = 'application/json'

DeviceStatus = namedtuple("DeviceStatus",
                          ["friendly_name", "model_name",
                           "manufacturer", "api_version"])
AppStatus = namedtuple("AppStatus", ["name", "state", "options"])


def _craft_url(host, app_id=None):
    """ Helper method to create a ChromeCast url given
        a host and an optional app_id. """
    return (FORMAT_APP_PATH.format(host, app_id) if app_id
            else FORMAT_BASE_URL.format(host))


def _read_xml_element(element, xml_ns, tag_name, default=""):
    """ Helper method to read text from an element. """
    try:
        return element.find(xml_ns + tag_name).text

    except Exception:
        return default


class PyChromecastException(Exception):
    """ Base exception for PyChromecast. """
    pass