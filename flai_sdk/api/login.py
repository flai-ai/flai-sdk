from .base import FlaiNoAuthService
from flai_sdk.tools.utils import is_wsl

import os, sys, shutil, subprocess, webbrowser, shlex, traceback
from datetime     import datetime, timedelta
from time         import monotonic
from time         import sleep
from socket       import gethostname
from json         import loads
from urllib.parse import urlsplit

# keep this tiny and surgical
STRIP_FOR_BROWSER = (
    "FONTCONFIG_FILE", "FONTCONFIG_PATH",
    "XDG_CACHE_HOME",  # avoid confusing browsers with temp caches
    "QT_QPA_PLATFORM", "QT_PLUGIN_PATH", "MPLBACKEND",
)
LD_INJECT_VARS = ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT")


class FlaiLogin(FlaiNoAuthService):
    _poll_wait_seconds = 1.    # seconds between polls !
    _deadline = monotonic()
    _usable_token = ''
    _auth_end_point = '#/cli/auth'

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/temporary-personal-access-tokens'
    

    @staticmethod
    def _host_from_url(url: str) -> str:
        # allow inputs without scheme (e.g., "api.flai.local/path")
        if "://" not in url:
            url = "//" + url
        return urlsplit(url).hostname  # e.g. "api.flai.local"


    @staticmethod
    def _base_domain_simple(host: str) -> str:
        # parse the app domain name
        parts = host.split(".")

        # Local devbox
        if parts[-1] == 'local':
            return '.'.join(parts[1:])
        # Prod/dev/stage
        elif parts[-1] == 'ai':
            return host.replace('api', 'app')
        # flai_host defined by custom IP
        else:
            return host


    @staticmethod
    def _is_text_script(path: str) -> bool:
        try:
            with open(path, "rb") as f:
                return f.read(2) == b"#!"
        except Exception:
            return False


    @staticmethod
    def _linux_child_env() -> dict[str, str]:
        env = os.environ.copy()

        # If you're frozen, don't leak bundled loader / GI paths into system helpers.
        # (This is the #1 cause of "xdg-open/gio/GLib weirdness" in PyInstaller builds.)
        meipass = getattr(sys, "_MEIPASS", None)

        # Strip all LD_* injections (safe for openers; avoids loading bundled libs)
        for k in list(env.keys()):
            if k.startswith("LD_"):
                env.pop(k, None)

        # Strip GI/GIO/GL-related vars if they point into the bundle
        for k in ("GI_TYPELIB_PATH", "GIO_EXTRA_MODULES", "LIBGL_DRIVERS_PATH"):
            v = env.get(k)
            if v and meipass and meipass in v:
                env.pop(k, None)

        return env


    @staticmethod
    def _spawn(args: list[str], env: dict[str, str] = None) -> None:
        subprocess.Popen(
            args,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,   # detach from your CLI session as much as possible
        )


    def open_url(self, url: str) -> bool:
        try:
            if sys.platform == "win32":
                # Uses the user's default browser via ShellExecute
                os.startfile(url)  # type: ignore[attr-defined]
                return True

            if sys.platform == "darwin":
                self._spawn(["/usr/bin/open", url])
                return True
            
            if is_wsl():
                ps = shutil.which("powershell.exe")
                
                # if powershell.exe isn't available, just fall through to Linux openers
                if ps:
                    ps_url = url.replace("'", "''")  # PowerShell single-quote escape
                    self._spawn([ps, "-NoProfile", "-Command", f"Start-Process '{ps_url}'"])
                    return True

            # Linux / other Unix
            env = self._linux_child_env() if sys.platform.startswith("linux") else None

            for cmd in (["gio", "open"], ["xdg-open"]):
                exe = shutil.which(cmd[0])
                if exe:
                    self._spawn([exe] + cmd[1:] + [url], env=env)
                    return True

            # last resort fallback (can still end up calling xdg-open internally)
            return webbrowser.open(url, new=1, autoraise=True)

        except Exception:
            return False


    def send_request_for_temporary_token_and_wait_for_real_token(self, open_browser: bool = False) -> bool:

        try:
            response = self.client.post(f'{self.service_url}', json={'name': gethostname()})
            data = loads(response)
        except: # damo tu nek specificen throw?
            print('Could not send request for inital token. Is correct host set?')
            return False
            
        # time managment
        print_deadline          = datetime.now() + timedelta(seconds=data['expiration_seconds'])
        self._deadline          = monotonic() + data['expiration_seconds']
        self._poll_wait_seconds = data['poll_interval_seconds']

        # url parsing
        host = self._host_from_url(self.service_url)     # "api.flai.ai"
        base = self._base_domain_simple(host)            # "flai.ai" (for *.flai.ai)
        
        url_for_auth = 'https://' + base + '/' +  self._auth_end_point + '?' + \
            f'request-id={data["token"].partition("|")[0]}'
        
        # set temporary token for authentifaction
        self.config.flai_access_token = data['token']
        self.client.token = self.config.flai_access_token

        # browser options and prints
        if open_browser:
            is_open = self.open_url(url_for_auth)

            # browser is detected
            if is_open:
                print(f'    Opening window with URL: {url_for_auth}')
                print(f'    *if window was accidentally closed or you do not know were it opened, manually copy and open this URL in any browser.')
            
            # browser problems
            else:
                print(f'    Browser could not be opened. Please open given URL in any browser: {url_for_auth}')

        else:
            # headless
            print(f'    Open given URL in any browser: {url_for_auth}')

        print(f' You have until {print_deadline.strftime("%H:%M:%S")} to complete authentication. If you run out of time, try again.')
        
        # wait for final token
        return self._pull_for_token()   # authentication successful / failed
    

    def is_temporary_token_expired(self) -> bool:
        return monotonic() >= self._deadline


    def _pull_for_token(self) -> bool:
        is_token_set = False

        # pull until time expires or break ends loop (token was successfully generated)
        while not self.is_temporary_token_expired():
            try:
                response = self.client.get(f'{self.service_url}/exchange', skip_check=True)
                self._usable_token = response['token']   # if user get `Unauthenticated.` it will throw KeyError
                is_token_set = True
                break
            except KeyError:
                pass
            except TypeError:
                pass

            sleep(self._poll_wait_seconds)

        # reset variables
        self.config.flai_access_token = ''
        self.client.token = self.config.flai_access_token

        return is_token_set
    

    def get_useable_token(self) -> str:
        output_token = self._usable_token
        self._usable_token = ''
        return output_token
