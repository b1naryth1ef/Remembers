from flask import Flask, render_template, redirect, flash, request
from redis import Redis
import requests, json, random, sys, os, re

app = Flask(__name__)
app.secret_key = 'rawr' #not using session, so doesnt need to be uber secret

r = Redis(host='hydr0.com', db=1)
url = "http://spreadsheets.google.com/feeds/list/%s/1/public/basic?alt=json"
orgurl = "https://docs.google.com/spreadsheet/ccc?key=%s"
captcha_priv = os.getenv('CAPTCHAPRIV', None)

#Data key: ([] == hashkey)
#memorial.<id>.data
#memorial.<id>[]docid
#memorial.<id>[]secret
#memorial.<id>[]title
#memorial.<id>[]desc

def checkCaptcha():
    if not captcha_priv: return True
    k = {
        'privatekey': captcha_priv,
        'remoteip': request.remote_addr,
        'challenge': request.form.get('recaptcha_challenge_field'),
        'response': request.form.get('recaptcha_response_field')
    }
    r = requests.get('http://www.google.com/recaptcha/api/verify', params=k)
    return r.text.startswith('true')

def check(id): return requests.get(url % id).status_code == 200

def addSite(title, desc, docid):
    if r.exists('memorial.%s' % title.replace(' ', '_').lower()):
        return None, None
    secret = random.randint(111111, 999999) #not really that secret, but screw it!
    s = {'docid': docid,
        'secret': secret,
        'title': title,
        'desc': desc}
    r.hmset('memorial.%s' % title.replace(' ', '_').lower(), s)
    return title.replace(' ', '_').lower(), secret

def getData(i):
    req = requests.get(url % i)
    if req.status_code != 200:
        return None

    result = []
    for i in req.json['feed']['entry']:
        c = i['content']['$t'].split(', ')
        li = {'photo': None}
        for e in c:
            v = e.split(': ')
            if len(v) == 2:
                li[v[0]] = v[1]
        li['name'] = i['title']['$t']
        result.append(li)
    return result

def reloadData(i): pass

@app.route('/')
def routeIndex():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def routeCreate():
    for i in ['title', 'docid', 'desc']:
        if not request.form.get(i):
            flash('You must fill in a value for %s!' % i, 'error') # could be better
            return redirect('/')
    docid = re.findall('/.*key=(.*)', request.form.get('docid'))
    if len(docid) == 1:
        docid = docid[0].split('#')[0]
    else:
        flash('That google doc url seems to be invalid!')
        return redirect('/')
    id, key = addSite(request.form.get('title'), request.form.get('desc'), docid)
    if not id:
        flash('The name is already taken! Try another one...')
        return redirect('/')
    flash('Your memorial was added! Its viewable here: <b>http://memorial.hydr0.com/p/%s/</b>. Also, please make sure to write this number down: %s' % (id, key), 'success')
    return redirect('/p/%s' % id)
    #if not checkCaptcha:
    #    flash('Your captcha was incorrect! Try again!', 'error')
    #    return redirect('/')

@app.route('/p/<page>/')
@app.route('/p/<page>/refresh/<key>')
def routePage(page=None, key=None):
    if not page: return redirect('/')
    page = page.replace(' ', '_').lower()
    if not r.exists('memorial.%s' % page):
        flash('Seems that page doesnt exist! Are you sure you have the right link?', 'error')
        return redirect('/')
    pg = r.hgetall('memorial.%s' % page)
    if not r.exists('memorial.%s.data' % page) or key == pg['secret']:
        data = getData(r.hget('memorial.%s' % page, 'docid'))
        if not data:
            flash('Something seems to be wrong, but we cant access the document resource for that page. Try again later!', 'error')
            return redirect('/')
        if key == pg['secret']:
            flash('Refreshed page!', 'success')
        r.set('memorial.%s.data' % page, json.dumps(data))
        r.expire('memorial.%s.data', 120) #2 min expire time
    if key:
        return redirect('/p/%s' % page)
    data = json.loads(r.get('memorial.%s.data' % page))
    return render_template('page.html', page=pg, persons=data)

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == 'lol':
        desc = """
        In memory of those who lost their lives to Hurricane Sandy.<br />
        Please help us improve this memorial. Click the following link to edit the spreadsheet; for example, you can update the bio column:<br /> <a href="http://bit.ly/hh-memorial-sheet">HH Memorial Sheet</a>.<br />
        Special thanks to @whitneyhess for all her work compiling <a href="http://whitneyhess.com/blog/2012/11/05/the-people-who-were-killed-by-hurricane-sandy/">this information</a>.
        """
        print addSite('Hurricane Sandy Memorial Project', desc, "0An-A-lITWCO8dG8zWXFQVEtMa05SVzYzWWZRMTRmYUE")
    else:
        app.run(debug=True, host="0.0.0.0", port=5000)
