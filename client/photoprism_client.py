import json
import os
from functools import wraps

import requests


INFINITE = 2**31-1


def _inspect_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        _check_for_error(response)
        response.raise_for_status()
        return response.json()
    return wrapper


class Client:
    """
    API doc:
    https://pkg.go.dev/github.com/photoprism/photoprism/internal/api
    """
    default_domain = 'https://demo.photoprism.org'
    default_root = '/api/v1'

    def __init__(self, username=None, password=None, domain=default_domain, root=default_root, debug=False):
        if debug:
            _enable_logging()
        self.base_url = domain + root
        self.session = requests.Session()
        if username:
            session_data = self._create_session(username=username, password=password)
            self.session.headers['X-Session-ID'] = session_data['id']
            self.download_token = session_data['config']['downloadToken']

    def _create_session(self, username, password):
        return self._post(
            '/session', {
                'username': username,
                'password': password
            }
        )

    def get_albums(self, count=INFINITE, **params):
        """
        count, offset, category, type=album
        """
        params['count'] = count
        return self._get('/albums', params)

    def create_album(self, title):
        return self._post('/albums', data={'Title': title})

    def add_photo_to_album(self, album_uid, photo_uid):
        return self._post(
            f'/albums/{album_uid}/photos',
            data={'photos': [photo_uid]}
        )

    def get_photos(self, count=INFINITE, **params):
        """
        count, offset, merged, country, camera, lens, label, year, month,
        color, order, public, quality
        """
        params['count'] = count
        return self._get('/photos', params)

    def get_photo(self, uid):
        return self._get('/photos/' + uid)

    def download_photo(self, uid: str, save_path: str):
        """
        下载指定照片的主文件（从 Files 中查找 primary=True 的 file → Hash → /download/{hash}）
        """
        # 1. 获取照片详情
        photo = self.get_photo(uid)

        # 2. 找到 primary 文件（或退回第一个文件）
        files = photo.get("Files", [])
        if not files:
            raise RuntimeError(f"照片 {uid} 没有可下载的文件")

        primary_file = next((f for f in files if f.get("Primary")), files[0])
        file_hash = primary_file.get("Hash")
        if not file_hash:
            raise RuntimeError(f"照片 {uid} 的主文件缺少 Hash")

        # 3. 下载该文件
        url = f"{self.base_url}/dl/{file_hash}?t={self.download_token}"
        resp = self.session.get(url, stream=True)
        resp.raise_for_status()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return save_path

    def add_label_to_photo(self, photo_uid, label_name, label_priority=10):
        return self._post(
            f'/photos/{photo_uid}/label',
            data={
                'Name': label_name,
                'Priority': label_priority
            }
        )

    def import_(self, path='/', move=True, dest=''):
        return self._post(
            '/import/',
            data={
                'path': path,
                'move': move,
                dest: dest
            }
        )

    @_inspect_response
    def _get(self, url_path, params=None):
        return self.session.get(self.base_url + url_path, params=params)

    @_inspect_response
    def _post(self, url_path, data=None):
        return self.session.post(
            self.base_url + url_path,
            data=json.dumps(data)
        )


def _check_for_error(response):
    if not response.ok:
        try:
            print(response.json())
        except ValueError:
            pass


def _enable_logging():
    # https://stackoverflow.com/a/16630836
    import logging
    import http.client as http_client

    http_client.HTTPConnection.debuglevel = 1

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True