class KissNet():
    def __init__(self, home, login, target, source='', username='', password=''):
        self.home = home
        self.login = login
        self.target = target
        self.source = source
        self.username = username
        self.password = password
        self.series = None

    def home_link(self):
        return self.home + r'/' + self.home

    def login_link(self):
        return self.home + r'/' + self.login

    def series_link(self, series):
        return self.home + r'/' + self.target + r'/' + series

    def episode_link(self, series, episode):
        return self.home + r'/' + self.target + r'/' + series + r'/'+ episode + self.source

    def user_htmlpath(self):
        return "//a[@id='aDropDown']/span"

    def vid_containerpath(self, loginstatus=False):
        if loginstatus is True:
            return "//div[@id='divDownload']/a"
        return 'my_video_1'

    def vid_mp4path(self, loginstatus=False):
        if loginstatus is True:
            return "//a[@id='button-download']"
        return 'videojs_html5_api'