import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
import random
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

SEARCH_URL = "https://hh.ru/search/resume"

async def fetch_text(client: httpx.AsyncClient, url: str, params=None) -> str:
    for attempt in range(3):
        try:
            # Добавляем случайную задержку
            await asyncio.sleep(random.uniform(1, 3))
            
            r = await client.get(url, params=params, headers=HEADERS, timeout=30.0)
            if r.status_code == 403:
                # Если заблокировали — ждём дольше и пробуем с другими заголовками
                await asyncio.sleep(random.uniform(5, 10))
                headers = HEADERS.copy()
                headers["User-Agent"] = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(100, 120)}.0.0.0 Safari/537.36"
                r = await client.get(url, params=params, headers=headers, timeout=30.0)
            
            r.raise_for_status()
            return r.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403 and attempt < 2:
                print(f"403 Forbidden, попытка {attempt + 1}/3")
                await asyncio.sleep(random.uniform(10, 20))
                continue
            raise
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(random.uniform(2, 5))
                continue
            raise

def parse_list(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main", {"class": "resume-serp-content"})
    if not main:
        return []
    resumes = main.find_all("div", {"data-qa": "resume-serp__resume"})
    urls = []
    for r in resumes[:20]:
        href = r.find("a")
        if not href:
            continue
        url = href.get("href")
        if not url:
            continue
        urls.append(f"https://hh.ru{url.split('?query')[0]}")
    return urls

def parse_resume(html: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("div", {"class": "resume-applicant"})
    if not main:
        return {}
    try:
        title = main.find("div", {"class": "resume-block__title-text-wrapper"}).get_text(" ", strip=True)
    except Exception:
        title = ""
    try:
        exp_block = main.find("div", {"data-qa": "resume-block-experience"})
        experience = exp_block.get_text(" ", strip=True) if exp_block else ""
    except Exception:
        experience = ""
    try:
        skills_block = main.find("div", {"data-qa": "skills-table"}) or main
        tags = []
        for el in skills_block.select('[data-qa="bloko-tag__text"], .bloko-tag__text, .resume-skill-item'):
            txt = el.get_text(" ", strip=True)
            if txt:
                tags.append(txt)
        if tags:
            skills = ", ".join(sorted(set(tags)))
        else:
            skills = (skills_block.get_text(" ", strip=True) if skills_block else "")
    except Exception:
        skills = ""
    return {"title": title, "experience": experience, "skills": skills}

async def search_and_fetch(query: str) -> List[Dict[str, str]]:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            html = await fetch_text(client, SEARCH_URL, params={
                "text": query,
                "isDefaultArea": "true",
                "exp_period": "all_time",
                "logic": "normal",
                "pos": "full_text",
                "hhtmFrom": "vacancy_search_list",
                "hhtmFromLabel": "resume_search_line",
            })
            urls = parse_list(html)
            results: List[Dict[str, str]] = []

            async def fetch_one(u: str):
                try:
                    await asyncio.sleep(random.uniform(0.5, 2))  # Задержка между запросами
                    t = await fetch_text(client, u)
                    data = parse_resume(t)
                    if data:
                        data["url"] = u
                        results.append(data)
                except Exception as e:
                    print(f"Ошибка при получении резюме {u}: {e}")

            await asyncio.gather(*[fetch_one(u) for u in urls])
            return results
    except Exception as e:
        print(f"Ошибка при поиске резюме: {e}")
        return []