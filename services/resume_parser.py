import requests
from bs4 import BeautifulSoup


headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
}

params = {
    'text': 'Программист',
    'isDefaultArea': 'true',
    'exp_period': 'all_time',
    'logic': 'normal',
    'pos': 'full_text',
    'hhtmFrom': 'vacancy_search_list',
    'hhtmFromLabel': 'resume_search_line',
}

response = requests.get(
    'https://hh.ru/search/resume',
      params=params,
      headers=headers
    )


soup = BeautifulSoup(response.text, 'html.parser')
main = soup.find('main', {'class': 'resume-serp-content'})
resumes = main.find_all('div', {'data-qa': 'resume-serp__resume'})
for r in resumes[:1]:
    resume_url = f'https://hh.ru{r.find("a").get("href").split("?query")[0]}'
    print(resume_url)

    response = requests.get(
        resume_url,
        headers=headers
        )

    
    soup = BeautifulSoup(response.text, 'html.parser')
    main = soup.find('div', {'class': 'resume-applicant'})
    title = main.find('div', {'class': 'resume-block__title-text-wrapper'}).text
    experience = main.find('div', {'data-qa': 'resume-block-experience'}).text[:200]
    skils = main.find('div', {'data-qa': 'skills-table'}).text