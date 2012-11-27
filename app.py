from flask import Flask, render_template, redirect, flash, request
from redis import Redis
import requests, random, os, re

app = Flask(__name__)
app.secret_key = 'rawr' #We dont use this for cookies/etc so it does not need to be secure

r = Redis(host='hydr0.com', db=1) #Redis connection
url = "http://spreadsheets.google.com/feeds/list/%s/1/public/basic?alt=json" #URL for google docs json API
orgurl = "https://docs.google.com/spreadsheet/ccc?key=%s" #URL for google docs direct url
captcha_priv = os.getenv('CAPTCHAPRIV', None) #We're not using captcha currently

#Data key: ([] == hashkey)
#memorial.<id>.data
#memorial.<id>[]docid
#memorial.<id>[]secret
#memorial.<id>[]title
#memorial.<id>[]desc

def checkCaptcha(): #Not used (yet)
    if not captcha_priv: return True
    k = {
        'privatekey': captcha_priv,
        'remoteip': request.remote_addr,
        'challenge': request.form.get('recaptcha_challenge_field'),
        'response': request.form.get('recaptcha_response_field')
    }
    r = requests.get('http://www.google.com/recaptcha/api/verify', params=k)
    return r.text.startswith('true')

def addSite(title, desc, docid):
    if r.exists('memorial.%s' % title.replace(' ', '_').lower()):
        return None, None
    secret = random.randint(111111, 999999) #6! possibilites is enough. Right?
    s = {'docid': docid,
        'secret': secret,
        'title': title,
        'desc': desc}
    r.hmset('memorial.%s' % title.replace(' ', '_').lower(), s)
    return title.replace(' ', '_').lower(), secret

def getData(i):
    req = requests.get(url % i)
    if req.status_code != 200:
        print 'Error: ', url % i
        return None

    result = []
    for num, i in enumerate(req.json['feed']['entry']):
        c = i['content']['$t'].split(', ')
        li = {'photo': None}
        for e in c:
            v = e.split(': ')
            if len(v) == 2:
                li[v[0]] = v[1]
        li['name'] = i['title']['$t']
        li['id'] = num+2 #This is basically the row ID (+1 for 0-inc, +1 for header)
        result.append(li)
    return result

@app.route('/')
def routeIndex():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def routeCreate():
    for i in ['title', 'docid', 'desc']:
        if not request.form.get(i):
            flash('You must fill in a value for %s!' % i.title(), 'error') #Meh, could be improved
            return redirect('/')
    docid = re.findall('/.*key=(.*)', request.form.get('docid')) #Grabs the DOCID (this regex is a bit iffy)
    if len(docid) == 1: #Did the regex find something?
        docid = re.sub('&.*', '', docid[0])
        docid = docid.split('#')[0]
    else:
        flash('That google doc url seems to be invalid! (Make sure you paste from the PUBLISHED google doc!', 'error')
        return redirect('/')
    id, key = addSite(request.form.get('title'), request.form.get('desc'), docid)
    if not id:
        flash('The name is already taken! Try another one...')
        return redirect('/')
    flash('Your memorial was added! Its viewable here: <b>http://memorial.hydr0.com/p/%s/</b>. Also, please make sure to write this number down: %s' % (id, key), 'success')
    return redirect('/p/%s' % id)
    #if not checkCaptcha: #Captcha is disabled currently
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
        view = render_template('page.html', page=pg, persons=data)
        r.set('memorial.%s.data' % page, view)
        r.expire('memorial.%s.data' % page, 120) #Expire the cache every two mins (could be adjusted)
        if key: return redirect('/p/%s' % page)
    else:
        view = r.get('memorial.%s.data' % page)
    return view

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
