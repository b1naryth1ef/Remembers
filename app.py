from flask import Flask, render_template
import requests, time, json
app = Flask(__name__)

cache_time = 0
cache = []
url = "http://spreadsheets.google.com/feeds/%s/%s/%s/public/basic?alt=json-in-script"

def reloadData():
    global cache, cache_time
    cache = []
    cache_time = time.time()
    content = requests.get(url % ('list', '0AlmaXtg5P-cbdGtrRXpqUnRUVXhtbkdaaWVxMlBJUEE', '1')).content
    content = content.replace('gdata.io.handleScriptLoaded(', '').replace(');', '') #hacky but it works
    try:
        data = json.loads(content)
    except:
        print 'Error loading JSON data!'
        return

    for ent in data['feed']['entry']:
        c = ent['content']['$t'].split(', ')
        li = {'photo': None}
        for e in c:
            v = e.split(': ')
            if len(v) == 2:
                li[v[0]] = v[1]
        li['name'] = ent['title']['$t']
        cache.append(li)

def checkData():
    if cache_time-time.time() > 300 or not cache: #5 min cache
        reloadData()

@app.route('/')
def routeIndex():
    checkData()
    return render_template('index.html', persons=cache)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
