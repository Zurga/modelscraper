from scraper import ThreadScraper
import json
import requests as req
from peerwise import clss

username = ''
passwd = ''
prefix = 'https://peerwise.cs.auckland.ac.nz/course/'

login_data = {'user': username,
            'pass': passwd,
            'cmd': 'login',
            'inst_shortcode': 'uva_nl',
            'redirect': '',
            }

ses = req.session()
login = ses.post('https://peerwise.cs.auckland.ac.nz/at/?uva_nl', data=login_data)
print('logged in')
course = ses.get('https://peerwise.cs.auckland.ac.nz/course/main.php?course_id=12160')
print('got the course')

scraper = ThreadScraper(clss=clss, get_threads=2, session=ses)
'''
results = scraper.start_scraping()
print(results)
with open('questions.json','w') as dump:
    json.dump(results, dump)
course_url = 'https://peerwise.cs.auckland.ac.nz/course/main.php?course_id=12160'
answer_url = prefix + 'main.php?answer=%s&cmd=saveAnswer&id=%d'
rate_url = prefix + main.php


if login:


def get_questions():
    unan = ses.get('https://peerwise.cs.auckland.ac.nz/course/main.php?cmd=showUnansweredQuestions')
    html = lxhtml.fromstring(unan.text)
    questions = html.cssselect('a.viewQ')
    return (prefix + q.attrib['href'] for q in questions)


def answer_question(url):
    q = ses.get(url)
    html = lxhtml.fromstring(q.text)
    answers = html.cssselect('input.btn_answer')
    text = html.cssselect('td.displayAltText p')
    q_id = url.split('=')[-1]
    print(url)
    ans_text = list(zip(answers, text))
    ans_text_len = [(ans, len(text.text_content().split())) for ans, text in ans_text]
    answer = max(ans_text_len, key=lambda x: x[1])
    q_answered = ses.post(answer_url % (answer[0].attrib['value'], q_id))

    rate_data['qid'] = q_id
    q_rated = ses.post(rate_url, data=rate_data)
    input('wacht even')


def main():
    while True:
        questions = get_questions()
        for q in questions:
            answer_question(q)


if __name__ == '__main__':
    main()
'''
