from enum import Enum
import requests
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

import cv2
import numpy as np

from errors import Error
from exceptions import *
from utils import abs_path, is_number


# Section A: GitHub API
class ProgramStatus(Enum):
    UPDATE_AVAILABLE = 'update available'
    UP_TO_DATE = 'latest'
    BETA = 'beta'


def fetch_latest_version() -> tuple[str, str]:
    response = requests.get(
        'https://api.github.com/repos/banz04/mic-drop-results/releases/latest',
        timeout=3,
    )
    tag = response.json()['tag_name'].lstrip('v')
    summary = response.json()['body'].partition('\n')[0]
    return (tag, summary)


# Section B: Discord API
def fetch_avatar_url(uid: str, api_token: str) -> str | None:  # TODO: docstring
    if not is_number(uid):
        return None

    # Try sending out a request to the API for the avatar's hash
    try:
        header = {'Authorization': f'Bot {api_token}'}
        response = requests.get(
            f'https://discord.com/api/v9/users/{uid}', headers=header,
            timeout=10
        )
    except (requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout) as e:
        raise ConnectionError from e

    # Try extracting the hash and return the complete link if succeed
    try:
        return 'https://cdn.discordapp.com/avatars/{}/{}.png'.format(
            uid, response.json()['avatar'])
    except KeyError as e:
        msg = response.json()['message'].lower()

        if '401: unauthorized' in msg:  # Invalid token
            raise InvalidTokenError(api_token, response.json()) from e

        elif 'rate-limit' in msg:
            time.sleep(response.json()['retry_after'])
            fetch_avatar_url(uid, api_token)

        elif 'unknown user' in msg:
            raise UnknownUserError(uid, response.json()) from e

        else:
            raise DiscordAPIError(api_token, response.json()) from e


def download_avatar(uid: str, avatar_dir: str, api_token: str) -> None:
    img_path = get_avatar_path(avatar_dir, uid)

    try:
        if avatar_url := fetch_avatar_url(uid, api_token):
            print('\033[A\033[2K' + avatar_url)
            req = urlopen(Request(
                avatar_url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=10)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, -1)

            cv2.imwrite(img_path, img)
    except URLError as e:
        raise ConnectionError from e


def get_avatar_path(avatar_dir: str, uid: str, *,
                    effect: str = '') -> str:
    """Returns the local path to the avatar file from user ID."""
    return abs_path(avatar_dir, f'{effect}_{uid}.png')
