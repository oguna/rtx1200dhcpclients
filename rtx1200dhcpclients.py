from flask import Flask, render_template
from html.parser import HTMLParser
import urllib.request
from werkzeug.contrib.cache import SimpleCache

app = Flask(__name__)
app.config.from_pyfile('rtx1200dhcpclients.cfg')
cache = SimpleCache()


class ClientEntry:
    def __init__(self, hostname: str, macaddress: str, ipaddress: str, registered: bool, leased: bool):
        self.hostname = hostname
        self.macaddress = macaddress
        self.ipaddress = ipaddress
        self.registered = registered
        self.leased = leased


class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.colums = None
        self.entries = []
        self.rowtag = None
        self.targettable = False

    def handle_starttag(self, tag, attrs):
        if tag == 'table' and ('summary', 'policycommon') in attrs:
            self.targettable = True
        if self.targettable and tag == 'tr' and attrs and attrs[0] in [('class', 'table1'), ('class', 'table2')]:
            self.colums = []
            self.rowtag = tag
            # print("Encountered a start tag:", tag)

    def handle_endtag(self, tag):
        if tag == 'table':
            self.targettable = False
        if self.targettable and tag == self.rowtag and len(self.colums) > 8:
            if len(self.colums) >= 16:
                entry = ClientEntry(self.colums[4], self.colums[6], self.colums[8], self.colums[10] == '○',
                                    self.colums[12] == '○')
            elif len(self.colums) > 8:
                entry = ClientEntry(self.colums[3], self.colums[5], self.colums[7], self.colums[9] == '○',
                                    self.colums[11] == '○')
            self.entries.append(entry)
            self.rowtag = None
            # print("Encountered an end tag :", tag)

    def handle_data(self, data):
        if self.rowtag:
            self.colums.append(data.strip())
            # print("Encountered some data  :", data)


@app.route('/')
def index():
    host = app.config['HOST']
    user = app.config['USER']
    password = app.config['PASSWORD']
    rv = cache.get('dhcpclients')
    if rv is None:
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        top_level_url = "http://" + host + "/admin/"
        password_mgr.add_password(None, top_level_url, user, password)
        handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
        opener = urllib.request.build_opener(handler)
        urllib.request.install_opener(opener)
        with urllib.request.urlopen('http://' + host + '/admin/dhcp/policy.html') as f:
            html = f.read().decode('cp932')

        parser = MyHTMLParser()
        parser.feed(html)

        rv = parser.entries
        cache.set('dhcpclients', rv, timeout=10)

    # start_index = html.find('<table border="0" width="540" cellpadding="1" cellspacing="1" summary="policycommon">')
    # end_index = html.find('</table>', start_index) + 8
    # return html[start_index: end_index]
    link = 'http://' + host + '/admin/dhcp/policy.html'

    return render_template('index.html', link=link, entries=rv)


if __name__ == '__main__':
    app.run()
